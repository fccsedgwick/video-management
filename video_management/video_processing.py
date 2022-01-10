# from aws_cdk import aws_lambda_destinations as lambda_destinations
from aws_cdk import aws_iam
from aws_cdk import Stack
from aws_cdk import Stage
from cdk_serverless_clamscan import ServerlessClamscan
from constructs import Construct

from video_management.lambda_packaging import PackageLambda
from video_management.models import AccountBuckets

# from lambda_packaging import PackageLambda


class VideoProcessingStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        buckets: AccountBuckets,
        publish_role: aws_iam.Role,
        **kwargs,
    ):
        super().__init__(scope, construct_id, **kwargs)

        self._create_publish_lambda(publish_role=publish_role, buckets=buckets)
        self._create_clamscan(buckets)

    def _create_publish_lambda(
        self, publish_role: aws_iam.Role, buckets: AccountBuckets
    ):
        # publish_lambda = PackageLambda(self).create_function(
        #     lambda_location="../lambda/aws_video_processing/", role=publish_role
        # )
        # publish_lambda.add_environment("SOURCE_BUCKET", buckets.upload)
        # publish_lambda.add_environment("DEST_BUCKET", buckets.publish)
        pass

    def _create_clamscan(self, buckets: AccountBuckets):
        pass
        # ServerlessClamscan(
        #     self,
        #     "ClamScan",
        #     buckets=[self.buckets.upload],
        #     on_result=lambda_destinations.LambdaDestination(publish_lambda),
        #     on_error=lambda_destinations.LambdaDestination(publish_lambda),
        # )


class VideoProcessingStage(Stage):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        buckets: AccountBuckets,
        publish_role: aws_iam.Role,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        video_storage_stack = VideoProcessingStack(
            self, "VideoStorageStack", buckets=buckets, publish_role=publish_role
        )
