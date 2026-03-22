# CDK App

This folder contains the AWS CDK v2 app for the phase-1 hackathon demo.

## What it deploys

- Custom Amazon EventBridge bus for synthetic incidents
- Lambda triage function that gathers context and calls Amazon Bedrock
- AWS Step Functions workflow for phase-1 orchestration
- DynamoDB table for incident history
- S3 bucket for domain knowledge and reasoning artifacts
- SNS topic for operator notifications

## Safe default

Live remediation is disabled by default. The first deploy is meant to prove the autonomous loop safely:

`synthetic event -> triage -> Bedrock decision -> workflow -> SNS + DynamoDB/S3`

Use Node.js 20 or newer when running the CDK CLI to avoid current end-of-life warnings from newer CDK releases.

To turn on live remediation later, deploy with:

```bash
cdk deploy \
  --profile YOUR_PROFILE \
  -c enableLiveRemediation=true
```
