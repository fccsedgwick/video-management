from dataclasses import dataclass

# from aws_cdk import aws_iam
# from aws_cdk import aws_s3


# @dataclass
# class AccountBuckets:
#     # will be ok if pipeline blows up due to NoneTypes making it that far...
#     # don't let it happen
#     logging: aws_s3.Bucket = None  # type: ignore[assignment]
#     upload: aws_s3.Bucket = None  # type: ignore[assignment]
#     publish: aws_s3.Bucket = None  # type: ignore[assignment]


@dataclass
class Account:
    name: str
    id: str
    region: str
    # buckets: AccountBuckets = AccountBuckets()
    # publish_role: aws_iam.Role = None  # type: ignore[assignment]
    manually_approve_change: bool = False
