from aws_cdk import Environment
from aws_cdk import Stack
from aws_cdk.pipelines import ManualApprovalStep
from aws_cdk.pipelines import ShellStep
from cdk_pipelines_github import GitHubWorkflow
from constructs import Construct

from common_pipeline.models import Account
from common_pipeline.solution import SolutionEnvironmentStage


class PipelineStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        accounts = {}
        accounts["dev"] = Account(name="dev", id="747096213102", region="us-east-2")
        accounts["prod"] = Account(
            name="prod",
            id="308828263283",
            region="us-east-2",
        )

        pipeline = GitHubWorkflow(
            self,
            "Pipeline",
            synth=ShellStep(
                "Synth",
                commands=[
                    "npm install -g aws-cdk",
                    "pipenv install",
                    "pipenv run cdk synth",
                ],
            ),
        )

        for account in accounts.values():
            pipeline.git_hub_action_role_arn = (
                f"arn:aws:iam::{account.id}:role/GitHubActionRole"
            )
            stage = SolutionEnvironmentStage(
                self,
                f"{account.name}-{account.region}-SolutionEnvironment",
                env=Environment(account=account.id, region=account.region),
            )

            pipeline.add_stage(stage)
