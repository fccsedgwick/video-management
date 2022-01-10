import json
from os import getenv

from aws_cdk import aws_iam as iam
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_ssm as ssm
from aws_cdk import CfnOutput
from aws_cdk import RemovalPolicy
from aws_cdk import Stack
from aws_cdk import Stage
from constructs import Construct


class VideoStorageStack(Stack):
    def __init__(
        self, scope: Construct, construct_id: str, logging_bucket: s3.Bucket, **kwargs
    ):
        super().__init__(scope, construct_id, **kwargs)

        user = iam.User(self, "s3_upload_user")
        upload_role = iam.Role(self, "s3_upload_role", assumed_by=user)
        publish_role = iam.Role(
            self,
            "s3_publish_role",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
        )

        upload_bucket = s3.Bucket(
            self,
            "UploadedVideos",
            object_ownership=s3.ObjectOwnership.BUCKET_OWNER_ENFORCED,
            enforce_ssl=True,
            server_access_logs_bucket=logging_bucket,
            server_access_logs_prefix="s3-upload-bucket-videos",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        upload_bucket.grant_put(upload_role)

        upload_bucket.grant_read(publish_role)
        upload_bucket.grant_delete(publish_role)

        param_value = {
            "bucket": upload_bucket.bucket_name,
            "upload_path": "uploads/",
            "upload_role": upload_role.role_arn,
        }
        bucket_param = ssm.StringParameter(
            self,
            "VideoStorageUploadBucket",
            parameter_name=getenv("UPLOADPARAMETER"),
            string_value=json.dumps(param_value),
        )
        bucket_param.grant_read(upload_role)

        wp_param = ssm.StringParameter.from_secure_string_parameter_attributes(
            self,
            "VideoPublishWPInfo",
            # null values here should break pipeline
            version=int(getenv("WPPARAMETERVERSION")),  # type: ignore[arg-type]
            parameter_name=getenv("WPPARAMETER"),  # type: ignore[arg-type]
        )
        wp_param.grant_read(publish_role)

        publish_bucket = s3.Bucket(
            self,
            "PublishedVideos",
            object_ownership=s3.ObjectOwnership.BUCKET_OWNER_ENFORCED,
            enforce_ssl=True,
            server_access_logs_bucket=logging_bucket,
            server_access_logs_prefix="s3-publish-bucket-videos",
        )

        publish_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                actions=["s3:GetObject"],
                resources=[publish_bucket.arn_for_objects("*")],
                principals=[iam.StarPrincipal()],
            )
        )
        publish_bucket.grant_put(publish_role)

        self.upload_bucket_arn = CfnOutput(
            self,
            "cfOutputUploadBucketARN",
            value=upload_bucket.bucket_arn,
            description="Upload bucket for the environment",
            export_name="upload_bucket",
        )
        self.publish_bucket_arn = CfnOutput(
            self,
            "cfOutputPublishBucketARN",
            value=publish_bucket.bucket_arn,
            description="Publish bucket for the environment",
            export_name="publish_bucket",
        )


class VideoStorageStage(Stage):
    def __init__(
        self, scope: Construct, construct_id: str, logging_bucket: s3.Bucket, **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        video_storage_stack = VideoStorageStack(
            self, "VideoStorageStack", logging_bucket=logging_bucket
        )

        self.upload_bucket_arn = video_storage_stack.upload_bucket_arn
        self.publish_bucket_arn = video_storage_stack.publish_bucket_arn
