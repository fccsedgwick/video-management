#!/usr/bin/env python3
from os import getenv

import aws_cdk as cdk
from dotenv import load_dotenv

from pipeline import PipelineStack

load_dotenv()

app = cdk.App()
PipelineStack(
    app,
    "MyPipelineStack",
    env=cdk.Environment(
        account=getenv("AWS_PIPELINE_ACCOUNT"), region=getenv("AWS_PIPELINE_REGION")
    ),
)

app.synth()
