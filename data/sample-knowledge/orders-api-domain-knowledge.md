# Orders API Domain Knowledge

## Service summary

- Service name: `orders-api`
- Environment: `hackathon`
- Runtime: EC2 Auto Scaling group behind an application load balancer
- Auto Scaling group: `orders-api-asg`
- Primary log group: `/aws/ec2/orders-api/app`

## Normal operating profile

- Typical CPU range: 25% to 45%
- Scale-out threshold for demo: above 70% sustained for 2 minutes
- Recovery signal: CPU returns below 65% and alarm begins moving back toward `OK`

## Approved low-risk remediation rules

- If CPU is high across the ASG and there is no evidence of a broken deployment, prefer scaling out.
- If one host is unhealthy but fleet-wide CPU is normal, restart the specific service through SSM instead of scaling the fleet.
- If the agent lacks enough evidence to distinguish between saturation and application failure, notify operators instead of taking action.

## Known patterns

- Load-test spikes are usually resolved by increasing desired capacity by 1 or 2 instances.
- A recent deployment may explain new errors, but CPU-only saturation should still prefer scale-out for the demo.
- Cost optimization should remain advisory in the live demo unless explicitly rehearsed.

## Unsafe actions for the hackathon

- Database failover
- Security group mutation
- Destructive instance termination
- Any rollback that has not been pre-approved

