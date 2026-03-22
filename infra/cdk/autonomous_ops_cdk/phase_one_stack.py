from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from aws_cdk import (
    CfnOutput,
    Duration,
    RemovalPolicy,
    Stack,
    aws_dynamodb as dynamodb,
    aws_events as events,
    aws_events_targets as targets,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_logs as logs,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
    aws_sns as sns,
    aws_sns_subscriptions as subscriptions,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
)
from constructs import Construct


REPO_ROOT = Path(__file__).resolve().parents[3]
LAMBDA_ROOT = REPO_ROOT / "infra" / "lambda"
SAMPLE_KNOWLEDGE_ROOT = REPO_ROOT / "data" / "sample-knowledge"


@dataclass(frozen=True)
class DemoConfig:
    project_name: str
    event_bus_name: str
    foundation_model_id: str
    notification_email: Optional[str]
    enable_live_remediation: bool


class AutonomousOpsPhaseOneStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        config = DemoConfig(
            project_name=self.node.try_get_context("projectName") or "autonomous-ops-demo",
            event_bus_name=self.node.try_get_context("eventBusName") or "autonomous-ops-demo",
            foundation_model_id=(
                self.node.try_get_context("foundationModelId") or "openai.gpt-oss-120b-1:0"
            ),
            notification_email=self.node.try_get_context("notificationEmail"),
            enable_live_remediation=context_bool(self, "enableLiveRemediation", default=False),
        )

        incident_table = dynamodb.Table(
            self,
            "IncidentHistoryTable",
            partition_key=dynamodb.Attribute(
                name="serviceName", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="incidentTimestamp", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            point_in_time_recovery_specification=dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=True
            ),
            removal_policy=RemovalPolicy.DESTROY,
        )

        knowledge_bucket = s3.Bucket(
            self,
            "KnowledgeBucket",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            auto_delete_objects=True,
            removal_policy=RemovalPolicy.DESTROY,
        )

        s3deploy.BucketDeployment(
            self,
            "DeploySampleKnowledge",
            sources=[s3deploy.Source.asset(str(SAMPLE_KNOWLEDGE_ROOT))],
            destination_bucket=knowledge_bucket,
            destination_key_prefix="runbooks/orders-api",
            retain_on_delete=False,
        )

        notification_topic = sns.Topic(
            self,
            "IncidentNotificationTopic",
            display_name="Autonomous Ops Demo Notifications",
        )

        if config.notification_email:
            notification_topic.add_subscription(
                subscriptions.EmailSubscription(config.notification_email)
            )

        verifier_log_group = logs.LogGroup(
            self,
            "RemediationVerifierLogGroup",
            log_group_name=f"/autonomous-ops/{self.stack_name}/remediation-verifier",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY,
        )

        verifier_function = lambda_.Function(
            self,
            "RemediationVerifierFunction",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="handler.handler",
            code=lambda_.Code.from_asset(str(LAMBDA_ROOT / "remediation_verifier")),
            timeout=Duration.seconds(60),
            memory_size=512,
            log_group=verifier_log_group,
            environment={
                "INCIDENT_TABLE_NAME": incident_table.table_name,
                "KNOWLEDGE_BUCKET": knowledge_bucket.bucket_name,
                "NOTIFICATION_TOPIC_ARN": notification_topic.topic_arn,
                "CPU_RECOVERY_THRESHOLD": "65",
            },
        )

        definition = build_state_machine_definition(
            self, verifier_function, notification_topic
        )

        state_machine = sfn.StateMachine(
            self,
            "RemediationWorkflow",
            definition_body=sfn.DefinitionBody.from_chainable(definition),
            timeout=Duration.minutes(10),
            tracing_enabled=True,
        )

        triage_log_group = logs.LogGroup(
            self,
            "TriageAgentLogGroup",
            log_group_name=f"/autonomous-ops/{self.stack_name}/triage-agent",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY,
        )

        triage_function = lambda_.Function(
            self,
            "TriageAgentFunction",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="handler.handler",
            code=lambda_.Code.from_asset(str(LAMBDA_ROOT / "triage_agent")),
            timeout=Duration.seconds(90),
            memory_size=1024,
            log_group=triage_log_group,
            environment={
                "INCIDENT_TABLE_NAME": incident_table.table_name,
                "KNOWLEDGE_BUCKET": knowledge_bucket.bucket_name,
                "REMEDIATION_STATE_MACHINE_ARN": state_machine.state_machine_arn,
                "FOUNDATION_MODEL_ID": config.foundation_model_id,
                "ALLOW_LIVE_REMEDIATION": str(config.enable_live_remediation).lower(),
                "DEFAULT_ASG_NAME": "",
                "DEFAULT_LOG_GROUP_NAME": "",
            },
        )

        event_bus = events.EventBus(
            self,
            "SyntheticIncidentBus",
            event_bus_name=config.event_bus_name,
        )

        events.Rule(
            self,
            "SyntheticIncidentRule",
            event_bus=event_bus,
            description="Routes synthetic hackathon incidents into the autonomous ops flow.",
            event_pattern=events.EventPattern(
                source=["hackathon.autonomous-ops"],
                detail_type=["SyntheticIncidentDetected"],
            ),
            targets=[targets.LambdaFunction(triage_function)],
        )

        incident_table.grant_read_write_data(triage_function)
        incident_table.grant_read_write_data(verifier_function)
        knowledge_bucket.grant_read_write(triage_function)
        knowledge_bucket.grant_read_write(verifier_function)
        notification_topic.grant_publish(verifier_function)
        state_machine.grant_start_execution(triage_function)

        triage_function.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "cloudwatch:DescribeAlarms",
                    "cloudwatch:GetMetricData",
                    "logs:FilterLogEvents",
                    "cloudtrail:LookupEvents",
                    "autoscaling:DescribeAutoScalingGroups",
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                ],
                resources=["*"],
            )
        )

        verifier_function.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "cloudwatch:GetMetricData",
                    "autoscaling:DescribeScalingActivities",
                ],
                resources=["*"],
            )
        )

        CfnOutput(self, "EventBusName", value=event_bus.event_bus_name)
        CfnOutput(self, "NotificationTopicArn", value=notification_topic.topic_arn)
        CfnOutput(self, "KnowledgeBucketName", value=knowledge_bucket.bucket_name)
        CfnOutput(self, "IncidentTableName", value=incident_table.table_name)
        CfnOutput(self, "StateMachineArn", value=state_machine.state_machine_arn)
        CfnOutput(self, "TriageFunctionName", value=triage_function.function_name)
        CfnOutput(
            self,
            "PhaseOneMode",
            value=(
                "live-remediation-enabled"
                if config.enable_live_remediation
                else "notify-only-safe-mode"
            ),
        )


