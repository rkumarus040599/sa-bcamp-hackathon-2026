# Solutions Architect Hackathon Workspace

This repository is now set up as a practical workspace for planning, shaping, and demoing a Solutions Architect Hackathon project.

The current concept is an agentic AI system that behaves like a virtual cloud engineer for AWS applications: it monitors signals, diagnoses incidents, and executes safe self-healing actions through an event-driven workflow.

## What is here

- `apps/hackathon-hub/`: a lightweight static project hub you can open locally for team alignment and demo framing
- `docs/`: working docs for the brief, architecture, prompts, and runbooks
- `docs/demo-scenario.md`: the current hackathon demo storyline
- `docs/implementation/`: polished demo flow, service mapping, and implementation guidance
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
5. Use [`docs/implementation/demo-flow.md`](./docs/implementation/demo-flow.md) and [`docs/implementation/service-mapping.md`](./docs/implementation/service-mapping.md) as the build blueprint.
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

Notes:

- `foundationModelId` is configurable because Bedrock model availability can vary by account and region.
- `enableLiveRemediation=false` is the default and is the recommended phase-1 setting.
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
