from os import environ
from os import path
from re import match

import boto3
import pytest
import requests
from lambda_function import ClamScanPayload
from lambda_function import ClamScanSource
from lambda_function import ClamScanStatus
from lambda_function import PublishLambda
from pytest_docker import docker_services
from requests.exceptions import ConnectionError
from urllib3.exceptions import ProtocolError


def is_responsive(url: str) -> bool:
    try:
        response = requests.get(url)
        if response.status_code == 404 and response.json() == {"status": "running"}:
            return True
        return False
    except (ConnectionError, ProtocolError):
        return False


@pytest.fixture(scope="session")
def docker_compose_file():
    dir = path.dirname(__file__)
    return path.join(dir, "docker-compose.yml")


@pytest.fixture(scope="session")
def localstack_with_buckets(docker_services):
    environ["SERVICES"] = "s3"
    port = docker_services.port_for("localstack", 4566)
    environ["AWS_ACCESS_KEY_ID"] = "test"
    environ["AWS_SECRET_ACCESS_KEY"] = "test"  # pragma: allowlist secret
    environ["AWS_DEFAULT_REGION"] = "us-east-2"
    environ["AWS_ENDPOINT"] = f"http://localhost:{port}"
    docker_services.wait_until_responsive(
        timeout=30.0, pause=0.1, check=lambda: is_responsive(environ["AWS_ENDPOINT"])
    )
    s3 = boto3.resource("s3", endpoint_url=environ["AWS_ENDPOINT"])
    s3.Bucket("source").create()
    s3.Bucket("destination").create()
    environ["SOURCE_BUCKET"] = "source"
    environ["DEST_BUCKET"] = "destination"


def get_clamscan_event(s3_key: str, status: ClamScanStatus) -> dict:
    return ClamScanPayload(
        source=ClamScanSource.SERVERLESS_CLAMSCAN,
        input_bucket=environ["SOURCE_BUCKET"],
        input_key=s3_key,
        status=status,
        message="testfilescanned",
    )


def put_test_file(s3_filename: str, clamscan_status: ClamScanStatus) -> str:
    s3 = boto3.resource("s3", endpoint_url=environ["AWS_ENDPOINT"])
    s3.meta.client.put_object(
        ACL="private",
        Body=b"testfile",
        Bucket=environ["SOURCE_BUCKET"],
        Key=s3_filename,
    )
    return s3_filename


def test_delete_file(localstack_with_buckets):
    # Arrange
    s3 = boto3.resource("s3", endpoint_url=environ["AWS_ENDPOINT"])
    test_file = "test_delete.txt"
    put_test_file(test_file, ClamScanStatus.CLEAN)
    # Act
    PublishLambda().delete_file(get_clamscan_event(test_file, ClamScanStatus.CLEAN))
    # Assert
    source_bucket_keys = s3.meta.client.list_objects_v2(
        Bucket=environ["SOURCE_BUCKET"], Prefix=test_file
    )
    assert source_bucket_keys["KeyCount"] == 0
    dest_bucket_keys = s3.meta.client.list_objects_v2(
        Bucket=environ["DEST_BUCKET"], Prefix=test_file
    )
    assert dest_bucket_keys["KeyCount"] == 0


def test_copy_file(localstack_with_buckets):
    # Arrange
    s3 = boto3.resource("s3", endpoint_url=environ["AWS_ENDPOINT"])
    test_file = "test_copy.txt"
    put_test_file(test_file, ClamScanStatus.CLEAN)
    # Act
    PublishLambda().copy_file(
        get_clamscan_event(test_file, ClamScanStatus.CLEAN), f"dst_{test_file}"
    )
    # Assert
    source_bucket_keys = s3.meta.client.list_objects_v2(
        Bucket=environ["SOURCE_BUCKET"], Prefix=test_file
    )
    assert source_bucket_keys["KeyCount"] == 1
    dest_bucket_keys = s3.meta.client.list_objects_v2(
        Bucket=environ["DEST_BUCKET"], Prefix=f"dst_{test_file}"
    )
    assert dest_bucket_keys["KeyCount"] == 1


def test_copy_tags(localstack_with_buckets):
    # Arrange
    s3 = boto3.resource("s3", endpoint_url=environ["AWS_ENDPOINT"])
    source_test_file = "src_test_copy_tags.txt"
    dest_test_file = "dst_test_copy_tags.txt"
    put_test_file(source_test_file, ClamScanStatus.CLEAN)
    tagset = [{"Key": "tagone", "Value": "val1"}, {"Key": "tagtwo", "Value": "val2"}]
    s3.meta.client.put_object_tagging(
        Bucket=environ["SOURCE_BUCKET"],
        Key=source_test_file,
        Tagging={"TagSet": tagset},
    )
    s3.meta.client.put_object(
        ACL="private",
        Body=b"testfile",
        Bucket=environ["DEST_BUCKET"],
        Key=dest_test_file,
    )
    # Act
    PublishLambda().copy_tags(
        get_clamscan_event(source_test_file, ClamScanStatus.CLEAN), dest_test_file
    )
    # Assert
    source_bucket_keys = s3.meta.client.list_objects_v2(
        Bucket=environ["SOURCE_BUCKET"], Prefix=source_test_file
    )
    assert source_bucket_keys["KeyCount"] == 1
    response = s3.meta.client.get_object_tagging(
        Bucket=environ["DEST_BUCKET"], Key=dest_test_file
    )
    assert response["TagSet"] == tagset


def test_move_file(localstack_with_buckets):
    # Arrange
    s3 = boto3.resource("s3", endpoint_url=environ["AWS_ENDPOINT"])
    test_file = "test_move.txt"
    put_test_file(test_file, ClamScanStatus.CLEAN)
    tagset = [{"Key": "onetag", "Value": "1val"}, {"Key": "twotag", "Value": "2val"}]
    s3.meta.client.put_object_tagging(
        Bucket=environ["SOURCE_BUCKET"], Key=test_file, Tagging={"TagSet": tagset}
    )
    # Act
    PublishLambda().move_video_to_published(
        get_clamscan_event(test_file, ClamScanStatus.CLEAN)
    )
    # Assert
    source_bucket_keys = s3.meta.client.list_objects_v2(
        Bucket=environ["SOURCE_BUCKET"], Prefix=test_file
    )
    assert source_bucket_keys["KeyCount"] == 0
    dest_bucket_keys = s3.meta.client.list_objects_v2(
        Bucket=environ["DEST_BUCKET"], Prefix=test_file
    )
    assert dest_bucket_keys["KeyCount"] == 0
    dest_bucket_keys = s3.meta.client.list_objects_v2(Bucket=environ["DEST_BUCKET"])
    copied_objects = [
        x["Key"] for x in dest_bucket_keys["Contents"] if x["Key"].endswith(test_file)
    ]
    assert len(copied_objects) == 1
    match_pattern = "^[0-9a-f]{32}_" + test_file
    assert match(match_pattern, copied_objects[0])
    response = s3.meta.client.get_object_tagging(
        Bucket=environ["DEST_BUCKET"], Key=copied_objects[0]
    )
    assert response["TagSet"] == tagset
