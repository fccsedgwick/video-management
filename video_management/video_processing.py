from aws_cdk import aws_iam
from aws_cdk import aws_lambda_destinations
from aws_cdk import aws_s3 as s3
from cdk_serverless_clamscan import ServerlessClamscan
from cdk_serverless_clamscan import ServerlessClamscanLoggingProps
from constructs import Construct

from video_management.lambda_packaging import PackageLambda


class VideoProcessing:
    def __init__(
        self,
        construct: Construct,
        logging_bucket: s3.Bucket,
        upload_bucket: s3.Bucket,
        publish_bucket: s3.Bucket,
        publish_role: aws_iam.Role,
    ):

        self._construct = construct

        self._create_publish_lambda(
            publish_role=publish_role,
            upload_bucket=upload_bucket,
            publish_bucket=publish_bucket,
        )
        self._create_clamscan(upload_bucket, logging_bucket=logging_bucket)

    def _create_publish_lambda(
        self,
        publish_role: aws_iam.Role,
        upload_bucket: s3.Bucket,
        publish_bucket: s3.Bucket,
    ):
        self.publish_lambda = PackageLambda(self._construct).create_function(
            lambda_location="video_management/lambda_functions/publish_lambda/",
            role=publish_role,
            function_name="publish_lambda",
        )
        self.publish_lambda.add_environment("SOURCE_BUCKET", upload_bucket.bucket_name)
        self.publish_lambda.add_environment("DEST_BUCKET", publish_bucket.bucket_name)

    def _create_clamscan(self, upload_bucket: s3.Bucket, logging_bucket: s3.Bucket):
        ServerlessClamscan(
            self._construct,
            "ClamScan",
            buckets=[upload_bucket],
            on_result=aws_lambda_destinations.LambdaDestination(self.publish_lambda),
            on_error=aws_lambda_destinations.LambdaDestination(self.publish_lambda),
            defs_bucket_access_logs_config=ServerlessClamscanLoggingProps(
                logs_bucket=logging_bucket, logs_prefix="ClamScan"
            ),
        )
