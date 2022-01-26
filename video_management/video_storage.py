import json
from os import getenv

from aws_cdk import aws_iam as iam
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_ssm as ssm
from aws_cdk import RemovalPolicy
from constructs import Construct


class VideoStorage:
    def __init__(self, construct: Construct, logging_bucket: s3.Bucket):
        self._construct = construct

        self._create_iam()
        self._create_upload_bucket(logging_bucket)
        self._create_publish_bucket(logging_bucket)
        self._create_ssm_parameters()

    def _create_iam(self):
        user = iam.User(self._construct, "s3_upload_user")
        self.upload_role = iam.Role(self._construct, "s3_upload_role", assumed_by=user)

        self.publish_role = iam.Role(
            self._construct,
            "s3_publish_role",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
        )

    def _create_upload_bucket(self, logging_bucket: s3.Bucket):
        self.upload_bucket = s3.Bucket(
            self._construct,
            "UploadedVideos",
            object_ownership=s3.ObjectOwnership.BUCKET_OWNER_ENFORCED,
            enforce_ssl=True,
            server_access_logs_bucket=logging_bucket,
            server_access_logs_prefix="s3-upload-bucket-videos",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
        )

        self.upload_bucket.grant_put(self.upload_role)

        self.upload_bucket.grant_read(self.publish_role)
        self.upload_bucket.grant_delete(self.publish_role)

    def _create_ssm_parameters(self):
        param_value = {
            "bucket": self.upload_bucket.bucket_name,
            "upload_path": "uploads/",
            "upload_role": self.upload_role.role_arn,
        }
        bucket_param = ssm.StringParameter(
            self._construct,
            "VideoStorageUploadBucket",
            parameter_name=getenv("UPLOADPARAMETER"),
            string_value=json.dumps(param_value),
        )
        bucket_param.grant_read(self.upload_role)

    def _create_publish_bucket(self, logging_bucket: s3.Bucket):
        self.publish_bucket = s3.Bucket(
            self._construct,
            "PublishedVideos",
            object_ownership=s3.ObjectOwnership.BUCKET_OWNER_ENFORCED,
            enforce_ssl=True,
            server_access_logs_bucket=logging_bucket,
            server_access_logs_prefix="s3-publish-bucket-videos",
        )

        self.publish_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                actions=["s3:GetObject"],
                resources=[self.publish_bucket.arn_for_objects("*")],
                principals=[iam.StarPrincipal()],
            )
        )
        self.publish_bucket.grant_put(self.publish_role)
        self.publish_bucket.grant_read(self.publish_role)
