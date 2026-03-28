import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import boto3


cloudwatch = boto3.client("cloudwatch")
logs = boto3.client("logs")
cloudtrail = boto3.client("cloudtrail")
autoscaling = boto3.client("autoscaling")
dynamodb = boto3.client("dynamodb")
s3 = boto3.client("s3")
stepfunctions = boto3.client("stepfunctions")
bedrock_runtime = boto3.client("bedrock-runtime")

TABLE_NAME = os.environ["INCIDENT_TABLE_NAME"]
KNOWLEDGE_BUCKET = os.environ["KNOWLEDGE_BUCKET"]
STATE_MACHINE_ARN = os.environ["REMEDIATION_STATE_MACHINE_ARN"]
FOUNDATION_MODEL_ID = os.environ["FOUNDATION_MODEL_ID"]
MIN_CONFIDENCE = float(os.environ.get("MIN_CONFIDENCE", "0.75"))
DEFAULT_LOOKBACK_MINUTES = int(os.environ.get("LOOKBACK_MINUTES", "15"))
ALLOW_LIVE_REMEDIATION = os.environ.get("ALLOW_LIVE_REMEDIATION", "false").lower() == "true"

HERE = Path(__file__).resolve().parent
ACTION_CATALOG = json.loads((HERE / "action_catalog.json").read_text())
SYSTEM_PROMPT = (HERE / "system_prompt.txt").read_text().strip()


def handler(event, context):
    incident = parse_incident_event(event)
    telemetry = make_json_safe(collect_incident_context(incident))
    knowledge = make_json_safe(collect_knowledge_context(incident))
    decision = ask_bedrock_for_decision(incident, telemetry, knowledge)
    decision = validate_decision(decision, incident)
    decision = apply_scale_out_override(decision, incident, telemetry)

    record = {
        "incident": incident,
        "telemetry": telemetry,
        "knowledge": {
            "recentIncidentCount": len(knowledge["recentIncidents"]),
            "domainArtifactKeys": knowledge["domainArtifactKeys"]
        },
        "decision": decision,
        "status": "TRIAGED",
        "createdAt": timestamp()
    }

    persist_incident_record(record)
    persist_reasoning_artifact(incident["incidentId"], record)

    execution_input = {
      "incident": incident,
      "decision": decision,
      "telemetry": telemetry,
      "knowledgeRefs": knowledge["domainArtifactKeys"]
    }

    execution = stepfunctions.start_execution(
        stateMachineArn=STATE_MACHINE_ARN,
        name=f"{incident['incidentId']}-{uuid4().hex[:8]}",
        input=json.dumps(execution_input)
    )

    return {
        "incidentId": incident["incidentId"],
        "stateMachineExecutionArn": execution["executionArn"],
        "selectedAction": decision["action"]["type"],
        "confidence": decision["confidence"]
    }


def parse_incident_event(event):
    detail = event.get("detail", {})
    hints = detail.get("incidentHints", detail)
    alarm_name = detail.get("alarmName", event.get("detail-type", "synthetic-incident"))
    incident_id = event.get("id") or f"incident-{uuid4().hex}"
    state = detail.get("state", "ALARM")
    reason = detail.get("reason", "No reason supplied.")

    if isinstance(state, dict):
        state_value = state.get("value", "ALARM")
        reason = state.get("reason", reason)
    else:
        state_value = state

    return {
        "incidentId": incident_id,
        "source": event.get("source", "unknown"),
        "detailType": event.get("detail-type", "unknown"),
        "alarmName": alarm_name,
        "state": state_value,
        "reason": reason,
        "serviceName": hints.get("service", "orders-api"),
        "environment": hints.get("environment", "hackathon"),
        "autoScalingGroupName": hints.get("autoScalingGroupName", os.environ.get("DEFAULT_ASG_NAME", "")),
        "logGroupName": hints.get("logGroupName", os.environ.get("DEFAULT_LOG_GROUP_NAME", "")),
        "metricNamespace": hints.get("metricNamespace", "AWS/EC2"),
        "metricName": hints.get("metricName", "CPUUtilization"),
        "dimensionName": hints.get("dimensionName", "AutoScalingGroupName"),
        "dimensionValue": hints.get("dimensionValue", hints.get("autoScalingGroupName", "")),
        "eventTime": event.get("time", timestamp())
    }


def collect_incident_context(incident):
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(minutes=DEFAULT_LOOKBACK_MINUTES)

    context = {
        "alarm": safe_call(lambda: describe_alarm(incident["alarmName"])),
        "metrics": safe_call(lambda: get_metric_snapshot(incident, start_time, end_time)),
        "logs": safe_call(lambda: get_recent_logs(incident["logGroupName"], start_time, end_time)),
        "recentChanges": safe_call(lambda: lookup_recent_changes(incident["autoScalingGroupName"], start_time, end_time)),
        "autoScaling": safe_call(lambda: get_asg_state(incident["autoScalingGroupName"]))
    }
    return context


