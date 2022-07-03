from aws_cdk import aws_cloudfront
from aws_cdk import aws_cloudfront_origins
from aws_cdk import aws_iam as iam
from aws_cdk import aws_s3 as s3
from constructs import Construct


class VideoStorage:
    def __init__(self, construct: Construct, logging_bucket: s3.Bucket):
        self._construct = construct

        self._create_iam()
        # self._create_upload_bucket(logging_bucket)
        self._create_publish_bucket(logging_bucket)
        self._create_cdn(logging_bucket)
        # self._create_ssm_parameters()

    def _create_iam(self):
        user = iam.User(self._construct, "s3_upload_user")
        self.upload_role = iam.Role(self._construct, "s3_upload_role", assumed_by=user)

    def _create_publish_bucket(self, logging_bucket: s3.Bucket):
        self.publish_bucket = s3.Bucket(
            self._construct,
            "PublishedVideos",
            object_ownership=s3.ObjectOwnership.BUCKET_OWNER_ENFORCED,
            enforce_ssl=True,
            server_access_logs_bucket=logging_bucket,
            server_access_logs_prefix="s3-publish-bucket-videos",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
        )

        self.publish_bucket.grant_write(self.upload_role)

    def _create_cdn(self, logging_bucket: s3.Bucket):
        self.cloudfront = aws_cloudfront.Distribution(
            self._construct,
            "PublishedBucketCDN",
            default_behavior=aws_cloudfront.BehaviorOptions(
                origin=aws_cloudfront_origins.S3Origin(self.publish_bucket)
            ),
            enable_logging=True,
            log_bucket=logging_bucket,
            log_file_prefix="cdn/",
        )
