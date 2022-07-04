"""Most tests will ignore ClamScan resources.

Given that the ClamScan solution is a CDK Solution Construct and is not managed here,
we will test that only AWS services that were used with v2.0.43 of
cdk-serverless-clamscan will be used
"""
# pylint: disable="redefined-outer-name,missing-function-docstring,unused-import"
from collections import namedtuple
from typing import List

import pytest
from aws_cdk.assertions import Match

from tests.iac import base_infrastructure_stack
from tests.iac import base_infrastructure_template
from tests.iac import module_app
from tests.iac import video_management_stack
from tests.iac import video_management_template


solution_known_resource_types = [
    "AWS::CloudFront::CloudFrontOriginAccessIdentity",
    "AWS::CloudFront::Distribution",
    "AWS::IAM::User",
    "AWS::IAM::Policy",
    "AWS::IAM::Role",
    "AWS::Lambda::CodeSigningConfig",
    "AWS::Lambda::Function",
    "AWS::Lambda::Permission",
    "AWS::S3::Bucket",
    "AWS::S3::BucketPolicy",
    "AWS::Signer::SigningProfile",
    "Custom::LogRetention",
]


ResourceType = namedtuple("ResourceType", ["name", "type"])


@pytest.fixture
def resources_and_types(video_management_template) -> List[ResourceType]:
    template_json = video_management_template.to_json()
    resource_types = [
        ResourceType(name=x, type=template_json["Resources"][x]["Type"])
        for x in template_json["Resources"].keys()
    ]
    return resource_types


@pytest.fixture
def non_clamscan_resources_and_types(resources_and_types) -> List[ResourceType]:
    non_clamscan_resources_and_types = [
        x for x in resources_and_types if not x.name.startswith("ClamScan")
    ]
    return non_clamscan_resources_and_types


def test_resources_are_known_types(resources_and_types):
    for x in resources_and_types:
        assert x.type in solution_known_resource_types


def test_only_one_iam_user_created(video_management_template):
    video_management_template.resource_count_is("AWS::IAM::User", 1)


def test_user_can_assume_iam_role(
    non_clamscan_resources_and_types, video_management_template
):
    role_type = [
        x for x in non_clamscan_resources_and_types if x.type == "AWS::IAM::User"
    ][0]
    video_management_template.has_resource_properties(
        "AWS::IAM::Role",
        Match.object_equals(
            {
                "AssumeRolePolicyDocument": {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Action": "sts:AssumeRole",
                            "Effect": "Allow",
                            "Principal": {
                                "AWS": {"Fn::GetAtt": [role_type.name, "Arn"]}
                            },
                        }
                    ],
                }
            }
        ),
    )


def test_roles_created(non_clamscan_resources_and_types):
    solution_roles = [
        x for x in non_clamscan_resources_and_types if x.type == "AWS::IAM::Role"
    ]
    assert len(solution_roles) == 1
    roles_startwith = [
        "s3uploadrole",
        # "s3publishrole",
        # "CustomS3AutoDeleteObjectsCustomResourceProviderRole",
        # "LogRetention",
        # "BucketNotificationsHandler",
        # "wppostingrole",
    ]
    for x in solution_roles:
        found = False
        for y in roles_startwith:
            matching_role = y
            if x.name.startswith(y):
                found = True
                break
        assert found
