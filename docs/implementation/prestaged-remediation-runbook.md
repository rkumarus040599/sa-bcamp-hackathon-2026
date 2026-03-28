# Pre-Staged Remediation Demo Runbook

This runbook is for the polished hackathon version of the demo where the remediation has already happened before the meeting, and the presenter walks through the evidence instead of waiting for EC2 scaling to finish live.

## Demo goal

Prove that the application can detect a CPU-spike incident, reason about it, execute a bounded remediation, verify the outcome, and write the result back into the knowledge base.

The key claim is:

`CPU spike detected -> Bedrock-guided decision -> Step Functions remediation -> Auto Scaling Group desired capacity increased -> recovery verified`

## What this runbook assumes

- You already ran one successful remediation before the demo.
- The Auto Scaling Group started at `desired=1` and was scaled to `desired=3` or started at `desired=2` and was scaled to `desired=4`.
- The deployed environment used live remediation for that pre-staged run.
- The evidence still exists in AWS:
  - completed Step Functions execution
  - Auto Scaling activity history
  - EC2 instances visible
  - DynamoDB incident records
  - S3 reasoning and verification artifacts
  - optional SNS notification

## Pre-demo setup checklist

Complete these before your team or judges join:

1. Confirm the demo ASG is at the baseline state before remediation.
2. Capture the `before` evidence while the ASG is still at baseline:
   - Auto Scaling Group details showing `desired=1`
   - EC2 instances page filtered to the demo ASG showing exactly one running instance
3. Save those baseline screenshots locally so you can show them during the demo after the environment has already scaled out.
4. Run the remediation ahead of time in the demo account.
5. Confirm the Auto Scaling Group now shows the scaled-out desired capacity.
6. Confirm the Step Functions execution completed successfully.
7. Confirm DynamoDB contains the incident record.
8. Confirm S3 contains both:
   - `incidents/reasoning/`
   - `incidents/verification/`
9. Capture the `after` evidence:
   - Auto Scaling Group details showing `desired=3`
   - Auto Scaling activity showing the scale-out
   - EC2 instances page filtered to the demo ASG showing three running instances
10. Keep one terminal open at the repo root in case you want to show the sample event payload.
11. Sign in to the AWS console in the correct region and pre-open all tabs listed below.
12. Disable browser tab groups or notifications that may distract during the walkthrough.
13. Save screenshots of the key screens as backup in case the console is slow.

## Exact setup steps to perform before the demo

Use this sequence when staging the demo in AWS.

1. Deploy the stack with live remediation and the demo app tier enabled.
2. Open `EC2 -> Auto Scaling groups -> orders-api-asg -> Details` and confirm:
   - `min=1`
   - `desired=1`
   - `max=3`
3. Open `EC2 -> Instances` filtered to `orders-api-asg` and confirm exactly one `t3.micro` instance is running.
4. Capture two screenshots:
   - `before-asg-details`
   - `before-ec2-instances`
5. Trigger the remediation before the meeting:
   - either send the synthetic CPU-spike event
   - or replay the already-tested incident path you trust most
6. Wait for the workflow to complete.
7. Open `Step Functions -> RemediationWorkflow -> Executions` and confirm the successful execution is visible.
8. Open `EC2 -> Auto Scaling groups -> orders-api-asg -> Details` and confirm `desired=3`.
9. Open `EC2 -> Auto Scaling groups -> orders-api-asg -> Activity` and confirm the successful scaling records are visible.
10. Open `EC2 -> Instances` filtered to `orders-api-asg` and confirm three running instances are visible.
11. Capture three more screenshots:
   - `after-step-functions-success`
   - `after-asg-details`
   - `after-ec2-instances`
12. Open `CloudWatch -> Alarms -> orders-api-asg-cpu-high` and confirm the alarm returned to `OK`.
13. Open `DynamoDB` and `S3` and confirm the reasoning and verification artifacts exist.
14. Keep the live AWS console tabs open on the `after` state, and keep the `before` screenshots ready in a local window or slide deck.

## Reliable pre-stage command sequence

