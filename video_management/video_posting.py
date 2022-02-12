from os import getenv

from aws_cdk import aws_iam
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_s3_notifications
from aws_cdk import aws_ssm as ssm
from constructs import Construct

from video_management.create_lambda import PackageLambda


class VideoPosting:
    """IAC to deploy lambda and supporting infrastructure"""

    def __init__(
        self,
        construct: Construct,
        publish_bucket: s3.Bucket,
    ):

        self._construct = construct

        self._create_iam(publish_bucket)
        self._set_permissions_wp_info_parameter()
        self._create_posting_video_lambda(
            publish_bucket=publish_bucket,
        )

    def _create_iam(self, publish_bucket):
        self.posting_role = aws_iam.Role(
            self._construct,
            "wp_posting_role",
            assumed_by=aws_iam.ServicePrincipal("lambda.amazonaws.com"),
        )
        # publish_bucket.grant_read(self.posting_role)
        self.posting_role.attach_inline_policy(
            aws_iam.Policy(
                self._construct,
                "AllowPostingS3Functions",
                statements=[
                    aws_iam.PolicyStatement(
                        actions=[
                            "s3:PutObjectTagging",
                            "s3:GetObjectTagging",
                            "s3:GetBucketLocation",
                        ],
                        effect=aws_iam.Effect.ALLOW,
                        resources=[f"{publish_bucket.bucket_arn}/*"],
                    )
                ],
            )
        )

    def _set_permissions_wp_info_parameter(self):
        wp_param = ssm.StringParameter.from_secure_string_parameter_attributes(
            self._construct,
            "VideoPublishWPInfo",
            # null values here should break pipeline
            version=int(getenv("WPPARAMETERVERSION")),  # type: ignore[arg-type]
            parameter_name=getenv("WPPARAMETER"),  # type: ignore[arg-type]
        )
        wp_param.grant_read(self.posting_role)

    def _create_posting_video_lambda(
        self,
        publish_bucket: s3.Bucket,
    ):
        self.posting_lambda = PackageLambda(self._construct).create_function(
            git_repo="fccsedgwick/post-video-lambda",
            lambda_package="post_video_lambda.zip",
            role=self.posting_role,
            cdk_name_prefix="VideoPostingFunction",
            function_description="Function to post video to WordPress.",
        )
        self.posting_lambda.add_environment("DEST_BUCKET", publish_bucket.bucket_name)
        # null values here should break pipeline
        self.posting_lambda.add_environment("WPPOSTPARAM", getenv("WPPARAMETER"))  # type: ignore[arg-type]
        self.posting_lambda.add_environment("WPPOSTPARAM_VERSION", getenv("WPPARAMETERVERSION"))  # type: ignore[arg-type]

        publish_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            aws_s3_notifications.LambdaDestination(self.posting_lambda),
        )
