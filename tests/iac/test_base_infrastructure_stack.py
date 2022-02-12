# pylint: disable="redefined-outer-name,missing-function-docstring,unused-import"
from tests.iac import base_infrastructure_stack
from tests.iac import base_infrastructure_template
from tests.iac import module_app


def test_only_one_resource(base_infrastructure_template):
    assert len(base_infrastructure_template.to_json()["Resources"]) == 2


def test_one_s3_bucket_created(base_infrastructure_template):
    base_infrastructure_template.resource_count_is("AWS::S3::Bucket", 1)


def test_one_s3_bucket_policy_created(base_infrastructure_template):
    base_infrastructure_template.resource_count_is("AWS::S3::BucketPolicy", 1)


def test_s3_bucket_has_update_replace_policy(base_infrastructure_template):
    base_infrastructure_template.has_resource(
        "AWS::S3::Bucket", {"UpdateReplacePolicy": "Retain"}
    )


def test_s3_bucket_has_deletion_protection_policy(base_infrastructure_template):
    base_infrastructure_template.has_resource(
        "AWS::S3::Bucket", {"DeletionPolicy": "Retain"}
    )


def test_s3_bucket_has_ownership_set_to_bucket_owner_preferred(
    base_infrastructure_template,
):
    base_infrastructure_template.has_resource_properties(
        "AWS::S3::Bucket",
        {"OwnershipControls": {"Rules": [{"ObjectOwnership": "BucketOwnerPreferred"}]}},
    )
