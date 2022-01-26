from aws_cdk import aws_s3 as s3
from aws_cdk import Stack
from constructs import Construct

from video_management.video_posting import VideoPosting
from video_management.video_processing import VideoProcessing
from video_management.video_storage import VideoStorage


class VideoManagementStack(Stack):
    def __init__(
        self, scope: Construct, construct_id: str, logging_bucket: s3.Bucket, **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        video_storage = VideoStorage(self, logging_bucket)

        video_processing = VideoProcessing(
            self,
            logging_bucket=logging_bucket,
            upload_bucket=video_storage.upload_bucket,
            publish_bucket=video_storage.publish_bucket,
            publish_role=video_storage.publish_role,
        )

        video_publishing = VideoPosting(
            self, publish_bucket=video_storage.publish_bucket
        )
