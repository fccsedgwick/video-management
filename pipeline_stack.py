from aws_cdk import Environment
from aws_cdk import Stack
from aws_cdk.pipelines import CodePipeline
from aws_cdk.pipelines import CodePipelineSource
from aws_cdk.pipelines import ManualApprovalStep
from aws_cdk.pipelines import ShellStep
from constructs import Construct

from models import Account
from solution import SolutionEnvironmentStage


class PipelineStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        accounts = {}
        accounts["dev"] = Account(name="dev", id="747096213102", region="us-east-2")
        accounts["prod"] = Account(
            name="prod",
            id="308828263283",
            region="us-east-2",
            manually_approve_change=True,
        )

        pipeline = CodePipeline(
            self,
            "Pipeline",
            cross_account_keys=True,
            synth=ShellStep(
                "Synth",
                input=CodePipelineSource.git_hub(
                    "fccsedgwick/video_management", "main"
                ),
                commands=[
                    "npm install -g aws-cdk",
                    "pipenv install",
                    "pipenv run cdk synth",
                ],
            ),
        )

        for account in accounts.values():
            stage = SolutionEnvironmentStage(
                self,
                f"{account.name}-{account.region}-SolutionEnvironment",
                env=Environment(account=account.id, region=account.region),
            )

            if account.manually_approve_change:
                pre = [ManualApprovalStep(f"PromoteTo{account.name}")]
            else:
                pre = None

            pipeline.add_stage(stage, pre=pre)