def build_state_machine_definition(
    scope: Construct,
    verifier_function: lambda_.IFunction,
    notification_topic: sns.ITopic,
) -> sfn.IChainable:
    publish_recommendation = tasks.SnsPublish(
        scope,
        "PublishRecommendation",
        topic=notification_topic,
        subject="Autonomous Ops Recommendation",
        message=sfn.TaskInput.from_object(
            {
                "incidentId": sfn.JsonPath.string_at("$.incident.incidentId"),
                "serviceName": sfn.JsonPath.string_at("$.incident.serviceName"),
                "summary": sfn.JsonPath.string_at("$.decision.summary"),
                "diagnosis": sfn.JsonPath.string_at("$.decision.diagnosis"),
                "action": sfn.JsonPath.string_at("$.decision.action.type"),
                "confidence": sfn.JsonPath.number_at("$.decision.confidence"),
            }
        ),
        result_path="$.notification",
    )

    scale_out = tasks.CallAwsService(
        scope,
        "ScaleOutAutoScalingGroup",
        service="autoScaling",
        action="updateAutoScalingGroup",
        iam_action="autoscaling:UpdateAutoScalingGroup",
        iam_resources=["*"],
        parameters={
            "AutoScalingGroupName": sfn.JsonPath.string_at(
                "$.decision.action.parameters.autoScalingGroupName"
            ),
            "DesiredCapacity": sfn.JsonPath.number_at(
                "$.decision.action.parameters.desiredCapacity"
            ),
        },
        result_path="$.remediationExecution",
    )

    wait_for_stabilization = sfn.Wait(
        scope,
        "WaitForStabilization",
        time=sfn.WaitTime.duration(Duration.seconds(90)),
    )

    verify_remediation = tasks.LambdaInvoke(
        scope,
        "VerifyRemediation",
        lambda_function=verifier_function,
        payload=sfn.TaskInput.from_object(
            {
                "incident": sfn.JsonPath.object_at("$.incident"),
                "decision": sfn.JsonPath.object_at("$.decision"),
            }
        ),
        payload_response_only=True,
        result_path="$.verification",
    )

    publish_resolved = tasks.SnsPublish(
        scope,
        "PublishResolvedNotification",
        topic=notification_topic,
        subject="Autonomous Ops Incident Resolved",
        message=sfn.TaskInput.from_object(
            {
                "incidentId": sfn.JsonPath.string_at("$.incident.incidentId"),
                "summary": sfn.JsonPath.string_at("$.verification.summary"),
            }
        ),
        result_path="$.resolutionNotification",
    )

    publish_escalation = tasks.SnsPublish(
        scope,
        "PublishEscalationNotification",
        topic=notification_topic,
        subject="Autonomous Ops Manual Review Required",
        message=sfn.TaskInput.from_object(
            {
                "incidentId": sfn.JsonPath.string_at("$.incident.incidentId"),
                "summary": sfn.JsonPath.string_at("$.verification.summary"),
            }
        ),
        result_path="$.escalationNotification",
    )

    resolved_choice = sfn.Choice(scope, "ResolvedChoice")
    resolved_choice.when(
        sfn.Condition.boolean_equals("$.verification.resolved", True),
        publish_resolved.next(sfn.Succeed(scope, "RemediationResolved")),
    )
    resolved_choice.otherwise(
        publish_escalation.next(sfn.Succeed(scope, "ManualReviewQueued"))
    )

    scale_out_branch = scale_out.next(wait_for_stabilization).next(
        verify_remediation
    ).next(resolved_choice)

    root_choice = sfn.Choice(scope, "SelectPhaseOnePath")
    root_choice.when(
        sfn.Condition.string_equals("$.decision.action.type", "scale_out_asg"),
        scale_out_branch,
    )
    root_choice.otherwise(
        publish_recommendation.next(sfn.Succeed(scope, "NotificationDelivered"))
    )
    return root_choice


def context_bool(scope: Construct, name: str, default: bool = False) -> bool:
    raw_value = scope.node.try_get_context(name)
    if raw_value is None:
        return default
    return str(raw_value).lower() in {"1", "true", "yes", "y"}
