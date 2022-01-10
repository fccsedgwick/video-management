#!/usr/bin/env python3
import aws_cdk as cdk
from dotenv import load_dotenv

from pipeline import PipelineStack

load_dotenv("app.env")

app = cdk.App()
PipelineStack(
    app,
    "VideoManagementPipelineStack",
    env=cdk.Environment(account="837883156427", region="us-east-2"),
)

app.synth()
