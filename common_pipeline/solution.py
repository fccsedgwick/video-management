from aws_cdk import Stage
from constructs import Construct

from common_pipeline.base_infrastructure import BaseInfrastructureStack
from video_management.video_management_stack import VideoManagementStack


class SolutionEnvironmentStage(Stage):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        base_infrastructure_stack = BaseInfrastructureStack(
            self,
            "BaseInfrastructureStack",
            description="Contains the AWS services which will (or can reaonsably "
            "assumed) to be used across various stacks for the same "
            "customer",
        )

        video_storage_stack = VideoManagementStack(
            self,
            "VideoManagementStack",
            description="Services used for ingesting, processing and posting videos "
            "to a site",
            logging_bucket=base_infrastructure_stack.logging_bucket,
        )