def collect_knowledge_context(incident):
    recent_incidents = query_recent_incidents(incident["serviceName"])
    domain_artifacts = load_domain_artifacts(incident["serviceName"])
    return {
        "recentIncidents": recent_incidents,
        "domainArtifacts": domain_artifacts,
        "domainArtifactKeys": [artifact["key"] for artifact in domain_artifacts]
    }


def ask_bedrock_for_decision(incident, telemetry, knowledge):
    payload = {
        "incident": incident,
        "telemetry": telemetry,
        "knowledge": {
            "recentIncidents": knowledge["recentIncidents"],
            "domainArtifacts": knowledge["domainArtifacts"]
        },
        "actionCatalog": ACTION_CATALOG["actions"]
    }

    try:
        response = bedrock_runtime.converse(
            modelId=FOUNDATION_MODEL_ID,
            system=[{"text": SYSTEM_PROMPT}],
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "text": json.dumps(payload)
                        }
                    ]
                }
            ],
            inferenceConfig={
                "temperature": 0.1,
                "topP": 0.9,
                "maxTokens": 1200
            }
        )

        model_text = "".join(
            block.get("text", "")
            for block in response["output"]["message"]["content"]
            if "text" in block
        )
        return extract_json_payload(model_text)
    except Exception as exc:
        return notify_only_decision(
            f"Bedrock response could not be used directly: {exc}",
            incident=incident
        )


def validate_decision(decision, incident):
    allowed_actions = {
        action["type"]: action
        for action in ACTION_CATALOG["actions"]
    }
    action = decision.get("action", {})
    action_type = action.get("type", "notify_only")

    if action_type not in allowed_actions:
        return notify_only_decision("Model selected an unsupported action.")

    required = allowed_actions[action_type]["requiredParameters"]
    parameters = action.get("parameters", {})
    if any(parameter not in parameters for parameter in required):
        return notify_only_decision("Model response was missing required action parameters.")

    confidence = float(decision.get("confidence", 0))
    if confidence < MIN_CONFIDENCE:
        return notify_only_decision(
            f"Confidence {confidence:.2f} is below the automation threshold.",
            incident=incident
        )

    if not ALLOW_LIVE_REMEDIATION and action_type != "notify_only":
        return notify_only_decision(
            "Live remediation is disabled for this deployment, so the incident was routed to notify_only.",
            incident=incident
        )

    return {
        "summary": decision.get("summary", "No summary provided."),
        "diagnosis": decision.get("diagnosis", "No diagnosis provided."),
        "confidence": confidence,
        "action": {
            "type": action_type,
            "reason": action.get("reason", "No reason provided."),
            "parameters": parameters,
            "requiresApproval": bool(action.get("requiresApproval", False))
        }
    }


def notify_only_decision(reason, incident=None):
    parameters = {}
    if incident:
        parameters["alarmName"] = incident["alarmName"]

    return {
        "summary": reason,
        "diagnosis": reason,
        "confidence": 0.0,
        "action": {
            "type": "notify_only",
            "reason": reason,
            "parameters": parameters,
            "requiresApproval": False
        }
    }


def apply_scale_out_override(decision, incident, telemetry):
    if incident.get("metricName") != "CPUUtilization":
        return decision

    action = decision.get("action", {})
    if action.get("type") == "scale_out_asg":
        return decision

    metric_values = latest_metric_values(telemetry)
    if not sustained_cpu_spike(metric_values):
        return decision

    auto_scaling_state = telemetry.get("autoScaling", {})
    if not isinstance(auto_scaling_state, dict):
        return decision

    desired_capacity = int(auto_scaling_state.get("DesiredCapacity", 0) or 0)
    max_capacity = int(auto_scaling_state.get("MaxSize", desired_capacity) or desired_capacity)
    target_capacity = min(max_capacity, max(desired_capacity + 2, 3))

    if target_capacity <= desired_capacity or not incident.get("autoScalingGroupName"):
        return decision

    latest_cpu = metric_values[0]
    return {
        "summary": (
            f"Sustained CPU spike detected at {latest_cpu:.2f}%. "
            f"Override selected a safe scale-out remediation."
        ),
        "diagnosis": (
            "Recent ASG CPU telemetry indicates real saturation while spare "
            "capacity is available, so the guardrail selected scale_out_asg."
        ),
        "confidence": max(float(decision.get("confidence", 0)), 0.98),
        "action": {
            "type": "scale_out_asg",
            "reason": (
                "Telemetry-based override for sustained high CPU on the application "
                "Auto Scaling Group."
            ),
            "parameters": {
                "autoScalingGroupName": incident["autoScalingGroupName"],
                "desiredCapacity": target_capacity,
                "recoveryThreshold": 65,
            },
            "requiresApproval": False,
        },
    }


