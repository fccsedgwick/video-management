from aws_cdk import aws_s3 as s3
from aws_cdk import Stack
from constructs import Construct

from video_management.video_storage import VideoStorage


class VideoManagementStack(Stack):
    def __init__(
        self, scope: Construct, construct_id: str, logging_bucket: s3.Bucket, **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        video_storage = VideoStorage(self, logging_bucket)
