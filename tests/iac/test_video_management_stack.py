"""Most tests will ignore ClamScan resources.

Given that the ClamScan solution is a CDK Solution Construct and is not managed here,
we will test that only AWS services that were used with v2.0.43 of
cdk-serverless-clamscan will be used
"""
from collections import namedtuple

import pytest
from aws_cdk.assertions import Match

from tests.iac import base_infrastructure_stack
from tests.iac import base_infrastructure_template
from tests.iac import module_app
from tests.iac import video_management_stack
from tests.iac import video_management_template


clamscan_known_resource_types = [
    "AWS::CloudFormation::CustomResource",
    "AWS::EC2::FlowLog",
    "AWS::EC2::RouteTable",
    "AWS::EC2::SecurityGroup",
    "AWS::EC2::SecurityGroupEgress",
    "AWS::EC2::SecurityGroupIngress",
    "AWS::EC2::Subnet",
    "AWS::EC2::SubnetRouteTableAssociation",
    "AWS::EC2::VPC",
    "AWS::EC2::VPCEndpoint",
    "AWS::EFS::AccessPoint",
    "AWS::EFS::FileSystem",
    "AWS::EFS::MountTarget",
    "AWS::Events::Rule",
    "AWS::IAM::Policy",
    "AWS::IAM::Role",
    "AWS::Lambda::EventInvokeConfig",
    "AWS::Lambda::Function",
    "AWS::Lambda::Permission",
    "AWS::Logs::LogGroup",
    "AWS::S3::Bucket",
    "AWS::S3::BucketPolicy",
    "Custom::S3AutoDeleteObjects",
]


solution_known_resource_types = [
    "AWS::IAM::User",
    "AWS::IAM::Policy",
    "AWS::IAM::Role",
    "AWS::Lambda::CodeSigningConfig",
    "AWS::Lambda::Function",
    "AWS::Lambda::Permission",
    "AWS::S3::Bucket",
    "AWS::S3::BucketPolicy",
    "AWS::Signer::SigningProfile",
    "AWS::SSM::Parameter",
    "Custom::LogRetention",
    "Custom::S3AutoDeleteObjects",
    "Custom::S3BucketNotifications",
]

ResourceType = namedtuple("ResourceType", ["name", "type"])


@pytest.fixture
def resources_and_types(video_management_template) -> list[ResourceType]:
    template_json = video_management_template.to_json()
    resource_types = [
        ResourceType(name=x, type=template_json["Resources"][x]["Type"])
        for x in template_json["Resources"].keys()
    ]
    return resource_types


@pytest.fixture
def non_clamscan_resources_and_types(resources_and_types) -> list[ResourceType]:
    non_clamscan_resources_and_types = [
        x for x in resources_and_types if not x.name.startswith("ClamScan")
    ]
    return non_clamscan_resources_and_types


@pytest.fixture
def upload_bucket_name(non_clamscan_resources_and_types):
    upload_bucket_names = [
        x.name
        for x in non_clamscan_resources_and_types
        if x.type == "AWS::S3::Bucket" and x.name.startswith("UploadedVideos")
    ]
    assert len(upload_bucket_names) == 1
    return upload_bucket_names[0]


def test_resources_are_known_types(resources_and_types):
    for x in resources_and_types:
        if x.name.startswith("ClamScan"):
            assert x.type in clamscan_known_resource_types
        else:
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
    assert len(solution_roles) == 5
    roles_startwith = [
        "s3uploadrole",
        "s3publishrole",
        "CustomS3AutoDeleteObjectsCustomResourceProviderRole",
        "LogRetention",
        "BucketNotificationsHandler",
    ]
    for x in solution_roles:
        found = False
        matching_role = ""
        for y in roles_startwith:
            matching_role = y
            if x.name.startswith(x):
                found = True
                break
        assert x.name.startswith(x)


def test_upload_bucket_blocks_public_access(
    upload_bucket_name, video_management_template
):
    bucket = video_management_template.to_json()["Resources"][upload_bucket_name]
    assert bucket["Properties"]["PublicAccessBlockConfiguration"] == {
        "BlockPublicAcls": True,
        "BlockPublicPolicy": True,
        "IgnorePublicAcls": True,
        "RestrictPublicBuckets": True,
    }


