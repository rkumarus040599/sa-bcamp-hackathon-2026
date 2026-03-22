# Demo Scenario

This is the current hackathon demonstration plan for the self-healing AWS operations agent.

## Demo goal

Show that the system can behave like a virtual cloud engineer: it notices a runtime issue, investigates it with context, executes a safe remediation, and verifies that the application recovered.

## Primary scenario

### CPU spike on the application tier

An AWS-hosted application experiences a sudden CPU spike that causes degraded response times. The system detects the anomaly, analyzes logs and runtime context, determines that the workload needs more capacity, and automatically scales the infrastructure to recover.

## Demo flow

1. Start with the application in a healthy baseline state.
2. Introduce synthetic load or a simulated incident that drives CPU utilization above the defined threshold.
3. Show the CloudWatch alarm or event entering the incident workflow.
4. Show the agent gathering context from metrics, logs, and resource state.
5. Present the agent's reasoning summary and selected remediation action.
6. Execute the remediation, such as increasing Auto Scaling capacity or service desired count.
7. Verify that CPU drops or health stabilizes after the action.
8. Close with a human-readable incident summary that captures the cause, action, and result.

## What judges should see

- Clear signal that the issue was detected automatically
- Evidence that the agent did more than static alerting
- A bounded and safe remediation path
- Visible improvement in application health after the fix
- A short operator-ready summary at the end

## Fallback plan if live automation is risky

If the full closed loop is not ready, keep the detection and diagnosis flow real, then trigger a controlled pre-approved remediation action with a visible verification step. That still demonstrates the core value without overpromising autonomy.

## Secondary scenarios for narration only

- Repeated error logs leading to an application restart or rollback
- Underutilized resources leading to a cost-optimization recommendation
- Memory pressure or unhealthy tasks leading to service recovery actions
