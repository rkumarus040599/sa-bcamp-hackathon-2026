# Polished Demo Flow

This is the judge-facing demonstration script for the `Autonomous Cloud Operations Agent`.

## Demo promise

Show a believable closed loop on AWS:

1. An operational problem appears.
2. The system detects it without human polling.
3. The agent gathers context and reasons about the issue.
4. The system executes a bounded remediation automatically.
5. Recovery is verified.
6. The outcome is written back into the knowledge base for future incidents.

## Primary demo path

### Scenario

An application tier running in an EC2 Auto Scaling group experiences a CPU spike that pushes response times higher than normal.

### Why this scenario works

- It is easy to explain in business terms.
- It uses AWS-native observability and remediation services.
- It gives the audience a visible before-and-after signal.
- It fits the architecture diagram cleanly.

## Demo setup

- Application: a simple web service running on EC2 behind an Auto Scaling group
- Monitoring: CloudWatch alarm on CPU utilization and optional latency signal
- Event ingestion: Amazon EventBridge rule for the alarm state change
- Agent entry point: AWS Lambda triage function
- Reasoning engine: Amazon Bedrock using a structured prompt plus domain knowledge
- Knowledge base: DynamoDB for incident history and S3 for runbooks and artifacts
- Remediation: AWS Step Functions invoking `UpdateAutoScalingGroup`
- Verification: CloudWatch metrics plus alarm-state recovery check
- Operator output: SNS notification and CloudWatch dashboard view

## Live walkthrough

### 1. Show healthy baseline

Start on a CloudWatch dashboard that shows:

- CPU below alarm threshold
- steady request latency
- the Auto Scaling group at its normal desired capacity

Narration:

`This is the normal state. The application is healthy, the ASG is stable, and no human operator is touching anything.`

### 2. Introduce the incident

Trigger synthetic load or inject a prepared EventBridge event that represents the CPU spike.

Narration:

`Now the application tier is under stress. In a real environment this is where teams usually get paged and start digging through dashboards and logs.`

### 3. Show detection through the event layer

Highlight that the alarm changes to `ALARM` and EventBridge receives the event.

Narration:

`CloudWatch detects the abnormal condition and EventBridge routes the incident into the autonomous operations workflow.`

### 4. Show the agent thinking

Display the Lambda triage result or a rendered reasoning summary that includes:

- what signal triggered the incident
- recent metrics and logs reviewed
- any recent change context from CloudTrail
- the diagnosis
- the selected remediation

Narration:

`The agent is not just relaying an alert. It is correlating telemetry, checking past patterns, and deciding on an approved action.`

### 5. Show the remediation workflow

Open the Step Functions execution and show the scale-out branch running.

Narration:

`The model does not get direct unrestricted control. It selects an action, and Step Functions executes the allowed remediation path.`

### 6. Show recovery verification

Return to CloudWatch and show:

- desired capacity increased
- CPU trending downward
- alarm returning toward `OK`

Narration:

`The workflow waits for stabilization, verifies the environment, and confirms that the remediation improved the service state.`

### 7. Show memory written back to the system

Display the incident history record in DynamoDB or the artifact in S3.

Narration:

`The incident outcome is written back into the knowledge base so the next remediation cycle starts smarter.`

### 8. Close with operator visibility

Show the SNS summary or operator-facing incident record.

Narration:

`Operators still stay in control. The system is autonomous, but it remains observable, auditable, and bounded.`

## Fallback mode

If live load generation is unstable, use a synthetic custom EventBridge event that carries the same incident payload. Keep the Bedrock reasoning, Step Functions execution, and verification screens real so the story remains credible.

## What to pre-stage before the demo

- CloudWatch dashboard with baseline and recovery widgets
- one alarm already configured and visible
- one application ASG with a small steady baseline capacity
- one Step Functions state machine deployed and tested
- one Lambda triage function with a prepared model prompt
- one DynamoDB table and one S3 bucket with sample incident history
- one SNS topic for operator notifications
- one custom EventBridge payload ready as a fallback trigger

## Suggested close

`Instead of waiting for a human to notice, investigate, decide, and act, this architecture lets AWS telemetry trigger an AI cloud engineer that can safely diagnose and remediate common incidents in real time.`

