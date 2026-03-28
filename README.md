# Solutions Architect Hackathon Workspace

This repository is now set up as a practical workspace for planning, shaping, and demoing a Solutions Architect Hackathon project.

The current concept is an agentic AI system that behaves like a virtual cloud engineer for AWS applications: it monitors signals, diagnoses incidents, and executes safe self-healing actions through an event-driven workflow.

## What is here

- `apps/hackathon-hub/`: a lightweight static project hub you can open locally for team alignment and demo framing
- `docs/`: working docs for the brief, architecture, prompts, and runbooks
- `docs/demo-scenario.md`: the current hackathon demo storyline
- `docs/implementation/`: polished demo flow, service mapping, and implementation guidance
- `docs/implementation/aws-pipeline-flow.md`: the end-to-end AWS event pipeline flowchart for the deployed demo
- `docs/implementation/judge-slide-flow.md`: the simplified one-slide version for judges and short demos
- `docs/implementation/prestaged-remediation-runbook.md`: the click-by-click runbook for the pre-executed remediation demo
- `templates/`: reusable templates for ADRs and demo prep
- `infra/`: a landing zone for IaC, deployment notes, and environment setup
- `infra/cdk/`: the AWS CDK v2 app for the phase-1 deployable demo
- `data/`: a place for sample datasets, fixtures, and source notes
- `arch-diagrams/`: existing architecture diagrams and image exports
- `sa-hackathon.code-workspace`: an editor workspace file for opening the repo as a focused project

## Quick start

1. Open [`sa-hackathon.code-workspace`](./sa-hackathon.code-workspace) in VS Code if you want a ready-made workspace.
2. Review [`docs/brief.md`](./docs/brief.md) for the current problem statement, users, and expected solution.
3. Refine the technical approach in [`docs/architecture/solution-outline.md`](./docs/architecture/solution-outline.md).
4. Use [`docs/demo-scenario.md`](./docs/demo-scenario.md) to keep the build aligned to the story we will show judges.
5. Use [`docs/implementation/demo-flow.md`](./docs/implementation/demo-flow.md), [`docs/implementation/service-mapping.md`](./docs/implementation/service-mapping.md), [`docs/implementation/aws-pipeline-flow.md`](./docs/implementation/aws-pipeline-flow.md), [`docs/implementation/judge-slide-flow.md`](./docs/implementation/judge-slide-flow.md), and [`docs/implementation/prestaged-remediation-runbook.md`](./docs/implementation/prestaged-remediation-runbook.md) as the build and rehearsal blueprint.
6. Drop updated diagrams into [`arch-diagrams/`](./arch-diagrams/).
7. Preview the starter project hub by opening [`apps/hackathon-hub/index.html`](./apps/hackathon-hub/index.html) in a browser.

If you want a local static server instead of opening the file directly, run:

```bash
python3 -m http.server 4173 --directory apps/hackathon-hub
```

Then visit `http://localhost:4173`.

## Deploy the phase-1 demo

The first deployable slice is intentionally small and safe:

`synthetic incident -> EventBridge -> Lambda triage -> Bedrock decision -> Step Functions -> SNS + DynamoDB/S3`

Live remediation is disabled by default so teammates can deploy this stack in their own AWS accounts without touching real infrastructure changes.

### Prerequisites

- AWS CLI v2 installed and configured
- AWS CDK v2 installed
- Node.js 20 or newer recommended for the CDK CLI
- Python 3 available locally
- An AWS profile with access to deploy Lambda, EventBridge, Step Functions, DynamoDB, S3, SNS, IAM, CloudWatch, Logs, and Bedrock
- Amazon Bedrock model access in the target region

### Clone and set up locally

From the repo root:

```bash
cd infra/cdk
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Bootstrap and deploy

Replace `YOUR_PROFILE` with your AWS CLI profile.

```bash
cd infra/cdk
source .venv/bin/activate
cdk bootstrap --profile YOUR_PROFILE
cdk deploy --profile YOUR_PROFILE
```

Optional deployment overrides:

```bash
cdk deploy --profile YOUR_PROFILE \
  -c foundationModelId=openai.gpt-oss-120b-1:0 \
  -c notificationEmail=you@example.com \
  -c enableLiveRemediation=false
```

To deploy the tiny demo app tier that the agent can later scale from `1` to `3`, use:

```bash
cdk deploy --profile YOUR_PROFILE \
  -c deployDemoAppTier=true \
  -c enableLiveRemediation=true
```

Notes:

- `foundationModelId` is configurable because Bedrock model availability can vary by account and region.
- `enableLiveRemediation=false` is the default and is the recommended phase-1 setting.
- `deployDemoAppTier=false` is the default so teammates do not incur EC2 charges unless they explicitly opt in.
- The optional demo app tier provisions an SSM-enabled `t3.micro` Auto Scaling Group named `orders-api-asg` with `min=1`, `desired=1`, and `max=3`.
- The demo app-tier deploy path creates a small public-only VPC with no NAT gateway, so it works even in accounts without a default VPC.
- The stack is account-agnostic, so teammates can deploy it to their own AWS accounts after cloning the repo.

### Send a synthetic incident

After deployment, from the repo root:

```bash
aws events put-events \
  --profile YOUR_PROFILE \
  --region YOUR_REGION \
  --entries file://data/sample-events/cpu-spike-custom-event.json