If you want a repeatable setup flow before the demo, use this sequence with your own profile and region values.

### 1. Reset the ASG to the baseline

```bash
aws autoscaling update-auto-scaling-group \
  --profile YOUR_PROFILE \
  --region YOUR_REGION \
  --auto-scaling-group-name orders-api-asg \
  --desired-capacity 1
```

Wait until only one instance remains `InService`, then capture the `before` screenshots.

### 2. Create CPU pressure on the remaining instance

Use SSM to run the helper script that was baked into the demo instances:

```bash
aws ssm send-command \
  --profile YOUR_PROFILE \
  --region YOUR_REGION \
  --instance-ids YOUR_INSTANCE_ID \
  --document-name AWS-RunShellScript \
  --comment "Start CPU burn for autonomous ops demo" \
  --parameters commands='["sudo /opt/autonomous-ops-demo/start-cpu-burn.sh"]'
```

If you need stronger CPU pressure for the alarm to trip faster:

```bash
aws ssm send-command \
  --profile YOUR_PROFILE \
  --region YOUR_REGION \
  --instance-ids YOUR_INSTANCE_ID \
  --document-name AWS-RunShellScript \
  --comment "Increase CPU burn for autonomous ops demo" \
  --parameters commands='["for i in $(seq 1 8); do nohup bash -c '\''while true; do :; done'\'' >/var/log/autonomous-ops-cpu-burn-extra.log 2>&1 & done"]'
```

### 3. Trigger the incident path

Use the synthetic CPU-spike event:

```bash
aws events put-events \
  --profile YOUR_PROFILE \
  --region YOUR_REGION \
  --entries file://data/sample-events/cpu-spike-custom-event.json
```

### 4. Wait for the successful workflow and scale-out

Confirm:

- a successful Step Functions execution appears
- `orders-api-asg` moves to `desired=3`
- three EC2 instances are visible
- the alarm later returns to `OK`

### 5. Stop the temporary CPU burn after verification

Run the cleanup script on all instances in the Auto Scaling Group:

```bash
aws ssm send-command \
  --profile YOUR_PROFILE \
  --region YOUR_REGION \
  --targets Key=tag:aws:autoscaling:groupName,Values=orders-api-asg \
  --document-name AWS-RunShellScript \
  --comment "Stop CPU burn after autonomous ops demo pre-stage" \
  --parameters commands='["sudo /opt/autonomous-ops-demo/stop-cpu-burn.sh"]'
```

After that, keep the environment in the `after` state for the actual presentation.

## Tabs to open before the demo

Open these tabs in this order so the story flows left to right through the architecture:

1. Local image or slide window with `before-asg-details` and `before-ec2-instances`
2. `Step Functions -> State machines -> RemediationWorkflow -> Executions`
3. `EC2 -> Auto Scaling groups -> your demo ASG -> Details`
4. `EC2 -> Auto Scaling groups -> your demo ASG -> Activity`
5. `EC2 -> Instances` filtered to the demo Auto Scaling Group
6. `CloudWatch -> Alarms`
7. `DynamoDB -> Tables -> IncidentHistoryTable -> Explore table items`
8. `S3 -> Knowledge bucket -> incidents/reasoning/`
9. `S3 -> Knowledge bucket -> incidents/verification/`
10. Optional: `SNS` or your email inbox if you configured notifications

## Resource names to have ready

If you need to recover names quickly, use the stack outputs from CloudFormation first. Have these written down before the demo:

- stack name: `AutonomousOpsPhaseOneStack`
- EventBridge bus name
- Step Functions state machine name or ARN
- triage Lambda function name
- incident DynamoDB table name
- knowledge S3 bucket name
- demo Auto Scaling Group name
- CloudWatch alarm name

## Presenter click path

This is the exact recommended click order during the demo.

### 1. Before screenshots

Open the saved `before-asg-details` and `before-ec2-instances` screenshots.

Call out:

- the application tier started from a known baseline
- the Auto Scaling Group was at `desired=1`
- only one EC2 instance was running before the incident

Suggested line:

