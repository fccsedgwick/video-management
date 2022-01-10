from aws_cdk import aws_iam
from aws_cdk import aws_s3
from aws_cdk import Environment
from aws_cdk import Fn
from aws_cdk import pipelines
from aws_cdk import Stack
from aws_cdk.pipelines import CodePipeline
from aws_cdk.pipelines import CodePipelineSource
from aws_cdk.pipelines import ShellStep
from constructs import Construct

from video_management.base_infrastructure import BaseInfrastructureStage
from video_management.models import Account
from video_management.video_processing import VideoProcessingStage
from video_management.video_storage import VideoStorageStage


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

    def _create_pipeline(self) -> None:
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

    def _create_base_infrastructure(self, accounts: dict) -> None:
        for account in accounts.values():
            stage = BaseInfrastructureStage(
                self,
                f"{account.name}-BaseInfrastructure",
                env=Environment(account=account.id, region=account.region),
            )
            self.pipeline.add_stage(stage)
            account.buckets.logging = aws_s3.Bucket.from_bucket_arn(
                self,
                id=f"{account.name}LoggingBucket",
                bucket_arn=Fn.import_value("loggingBucketARN"),
            )

    def _create_video_management(self, account: Account) -> None:
        self._create_video_storage(account)
        self._create_video_processing(account)

    def _create_video_storage(self, account: Account) -> None:
        stage = VideoStorageStage(
            self,
            f"{account.name}-VideoStorage",
            env=Environment(account=account.id, region=account.region),
            # next line needs a bucket, gets a bucket interface
            buckets=account.buckets,
        )
        if account.manually_approve_change:
            pre = [pipelines.ManualApprovalStep(f"PromoteTo{account.name}")]
        else:
            pre = None
        self.pipeline.add_stage(stage, pre=pre)
        account.buckets.upload = aws_s3.Bucket.from_bucket_arn(  # type: ignore[assignment]
            self,
            id=f"{account.name}-UploadBucket",
            bucket_arn=Fn.import_value("uploadBucketARN"),
        )
        account.buckets.publish = aws_s3.Bucket.from_bucket_arn(  # type: ignore[assignment]
            self,
            id=f"{account.name}-PublishBucket",
            bucket_arn=Fn.import_value("publishBucketARN"),
        )
        account.publish_role = aws_iam.Role.from_role_arn(  # type: ignore[assignment]
            self,
            id=f"{account.name}-PublishRole",
            role_arn=Fn.import_value("publishRoleARN"),
        )

    def _create_video_processing(self, account: Account) -> None:
        stage = VideoProcessingStage(
            self,
            f"{account.name}-VideoProcessing",
            env=Environment(account=account.id, region=account.region),
            buckets=account.buckets,
            publish_role=account.publish_role,
        )
        self.pipeline.add_stage(stage)
