from dataclasses import dataclass

from aws_cdk import aws_s3
from aws_cdk import Environment
from aws_cdk import Fn
from aws_cdk import pipelines
from aws_cdk import Stack
from aws_cdk.pipelines import CodePipeline
from aws_cdk.pipelines import CodePipelineSource
from aws_cdk.pipelines import ShellStep
from constructs import Construct

from pipeline.base_infrastructure import BaseInfrastructureStage
from pipeline.video_storage import VideoStorageStage


@dataclass
class Account:
    name: str
    id: str
    region: str
    logging_bucket_arn: str = None  # type: ignore[assignment]
    manually_approve_change: bool = False


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

        self._create_pipeline()
        self._create_base_infrastructure(accounts)
        self._create_video_management(accounts["dev"])
        self._create_video_management(accounts["prod"])

    def _create_pipeline(self):
        self.pipeline = CodePipeline(
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

    def _create_base_infrastructure(self, accounts: dict):
        for account in accounts.values():
            stage = BaseInfrastructureStage(
                self,
                f"{account.name}-BaseInfrastructure",
                env=Environment(account=account.id, region=account.region),
            )
            self.pipeline.add_stage(stage)
            account.logging_bucket_arn = stage.logging_bucket_arn

    def _create_video_management(self, account: Account):
        buckets = self._create_video_storage(account)
        self._create_video_processing(account, buckets)

    def _create_video_storage(self, account: Account) -> dict:
        stage = VideoStorageStage(
            self,
            f"{account.name}",
            env=Environment(account=account.id, region=account.region),
            logging_bucket=aws_s3.Bucket.from_bucket_arn(
                self,
                id=f"{account.name}LoggingBucket",
                bucket_arn=Fn.import_value(account.logging_bucket_arn),
            ),
        )
        if account.manually_approve_change:
            pre = [pipelines.ManualApprovalStep(f"PromoteTo{account.name}")]
        else:
            pre = None
        self.pipeline.add_stage(stage, pre=pre)
        buckets = {
            "upload": stage.upload_bucket_arn,
            "published": stage.publish_bucket_arn,
        }
        return buckets

    def _create_video_processing(self, account: Account, buckets: dict):
        pass