`I pre-ran the remediation before the demo to save time. This is the baseline state: one instance serving the application tier before the CPU spike response was triggered.`

### 2. Step Functions execution

Open `Step Functions -> State machines -> RemediationWorkflow -> Executions`.

Show:

- the successful execution that matches the incident timestamp
- the `scale_out_asg` decision
- successful workflow completion

Suggested line:

`This is the completed autonomous remediation run. The workflow received the incident, selected the scale-out path, and completed successfully.`

### 3. Auto Scaling Group details

Open `EC2 -> Auto Scaling groups -> your demo ASG -> Details`.

Show:

- minimum size
- desired capacity
- maximum size
- the post-remediation desired capacity

Suggested line:

`This is the after state. The application tier moved from the baseline of 1 instance to the recovery target of 3 instances.`

### 4. Auto Scaling activity

Open the `Activity` tab for the same Auto Scaling Group.

Show:

- the scaling activity record
- timestamp
- successful status

Suggested line:

`This is the proof that AWS executed the scale-out action, not just a recommendation.`

### 5. EC2 instances after remediation

Open `EC2 -> Instances` filtered to the demo Auto Scaling Group.

Show:

- the instance count after remediation
- the new instances in `running` state
- the launch times that line up with the incident window

Suggested line:

`This is the after view of the EC2 fleet. You can see the additional instances that were launched as part of the remediation.`

### 6. CloudWatch alarm

Open `CloudWatch -> Alarms` and click the CPU alarm for the demo ASG or app tier.

Show:

- alarm name
- alarm state history
- the transition into `ALARM`
- the later return to `OK`

Suggested line:

`CloudWatch detected the abnormal CPU condition, and after the scale-out the alarm returned to OK, so the system verified recovery.`

### 7. DynamoDB incident history

Open `DynamoDB -> Tables -> IncidentHistoryTable -> Explore table items`.

Show:

- the incident record
- service name
- incident ID
- status
- payload summary if visible

Suggested line:

`The system records operational memory in DynamoDB so future incidents can use prior context instead of starting from zero.`

### 8. S3 reasoning artifact

Open `S3 -> Knowledge bucket -> incidents/reasoning/`.

Show:

- the reasoning artifact for the incident
- timestamped object name

Suggested line:

`This artifact captures the decision context and reasoning trail that led to the remediation choice.`

### 9. S3 verification artifact

Open `S3 -> Knowledge bucket -> incidents/verification/`.

Show:

- the verification artifact for the same incident
- the resolution summary

Suggested line:

`After the action completed, the system verified the outcome and stored the result for future use.`

### 10. Optional SNS or inbox view

If notifications are configured, open the notification destination.

Show:

- recommendation or resolution notification
- timestamp alignment with the same incident

Suggested line:

`Operators stay informed throughout the process, but they are no longer doing the entire diagnose-and-remediate loop manually.`

## Short demo script

Use this version if you only have two to three minutes:

1. Show the `before` screenshots.
2. Show the Step Functions execution.
3. Show the Auto Scaling Group details and activity.
4. Show the `after` EC2 instances.
5. Show the CloudWatch alarm back at `OK`.
6. Close with DynamoDB or S3 writeback.

Short close:

`This demo shows an agentic AWS operations pattern where an incident is detected, analyzed, remediated, verified, and written back into operational memory with a controlled execution path.`

## Backup plan if a console page is slow

If the console becomes slow, prioritize these screens:

1. Step Functions execution
2. Auto Scaling Group details
3. Auto Scaling activity
4. EC2 instances after remediation
5. CloudWatch alarm

That sequence is enough to prove the remediation occurred.

## Rehearsal checklist

- Rehearse the full flow once with a timer.
- Keep every console tab pinned in the order listed above.
- Set each AWS console tab to the same time range where possible.
- Write down the before and after capacity numbers on a note.
- Keep one backup screenshot for:
  - before ASG details
  - before EC2 instances
  - Step Functions execution
  - Auto Scaling activity
  - after EC2 instances
  - CloudWatch alarm
