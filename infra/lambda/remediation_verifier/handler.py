import json
import os
from datetime import datetime, timedelta, timezone

import boto3


cloudwatch = boto3.client("cloudwatch")
autoscaling = boto3.client("autoscaling")
dynamodb = boto3.client("dynamodb")
s3 = boto3.client("s3")
sns = boto3.client("sns")

TABLE_NAME = os.environ["INCIDENT_TABLE_NAME"]
KNOWLEDGE_BUCKET = os.environ["KNOWLEDGE_BUCKET"]
NOTIFICATION_TOPIC_ARN = os.environ.get("NOTIFICATION_TOPIC_ARN")
RECOVERY_LOOKBACK_MINUTES = int(os.environ.get("RECOVERY_LOOKBACK_MINUTES", "10"))
DEFAULT_RECOVERY_THRESHOLD = float(os.environ.get("CPU_RECOVERY_THRESHOLD", "65"))


def handler(event, context):
    incident = event["incident"]
    decision = event["decision"]
    action = decision["action"]

    verification = verify_recovery(incident, action)
    summary = {
        "incidentId": incident["incidentId"],
        "serviceName": incident["serviceName"],
        "resolved": verification["resolved"],
        "summary": verification["summary"],
        "checkedAt": timestamp()
    }

    persist_verification(summary)
    persist_verification_artifact(summary)

    if NOTIFICATION_TOPIC_ARN:
        sns.publish(
            TopicArn=NOTIFICATION_TOPIC_ARN,
            Subject="Autonomous remediation verification result",
            Message=json.dumps(summary, indent=2)
        )

    return summary


def verify_recovery(incident, action):
    if action["type"] == "scale_out_asg":
        return verify_scale_out_recovery(incident, action)
    return {
        "resolved": False,
        "summary": "Verification logic for this action type is not implemented yet."
    }


def verify_scale_out_recovery(incident, action):
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(minutes=RECOVERY_LOOKBACK_MINUTES)

    metric_results = cloudwatch.get_metric_data(
        MetricDataQueries=[
            {
                "Id": "cpu",
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

    values = metric_results["MetricDataResults"][0].get("Values", [])
    latest_value = values[0] if values else None
    threshold = action["parameters"].get("recoveryThreshold", DEFAULT_RECOVERY_THRESHOLD)

    scaling_activities = autoscaling.describe_scaling_activities(
        AutoScalingGroupName=action["parameters"]["autoScalingGroupName"],
        MaxRecords=5
    )

    resolved = latest_value is not None and latest_value <= threshold
    if resolved:
        summary = (
            f"Recovery verified. Latest CPU value {latest_value:.2f} is at or below "
            f"the threshold {threshold:.2f}."
        )
    else:
        summary = (
            f"Recovery not yet verified. Latest CPU value was {latest_value} with "
            f"{len(scaling_activities.get('Activities', []))} recent scaling activities."
        )

    return {
        "resolved": resolved,
        "summary": summary
    }


def persist_verification(summary):
    dynamodb.put_item(
        TableName=TABLE_NAME,
        Item={
            "serviceName": {"S": summary["serviceName"]},
            "incidentTimestamp": {"S": summary["checkedAt"]},
            "incidentId": {"S": summary["incidentId"]},
            "status": {"S": "VERIFIED" if summary["resolved"] else "ESCALATED"},
            "payload": {"S": json.dumps(summary)}
        }
    )


def persist_verification_artifact(summary):
    s3.put_object(
        Bucket=KNOWLEDGE_BUCKET,
        Key=f"incidents/verification/{summary['incidentId']}.json",
        Body=json.dumps(summary, indent=2).encode("utf-8"),
        ContentType="application/json"
    )


def timestamp():
    return datetime.now(timezone.utc).isoformat()

