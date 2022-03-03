#!/usr/bin/env python3
from os import environ

import aws_cdk as cdk
from dotenv import load_dotenv

from common_pipeline.base_infrastructure import BaseInfrastructureStack
from video_management.video_management_stack import VideoManagementStack

load_dotenv("app.env")

app = cdk.App()

base_infrastructure_stack = BaseInfrastructureStack(
    app,
    "BaseInfrastructureStack",
    description="Contains the AWS services which will be used across various stacks",
    env=cdk.Environment(account=environ["CDK_DEFAULT_ACCOUNT"], region="us-east-2"),
)

video_storage_stack = VideoManagementStack(
    app,
    "VideoManagementStack",
    description="Services used for ingesting, processing and posting videos to a site",
    logging_bucket=base_infrastructure_stack.logging_bucket,
    env=cdk.Environment(account=environ["CDK_DEFAULT_ACCOUNT"], region="us-east-2"),
)

app.synth()
