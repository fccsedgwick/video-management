import aws_cdk.assertions as assertions
import pytest
from aws_cdk import App
from dotenv import load_dotenv

from base_infrastructure import BaseInfrastructureStack
from video_management.video_management_stack import VideoManagementStack


@pytest.fixture(scope="module")
def module_app():
    module_app = App()
    return module_app


@pytest.fixture(scope="module")
def base_infrastructure_stack(module_app):
    stack = BaseInfrastructureStack(module_app, "base-infrastructure")
    return stack


@pytest.fixture(scope="module")
def base_infrastructure_template(base_infrastructure_stack):
    template = assertions.Template.from_stack(base_infrastructure_stack)
    return template


@pytest.fixture(scope="module")
def video_management_stack(module_app, base_infrastructure_stack):
    load_dotenv("app.env")
    stack = VideoManagementStack(
        module_app,
        "video-management",
        logging_bucket=base_infrastructure_stack.logging_bucket,
    )
    return stack


@pytest.fixture(scope="module")
def video_management_template(video_management_stack):
    template = assertions.Template.from_stack(video_management_stack)
    return template
