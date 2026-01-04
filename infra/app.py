#!/usr/bin/env python3
import aws_cdk as cdk
from octivary_stack import OctivaryStack

app = cdk.App()

OctivaryStack(
    app,
    'OctivaryStack',
)

app.synth()