def test_upload_bucket_notifications_to_clamscan_on_object_upload(
    non_clamscan_resources_and_types,
    resources_and_types,
    video_management_template,
    upload_bucket_name,
):
    # There is a notification
    upload_video_notifications = [
        x.name
        for x in non_clamscan_resources_and_types
        if x.type == "Custom::S3BucketNotifications"
        and x.name.startswith("UploadedVideosNotifications")
    ]
    assert len(upload_video_notifications) == 1

    clamscan_lambdas = [
        x.name
        for x in resources_and_types
        if x.type == "AWS::Lambda::Function"
        and x.name.startswith("ClamScanServerlessClamscan")
    ]
    assert len(clamscan_lambdas) == 1
    clamscan_lambda = clamscan_lambdas[0]

    # The notification is for object uploads and sends to clamscan
    video_management_template.has_resource_properties(
        "Custom::S3BucketNotifications",
        {
            "ServiceToken": {"Fn::GetAtt": [Match.any_value(), "Arn"]},
            "BucketName": {"Ref": upload_bucket_name},
            "NotificationConfiguration": {
                "LambdaFunctionConfigurations": [
                    {
                        "Events": ["s3:ObjectCreated:*"],
                        "LambdaFunctionArn": {"Fn::GetAtt": [clamscan_lambda, "Arn"]},
                    }
                ]
            },
            "Managed": True,
        },
    )


def test_clamscan_notifications_to_publishing_lambda(
    non_clamscan_resources_and_types, video_management_template
):
    publishing_lambdas = [
        x
        for x in non_clamscan_resources_and_types
        if x.type == "AWS::Lambda::Function"
        and x.name.startswith("videoPublishingFunction")
    ]
    assert len(publishing_lambdas) == 1
    publishing_lambda = publishing_lambdas[0].name
    video_management_template.has_resource_properties(
        "AWS::Lambda::EventInvokeConfig",
        {
            "FunctionName": {"Ref": Match.any_value()},
            "Qualifier": "$LATEST",
            "DestinationConfig": {
                "OnFailure": {
                    "Destination": {"Fn::GetAtt": [publishing_lambda, "Arn"]}
                },
                "OnSuccess": {
                    "Destination": {"Fn::GetAtt": [publishing_lambda, "Arn"]}
                },
            },
        },
    )


# def test_published_bucket_notifications_to_posting_lambda(
#     non_clamscan_resources_and_types, video_management_template
# ):
#     # There is a notification
#     published_video_notifications = [
#         x.name
#         for x in non_clamscan_resources_and_types
#         if x.type == "Custom::S3BucketNotifications"
#         and x.name.startswith("PublishedVideosNotifications")
#     ]
#     assert len(published_video_notifications) == 1

#     publish_bucket = [
#         x.name
#         for x in non_clamscan_resources_and_types
#         if x.type == "AWS::S3::Bucket" and x.name.startswith("PublishedVideos")
#     ][0]

#     publish_lambdas = [
#         x.name
#         for x in resources_and_types
#         if x.type == "AWS::Lambda::Function"
#         and x.name.startswith("PostVideos")
#     ]
#     assert len(publish_lambdas) == 1
#     publish_lambda = publish_lambdas[0]

#     # The notification is for object uploads and sends to the posting lambda
#     video_management_template.has_resource_properties(
#         "Custom::S3BucketNotifications",
#         {
#             "ServiceToken": {"Fn::GetAtt": [Match.any_value(), "Arn"]},
#             "BucketName": {"Ref": publish_bucket},
#             "NotificationConfiguration": {
#                 "LambdaFunctionConfigurations": [
#                     {
#                         "Events": ["s3:ObjectCreated:*"],
#                         "LambdaFunctionArn": {"Fn::GetAtt": [publish_lambda, "Arn"]},
#                     }
#                 ]
#             },
#             "Managed": True,
#         },
#     )
