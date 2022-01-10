from aws_cdk import aws_s3 as s3
from aws_cdk import CfnOutput
from aws_cdk import Stack
from aws_cdk import Stage
from constructs import Construct


class BaseInfrastructureStack(Stack):
    """Common Infrastructure Stack.

    Includes items which cannot be deleted - like S3 Logging buckets, DNS zones if
    used...
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        """Instantiates the Infrastructure Stack

        Args:
            scope (Construct): Construct to which this stack belongs. Should be 'app'
                               in 'app.py'
            construct_id (str): Name of the stack
        """
        super().__init__(scope, construct_id, **kwargs)

        logging_bucket = s3.Bucket(
            self,
            "Logging",
            object_ownership=s3.ObjectOwnership.BUCKET_OWNER_PREFERRED,
            enforce_ssl=True,
        )

        self.logging_bucket_arn = CfnOutput(
            self,
            "cfOutputLoggingBucketARN",
            value=logging_bucket.bucket_arn,
            description="Logging bucket for the environment",
            export_name="loggingBucket",
        )


class BaseInfrastructureStage(Stage):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        base_infrastructure_stack = BaseInfrastructureStack(
            self, "BaseInfrastructureStack"
        )

        self.logging_bucket_arn = (
            base_infrastructure_stack.logging_bucket_arn.import_value
        )
