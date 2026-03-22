# Parsed Diagram Summary

This page converts the current PNG architecture diagram into a text description we can reuse in the proposal, demo, and final presentation.

## Diagram title

`Agentic AI for Autonomous Cloud Operations on AWS`

## Parsed layers

### 1. Cloud sources

The diagram shows five AWS source categories feeding the workflow:

- CloudWatch
- CloudTrail
- VPC / EC2
- RDS / Lambda
- Cost & Billing

These represent the operational, infrastructure, runtime, and cost signals that can initiate an incident or optimization flow.

### 2. Event layer

The event layer is built on `Amazon EventBridge` and uses an `Event Bus` as the central ingestion point. The diagram positions EventBridge as the normalization and routing layer between cloud signals and the AI workflow.

### 3. AI agent layer

The AI layer has two main components:

- `AWS Lambda` labeled as the trigger
- `Amazon Bedrock` labeled as `LLM + Reasoning`

The Bedrock agent is explicitly shown performing four capabilities:

- Analyze
- Diagnose
- Decide
- Plan Action

This makes the diagram more than a chatbot pattern. It presents Bedrock as an operational reasoning engine that turns incidents into bounded next steps.

### 4. Knowledge base

The knowledge base sits beneath the agent layer and is connected back into the reasoning process. It contains:

- `DynamoDB`
- `S3`
- `Incident History + Patterns`

The most likely interpretation is that the agent uses this layer to retrieve prior incidents, patterns, context, and evidence, then writes back the outcome of each remediation cycle.

### 5. Remediation layer

The remediation layer is labeled `Automated Actions (AWS Step Functions)` and lists the actions the system can take:

- Auto Scaling
- SSM
- Restart
- Patch
- Optimize Cost

This is an important design choice because it shows that the model does not act directly on infrastructure without control. Instead, it hands execution to Step Functions, which is a safer and more auditable orchestration layer.

### 6. Monitoring and dashboard layer

The right side of the diagram shows operator-facing outputs:

- CloudWatch Dashboards
- SNS Alerts
- Cost Reports
- Logs & Analytics

This means the architecture is not just self-healing. It is also intended to remain observable and explainable to humans.

## Parsed end-to-end flow

1. AWS operational signals originate from CloudWatch, CloudTrail, VPC or EC2, RDS or Lambda, and Cost and Billing.
2. Those signals enter Amazon EventBridge through the event bus.
3. EventBridge invokes a Lambda trigger.
4. Lambda hands the incident context to Amazon Bedrock.
5. Bedrock analyzes the issue, diagnoses the likely cause, decides on a response, and plans an action.
6. Bedrock consults the knowledge base backed by DynamoDB and S3.
7. The chosen remediation is executed through AWS Step Functions.
8. Step Functions runs one of the available automated actions such as scaling, SSM, restart, patching, or cost optimization.
9. Incident outcomes are stored back into the knowledge base.
10. Dashboards, alerts, reports, and logs reflect both the issue and the remediation result.
11. The workflow ends when the incident is resolved and verification confirms recovery.

## Architecture strengths visible in the diagram

- Clear separation between detection, reasoning, remediation, and monitoring
- Event-driven design using EventBridge rather than tight point-to-point coupling
- Safe action pattern where Bedrock decides but Step Functions executes
- Feedback loop through DynamoDB and S3 so the agent can use historical context
- Explicit operator visibility through dashboards, alerts, and analytics

## Open points to confirm from the final design

- Which cloud source events are actually in scope for the hackathon demo
- Whether the knowledge base is retrieval-only or also updated after each incident
- How verification is implemented after remediation
- Which actions are fully automatic versus approval-gated
- Whether the cost optimization path is live in the demo or only described
