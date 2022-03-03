from os import remove

from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_signer as signer
from aws_cdk.aws_logs import RetentionDays
from constructs import Construct

from github import Github


class PackageLambda:
    """Class to create Lambda function"""

    def __init__(self, construct: Construct) -> None:
        self._construct = construct

    def create_function(
        self,
        git_repo: str,
        lambda_package: str,
        role: iam.Role,
        cdk_name_prefix: str,
        function_description: str,
        handler_prefix: str = None,
    ) -> lambda_.Function:
        """Create CDK function to deploy lambda

        Args:
            git_repo (str): Github repo in "<owner>/<repo>" format where the
                            lambda function package is released
            lambda_package (str): The name of the lambda package. Should be a
                                  zip file.
            role (iam.Role): The IAM role that the lambda function should
                             assume when running
            cdk_name_prefix (str): naming prefix for the CDK artifact which
                                   defines the lambda function
            function_description (str): description of the lambda function.
                                        Will be visible in the AWS console

        Returns:
            lambda_.Function: The CDK lambda function which is created
        """

        gh = Github()
        gh.repo = git_repo
        package = gh.get_latest_signed_assets([lambda_package])[0]

        signing_profile = signer.SigningProfile(
            self._construct,
            f"{cdk_name_prefix}SigningProfile",
            platform=signer.Platform.AWS_LAMBDA_SHA384_ECDSA,
        )

        code_signing_config = lambda_.CodeSigningConfig(
            self._construct,
            f"{cdk_name_prefix}CodeSigningConfig",
            signing_profiles=[signing_profile],
        )

        role.add_managed_policy(
            iam.ManagedPolicy.from_managed_policy_arn(
                self._construct,
                f"{cdk_name_prefix}AWSLambdaBasicExecutionRole",
                managed_policy_arn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
            )
        )

        handler = "lambda_function.lambda_handler"
        if handler_prefix is not None:
            handler = f"{handler_prefix}.{handler}"

        new_lambda = lambda_.Function(
            self._construct,
            cdk_name_prefix,
            code_signing_config=code_signing_config,
            log_retention=RetentionDays.ONE_WEEK,
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler=handler,
            code=lambda_.Code.from_asset(package),
            role=role,
            description=function_description,
        )

        remove(package)

        return new_lambda
