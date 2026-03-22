# Service and API Mapping

This page maps each major box in the architecture diagram to concrete AWS services and API operations for the hackathon demo.

## Opinionated demo target

For the hackathon, the cleanest implementation path is:

- Application tier on EC2 Auto Scaling
- CPU spike as the primary incident
- CloudWatch alarm as the main trigger
- EventBridge as the incident bus
- Lambda as the triage function
- Bedrock as the reasoning engine
- DynamoDB and S3 as the domain knowledge base
- Step Functions as the remediation orchestrator
- SNS and CloudWatch as the operator-facing output layer

This keeps the story aligned to the diagram and minimizes unnecessary build surface.

## Box-to-service mapping

| Diagram box | AWS service | What it does in the demo | Primary APIs or events |
| --- | --- | --- | --- |
| CloudWatch | Amazon CloudWatch and CloudWatch Logs | Detect CPU alarm, retrieve metrics, inspect logs, show dashboards | `DescribeAlarms`, `GetMetricData`, `FilterLogEvents`, `CloudWatch Alarm State Change` event |
| CloudTrail | AWS CloudTrail | Provide recent change context that might explain the incident | `LookupEvents` |
| VPC / EC2 | Amazon EC2 and EC2 Auto Scaling | Represent the monitored application tier and resource state | `DescribeInstances`, `DescribeAutoScalingGroups`, `UpdateAutoScalingGroup`, `DescribeScalingActivities` |
| RDS / Lambda | Amazon RDS and AWS Lambda | Supply application dependency or function runtime context if needed | `DescribeDBInstances`, `GetFunctionConfiguration` |
| Cost & Billing | AWS Cost Explorer | Support the optimization branch of the architecture | `GetCostAndUsage`, `GetCostAndUsageWithResources` |
| Event Bus | Amazon EventBridge | Receive incident signals and route them into the workflow | `PutRule`, `PutTargets`, `PutEvents` |
| Trigger | AWS Lambda | Enrich event context, query the knowledge base, call Bedrock, and start remediation | EventBridge target invocation, `Invoke` for test calls |
| AI Brain | Amazon Bedrock Runtime | Analyze, diagnose, decide, and return a structured action plan | `Converse` |
| Knowledge base | Amazon DynamoDB | Store and query incident history, known patterns, and recent outcomes | `Query`, `PutItem` |
| Knowledge base artifacts | Amazon S3 | Store runbooks, domain notes, and reasoning artifacts | `GetObject`, `PutObject` |
| Remediation orchestrator | AWS Step Functions | Execute the allowed remediation path chosen by the agent | `StartExecution` |
| Auto Scaling action | Amazon EC2 Auto Scaling | Increase desired capacity during the CPU spike scenario | `UpdateAutoScalingGroup` |
| SSM action | AWS Systems Manager | Restart services, run patch workflows, or execute operational documents | `SendCommand`, `StartAutomationExecution` |
| Monitoring output | Amazon SNS | Notify operators about selected action and final outcome | `Publish` |
| Monitoring output | Amazon CloudWatch Dashboards | Show before-and-after health and recovery verification | Dashboard widgets backed by CloudWatch metrics |

## Recommended implementation by layer

### 1. Cloud sources

- Use a CloudWatch metric alarm for CPU utilization on the application ASG.
- Optionally enrich with application logs from CloudWatch Logs.
- Use CloudTrail lookups to detect whether a recent deployment or config change may have contributed.

### 2. Event layer

- Create an EventBridge rule that matches `CloudWatch Alarm State Change`.
- Add the Lambda triage function as the target.
- Keep a second custom event path available through `PutEvents` so you can inject a clean demo incident if needed.

### 3. AI agent layer

- Lambda receives the event and gathers the incident context.
- Lambda reads recent incident patterns from DynamoDB and domain runbooks from S3.
- Lambda sends a structured payload to Bedrock `Converse`.
- Bedrock returns JSON that includes summary, diagnosis, confidence, and recommended action.

### 4. Knowledge base

- DynamoDB table schema:
  - partition key: `serviceName`
  - sort key: `incidentTimestamp`
- S3 bucket layout:
  - `runbooks/`
  - `architecture/`
  - `incidents/raw/`
  - `incidents/reasoning/`

### 5. Remediation layer

- Lambda starts the Step Functions workflow.
- The first demo branch should be `scale_out_asg`.
- Keep additional branches modeled for `restart_service_via_ssm`, `patch_instance_via_ssm`, and `optimize_cost_recommendation`.
- After the action, invoke a verifier Lambda that checks recovery and writes the outcome back to DynamoDB and S3.

### 6. Monitoring and dashboard layer

- Publish an SNS notification with the diagnosis and selected action.
- Show CloudWatch metrics before and after remediation.
- Persist a short incident summary for operator review.

## API contract for the Bedrock decision

The triage function should expect Bedrock to return a JSON payload shaped like this:

```json
{
  "summary": "CPU is elevated across the application tier.",
  "diagnosis": "The Auto Scaling group is under-provisioned for the current load.",
  "confidence": 0.93,
  "action": {
    "type": "scale_out_asg",
    "reason": "Increase capacity to reduce saturation.",
    "parameters": {
      "autoScalingGroupName": "orders-api-asg",
      "desiredCapacity": 4
    },
    "requiresApproval": false
  }
}
```

## Best-fit API set for the first demo

If we optimize for one polished scenario, the smallest useful API footprint is:

- `DescribeAlarms`
- `GetMetricData`
- `FilterLogEvents`
- `LookupEvents`
- `DescribeAutoScalingGroups`
- `Converse`
- `Query`
- `GetObject`
- `StartExecution`
- `UpdateAutoScalingGroup`
- `DescribeScalingActivities`
- `PutItem`
- `PutObject`
- `Publish`

## Optional later extension

If we want to make the domain knowledge layer more managed over time, we can infer from the current design that Bedrock could later be paired with a managed retrieval layer. For the hackathon, though, direct retrieval from DynamoDB and S3 keeps the implementation simpler and closer to the diagram.

