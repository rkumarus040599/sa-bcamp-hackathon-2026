# Infrastructure Notes

Use this folder for deployment plans, IaC, environment-specific decisions, and service inventories.

Suggested layout if the project grows:

- `terraform/`
- `cloudformation/`
- `scripts/`
- `environments/`

Current demo scaffold:

- `cdk/`: Python AWS CDK v2 app for the phase-1 deployable demo
- `step-functions/remediation-workflow.asl.json`: starter remediation state machine
- `lambda/triage_agent/`: Lambda scaffold that enriches the incident, queries the knowledge base, calls Bedrock, and starts remediation
- `lambda/remediation_verifier/`: Lambda scaffold that verifies recovery and writes the outcome back into the knowledge base
