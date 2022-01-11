from aws_cdk import aws_s3 as s3
from aws_cdk import Stack
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

        self.logging_bucket = s3.Bucket(
            self,
            "Logging",
            object_ownership=s3.ObjectOwnership.BUCKET_OWNER_PREFERRED,
            enforce_ssl=True,
        )
