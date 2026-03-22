# Solution Outline

Use this document alongside the visual diagram so the architecture tells a coherent story. This version is aligned to the current high-level architecture diagram.

## 1. Business context

- Problem summary: Cloud teams lose time and availability because alerts still require manual diagnosis and remediation.
- Desired outcome: Detect runtime issues early and let a virtual cloud engineer analyze and resolve safe operational incidents automatically.
- Who interacts with the system: AWS application workloads, observability services, the agentic workflow, and human operators who review outcomes.

## 2. System components

### Cloud sources

- CloudWatch for operational metrics, alarms, and dashboards
- CloudTrail for change and activity visibility
- VPC and EC2 as monitored infrastructure sources
- RDS and Lambda as application runtime and dependency sources
- Cost and Billing as a signal source for optimization-related actions

### Event layer

- Amazon EventBridge as the central event bus that receives incident and operational events from cloud sources

### AI agent layer

- AWS Lambda as the trigger and control point that starts the reasoning flow
- Amazon Bedrock as the reasoning engine that analyzes, diagnoses, decides, and plans an action
- A knowledge base connected to the agent so it can use prior incident history and learned patterns

### Knowledge base

- DynamoDB to store incident history and structured patterns
- Amazon S3 to store supporting artifacts, histories, and related knowledge assets

### Remediation layer

- AWS Step Functions to orchestrate automated actions
- Auto Scaling actions for capacity-based remediation
- AWS Systems Manager for operational runbooks and command execution
- Restart actions for service recovery
- Patch actions for safe repair or drift correction
- Cost optimization actions for efficiency-related recommendations or changes

### Monitoring and dashboard layer

- CloudWatch Dashboards for operational visibility
- SNS Alerts for notifications
- Cost Reports for optimization visibility
- Logs and analytics outputs for audit and review

## 3. Request or event flow

1. Cloud sources such as CloudWatch, CloudTrail, VPC or EC2, RDS or Lambda, and Cost and Billing generate operational events and telemetry.
2. Amazon EventBridge receives those signals on the event bus and normalizes the handoff into the agentic workflow.
3. A Lambda trigger is invoked from the event bus.
4. Lambda passes the incident context into the AI agent layer.
5. Amazon Bedrock analyzes the signal, diagnoses the likely issue, decides on the best response, and plans an action.
6. Bedrock consults the knowledge base, which uses DynamoDB and S3 for incident history and patterns.
7. The selected remediation path is handed to AWS Step Functions in the remediation layer.
8. Step Functions executes bounded actions such as auto scaling, SSM automation, restart, patching, or cost optimization steps.
9. Incident outcomes and patterns are persisted back into DynamoDB and S3.
10. Monitoring outputs are reflected in CloudWatch Dashboards, SNS alerts, cost reports, and logs and analytics.
11. The loop closes when the incident is resolved and verification signals confirm recovery.

## 4. Security and governance

- Identity and access model: Least-privilege IAM roles for EventBridge, Lambda, Bedrock access, Step Functions, DynamoDB, S3, and each remediation action
- Network boundaries: Keep execution inside approved AWS accounts and VPC-connected environments where required
- Secrets handling: Use AWS-native secret storage and avoid embedding credentials in prompts or workflow code
- Audit trail: Persist incident context, reasoning summary, action taken, and verification result through the knowledge base and monitoring layers
- Policy and guardrails: Restrict Bedrock-driven decisions to pre-approved Step Functions branches and allowlisted operational actions

## 5. Reliability and scale

- Failure modes: False-positive alarms, incomplete telemetry, failed Step Functions actions, or low-confidence diagnoses from the agent
- Recovery path: Fall back to notification-only behavior when confidence is low, data is incomplete, or a requested action is outside policy
- Monitoring and alerting: Track incident count, diagnosis quality, action success rate, verification success, and manual override cases
- Cost awareness: Cost and Billing is explicitly in scope, which makes optimization a first-class use case as well as a governance concern

## 6. Tradeoffs

- Optimized for: Fast recovery of common operational incidents using safe, observable automation with a central event bus and explicit action orchestration
- Deferred: Broad multi-incident autonomy, destructive remediations, and advanced cross-account governance
- Assumptions to validate: Which source events will be live in the demo, whether Bedrock reasoning will be fully live or partly scripted, and how recovery verification will be shown visually

## 7. Demo notes

- What to show live: A CPU spike or similar runtime issue that triggers detection, diagnosis, remediation, and recovery verification
- What to simulate: Any source events that are hard to generate live, as long as EventBridge, Lambda, Bedrock reasoning, and Step Functions remediation still look like one credible flow
- What evidence supports the claims: EventBridge event receipt, Lambda invocation, Bedrock reasoning summary, Step Functions execution, DynamoDB or S3 incident record, improved CloudWatch metrics, and an operator-facing notification

## 8. Diagram-aligned summary

- Event ingress is centralized through Amazon EventBridge.
- AWS Lambda is the trigger that connects incoming events to the AI reasoning layer.
- Amazon Bedrock is the decision engine and is shown performing analyze, diagnose, decide, and plan-action functions.
- DynamoDB and S3 act as the knowledge base for incident history and patterns.
- AWS Step Functions orchestrates remediation actions rather than letting the model call arbitrary APIs directly.
- Monitoring remains visible through CloudWatch Dashboards, SNS alerts, cost reports, and logs analytics outputs.
