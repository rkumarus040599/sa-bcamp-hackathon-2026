#!/usr/bin/env python3
import os

import aws_cdk as cdk

from autonomous_ops_cdk.phase_one_stack import AutonomousOpsPhaseOneStack


app = cdk.App()

AutonomousOpsPhaseOneStack(
    app,
    "AutonomousOpsPhaseOneStack",
    env=cdk.Environment(
        account=os.getenv("CDK_DEFAULT_ACCOUNT"),
        region=os.getenv("CDK_DEFAULT_REGION"),
    ),
)

app.synth()

