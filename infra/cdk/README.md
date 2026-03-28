# CDK App

This folder contains the AWS CDK v2 app for the phase-1 hackathon demo.

## What it deploys

- Custom Amazon EventBridge bus for synthetic incidents
- Lambda triage function that gathers context and calls Amazon Bedrock
- AWS Step Functions workflow for phase-1 orchestration
- DynamoDB table for incident history
- S3 bucket for domain knowledge and reasoning artifacts
- SNS topic for operator notifications
- Optional demo EC2 Auto Scaling Group app tier for live scale-out remediation rehearsals

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

To provision the demo app tier as well, deploy with:

```bash
cdk deploy \
  --profile YOUR_PROFILE \
  -c deployDemoAppTier=true \
  -c enableLiveRemediation=true
```

Demo app-tier defaults:

- Auto Scaling Group name: `orders-api-asg`
- instance type: `t3.micro`
- min capacity: `1`
- desired capacity: `1`
- max capacity: `3`

You can override those values with:

```bash
cdk deploy \
  --profile YOUR_PROFILE \
  -c deployDemoAppTier=true \
  -c enableLiveRemediation=true \
  -c demoAutoScalingGroupName=orders-api-asg \
  -c demoInstanceType=t3.micro \
  -c demoMinCapacity=1 \
  -c demoDesiredCapacity=1 \
  -c demoMaxCapacity=3
```

The app-tier path creates a small public-only demo VPC with no NAT gateway so it does not depend on a default VPC in the target account.