```

That injects a phase-1 demo incident into the custom event bus and starts the autonomous workflow.

### Useful follow-up commands

```bash
cd infra/cdk
source .venv/bin/activate
cdk synth --profile YOUR_PROFILE
cdk diff --profile YOUR_PROFILE
cdk destroy --profile YOUR_PROFILE
```

### Tear everything down

To remove the deployed demo stack and stop ongoing AWS charges, run:

```bash
./scripts/destroy_hackathon_resources.sh --profile YOUR_PROFILE --region YOUR_REGION
```

That removes the main `AutonomousOpsPhaseOneStack` resources. If you also want to remove the shared CDK bootstrap stack and you are sure no other CDK apps use it, add `--include-bootstrap`.

## Run the deployed demo

After the phase-1 stack is deployed, teammates can run the same demo flow in their own AWS accounts.

For the polished judge-facing version where you pre-run a real remediation and then walk through the evidence, use [`docs/implementation/prestaged-remediation-runbook.md`](./docs/implementation/prestaged-remediation-runbook.md).

For a simple end-to-end view of how the incident moves through AWS services, open [`docs/implementation/aws-pipeline-flow.md`](./docs/implementation/aws-pipeline-flow.md).

For a single-slide, judge-friendly version with fewer boxes and a short speaking track, open [`docs/implementation/judge-slide-flow.md`](./docs/implementation/judge-slide-flow.md).

### What the phase-1 demo proves

This deployment demonstrates the safe autonomous-ops loop:

`synthetic incident -> EventBridge -> Lambda triage -> Bedrock decision -> Step Functions -> DynamoDB/S3 writeback`

By default, the stack runs in `notify-only-safe-mode`, which means it proves the reasoning and workflow path without making live infrastructure changes.

### Open these AWS console pages first

In your target region, open:

- CloudFormation for `AutonomousOpsPhaseOneStack`
- EventBridge for the deployed custom event bus
- Step Functions for the deployed remediation workflow
- Lambda for the deployed triage function
- DynamoDB for the deployed incident table
- S3 for the deployed knowledge bucket

You can get the exact deployed names from the CloudFormation stack outputs:

```bash
aws cloudformation describe-stacks \
  --stack-name AutonomousOpsPhaseOneStack \
  --profile YOUR_PROFILE \
  --region YOUR_REGION
```

### Confirm the clean starting state

Before triggering the incident:

- Step Functions should have no new execution for this run yet
- DynamoDB should have zero or only old historical incidents
- S3 should already contain the sample runbook in `runbooks/orders-api/`

### Trigger the incident

From the repo root:

```bash
aws events put-events \
  --profile YOUR_PROFILE \
  --region YOUR_REGION \
  --entries file://data/sample-events/cpu-spike-custom-event.json
```

This sends a synthetic CPU-spike style event into the custom EventBridge bus and starts the phase-1 autonomous workflow.

### What to show in the demo

1. Start at the CloudFormation outputs and point out that the stack is in safe phase-1 mode.
2. Show the knowledge bucket already contains the sample domain runbook.
3. Trigger the synthetic incident with `aws events put-events`.
4. Open Step Functions and show that a new execution appears for the remediation workflow.
5. Open the execution and explain that the system received the event, triaged the incident, called Bedrock, and chose a bounded next step.
6. Explain that phase 1 is intentionally deployed in `notify-only-safe-mode`, so it proves the agent loop without changing infrastructure.
7. Open DynamoDB and show that a new incident record has been written.
8. Open S3 and show that a new reasoning artifact appears under `incidents/reasoning/`.
9. If an SNS subscription was configured during deploy, show the notification that was produced.

### Suggested demo narration

- `We start from a clean baseline with the stack deployed and domain knowledge loaded.`
- `I inject a synthetic cloud incident into EventBridge.`
- `The triage Lambda gathers context and Bedrock decides on the safest action from the allowlist.`
- `Because this stack is in safe mode, it records the incident and publishes the recommendation path instead of mutating live infrastructure.`
- `The system writes the outcome back to the knowledge base so the next incident starts with more memory.`

### What success looks like

The demo is successful if you can show:

- the synthetic event was accepted
- a Step Functions execution started
- the workflow completed successfully
- a new incident record appeared in DynamoDB
- a new artifact appeared in S3

### Optional live commands for verification

List recent workflow executions:

```bash
aws stepfunctions list-executions \
  --state-machine-arn YOUR_STATE_MACHINE_ARN \
  --profile YOUR_PROFILE \
  --region YOUR_REGION \
  --max-results 5
```

Count current incident records:

```bash
aws dynamodb scan \
  --table-name YOUR_INCIDENT_TABLE_NAME \
  --profile YOUR_PROFILE \
  --region YOUR_REGION \
  --select COUNT
```

List reasoning artifacts:

```bash
aws s3 ls s3://YOUR_KNOWLEDGE_BUCKET/incidents/reasoning/ \
  --profile YOUR_PROFILE \
  --region YOUR_REGION
```

### What to commit

Yes, you can check this code into GitHub for teammates to use in their own AWS accounts.

Safe to commit:

- source code
- CDK app files
- documentation
- sample events
- sample knowledge files

Do not commit:

- AWS credentials
- `.venv/`
- `cdk.out/`
- any local secrets or environment files

## Suggested working rhythm

- Capture the core customer problem in the brief first.
- Keep the architecture doc and diagram in sync as the solution sharpens.
- Save prompts, evaluation ideas, and operating notes in `docs/` so the final submission is reproducible.
- Use the demo script template early so the build stays aligned to the story you want to tell.
