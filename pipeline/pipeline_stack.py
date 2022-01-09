from dataclasses import dataclass

import aws_cdk as cdk
from aws_cdk.pipelines import CodePipeline
from aws_cdk.pipelines import CodePipelineSource
from aws_cdk.pipelines import ShellStep
from base_infrastructure import BaseInfrastructureStage
from constructs import Construct


@dataclass
class Account:
    id: str
    region: str


accounts = []
accounts.append(Account(id="747096213102", region="us-east-2"))
accounts.append(Account(id="308828263283", region="us-east-2"))


class PipelineStack(cdk.Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        pipeline = CodePipeline(
            self,
            "Pipeline",
            synth=ShellStep(
                "Synth",
                input=CodePipelineSource.git_hub(
                    "fccsedgwick/video_management", "main"
                ),
                commands=[
                    "npm install -g aws-cdk",
                    "python -m pip install pipenv",
                    "pipenv install",
                    "pipenv run cdk synth",
                ],
            ),
        )

        for account in accounts:
            pipeline.add_stage(
                BaseInfrastructureStage(
                    self,
                    "base_infrastructure",
                    env=cdk.Environment(account=account.id, region=account.region),
                )
            )