def describe_alarm(alarm_name):
    response = cloudwatch.describe_alarms(AlarmNames=[alarm_name])
    return response.get("MetricAlarms", [])[:1]


def get_metric_snapshot(incident, start_time, end_time):
    if not incident["dimensionValue"]:
        return []

    response = cloudwatch.get_metric_data(
        MetricDataQueries=[
            {
                "Id": "incidentmetric",
                "MetricStat": {
                    "Metric": {
                        "Namespace": incident["metricNamespace"],
                        "MetricName": incident["metricName"],
                        "Dimensions": [
                            {
                                "Name": incident["dimensionName"],
                                "Value": incident["dimensionValue"]
                            }
                        ]
                    },
                    "Period": 60,
                    "Stat": "Average"
                },
                "ReturnData": True
            }
        ],
        StartTime=start_time,
        EndTime=end_time
    )
    return response.get("MetricDataResults", [])


def get_recent_logs(log_group_name, start_time, end_time):
    if not log_group_name:
        return []

    response = logs.filter_log_events(
        logGroupName=log_group_name,
        startTime=int(start_time.timestamp() * 1000),
        endTime=int(end_time.timestamp() * 1000),
        limit=25
    )
    return [
        {
            "timestamp": entry.get("timestamp"),
            "message": entry.get("message", "")[:500]
        }
        for entry in response.get("events", [])
    ]


def lookup_recent_changes(resource_name, start_time, end_time):
    if not resource_name:
        return []

    response = cloudtrail.lookup_events(
        LookupAttributes=[
            {
                "AttributeKey": "ResourceName",
                "AttributeValue": resource_name
            }
        ],
        StartTime=start_time,
        EndTime=end_time,
        MaxResults=10
    )
    return response.get("Events", [])


def get_asg_state(auto_scaling_group_name):
    if not auto_scaling_group_name:
        return {}

    response = autoscaling.describe_auto_scaling_groups(
        AutoScalingGroupNames=[auto_scaling_group_name]
    )
    groups = response.get("AutoScalingGroups", [])
    return groups[0] if groups else {}


def query_recent_incidents(service_name):
    response = dynamodb.query(
        TableName=TABLE_NAME,
        KeyConditionExpression="serviceName = :serviceName",
        ExpressionAttributeValues={
            ":serviceName": {"S": service_name}
        },
        ScanIndexForward=False,
        Limit=5
    )
    return [deserialize_item(item) for item in response.get("Items", [])]


def load_domain_artifacts(service_name):
    artifacts = []
    prefix = f"runbooks/{service_name}/"
    response = s3.list_objects_v2(Bucket=KNOWLEDGE_BUCKET, Prefix=prefix)
    for entry in response.get("Contents", [])[:5]:
        key = entry["Key"]
        obj = s3.get_object(Bucket=KNOWLEDGE_BUCKET, Key=key)
        artifacts.append(
            {
                "key": key,
                "content": obj["Body"].read().decode("utf-8")[:4000]
            }
        )
    return artifacts


def persist_incident_record(record):
    dynamodb.put_item(
        TableName=TABLE_NAME,
        Item={
            "serviceName": {"S": record["incident"]["serviceName"]},
            "incidentTimestamp": {"S": record["incident"]["eventTime"]},
            "incidentId": {"S": record["incident"]["incidentId"]},
            "status": {"S": record["status"]},
            "payload": {"S": json.dumps(record)}
        }
    )


def persist_reasoning_artifact(incident_id, record):
    s3.put_object(
        Bucket=KNOWLEDGE_BUCKET,
        Key=f"incidents/reasoning/{incident_id}.json",
        Body=json.dumps(record, indent=2).encode("utf-8"),
        ContentType="application/json"
    )


def deserialize_item(item):
    payload = item.get("payload", {}).get("S")
    if not payload:
        return item
    return json.loads(payload)


def extract_json_payload(model_text):
    content = model_text.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1]
        content = content.rsplit("```", 1)[0]
    return json.loads(content)


def latest_metric_values(telemetry):
    metrics = telemetry.get("metrics", [])
    if not metrics or not isinstance(metrics[0], dict):
        return []
    values = metrics[0].get("Values", [])
    return [
        float(value)
        for value in values
        if isinstance(value, (int, float))
    ]


def sustained_cpu_spike(values):
    if len(values) >= 2 and values[0] >= 70 and values[1] >= 70:
        return True
    if values and values[0] >= 90:
        return True
    return False


def safe_call(fn):
    try:
        return fn()
    except Exception as exc:
        return {
            "error": str(exc)
        }


def make_json_safe(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {
            key: make_json_safe(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [make_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [make_json_safe(item) for item in value]
    return value


def timestamp():
    return datetime.now(timezone.utc).isoformat()
