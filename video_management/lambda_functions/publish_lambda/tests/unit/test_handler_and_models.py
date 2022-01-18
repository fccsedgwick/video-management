from copy import deepcopy

import pytest
from lambda_function import ClamScanPayload
from lambda_function import ClamScanSource
from lambda_function import ClamScanStatus
from lambda_function import lambda_handler
from lambda_function import load_event


@pytest.fixture(scope="module")
def clamscan_event():
    return {
        "version": "1.0",
        "timestamp": "2022-01-14T11: 28: 37.254Z",
        "requestContext": {
            "requestId": "d6950426-64df-4690-9647-f8edc8870b49",
            "functionArn": "arn:aws:lambda:us-east-2: 747096213102:function:dev-us-east-2-SolutionEnv-ClamScanServerlessClamsc-rwh0tqCYx9kZ:$LATEST",
            "condition": "Success",
            "approximateInvokeCount": 1,
        },
        "requestPayload": {
            "Records": [
                {
                    "eventVersion": "2.1",
                    "eventSource": "aws:s3",
                    "awsRegion": "us-east-2",
                    "eventTime": "2022-01-14T11: 28: 09.374Z",
                    "eventName": "ObjectCreated:Put",
                    "userIdentity": {
                        "principalId": "AWS:AROA234THQZXDVNZF2U43:sugar.suntan.unused"
                    },
                    "requestParameters": {"sourceIPAddress": "68.102.31.220"},
                    "responseElements": {
                        "x-amz-request-id": "YJDVRRYTSGAZZ79M",
                        "x-amz-id-2": "W/vCysPvrnO7Q+0t8UOgqpq9Gqde4fgCX8Mo8c4nV5LG6q+nAJiMmghbSkqQjxYIPr1O5YmqxLVXyVz9bcrs4xe+o11p+s2F",
                    },
                    "s3": {
                        "s3SchemaVersion": "1.0",
                        "configurationId": "YjU0ZGY5YjktNTIwOS00M2I4LThkM2EtNDljM2E2YTg5ZDg4",
                        "bucket": {
                            "name": "dev-us-east-2-solutionenvi-uploadedvideos8e2112d9-6dgcj4udmwy",
                            "ownerIdentity": {"principalId": "A1PK9S96T3XHRJ"},
                            "arn": "arn:aws:s3: : :dev-us-east-2-solutionenvi-uploadedvideos8e2112d9-6dgcj4udmwy",
                        },
                        "object": {
                            "key": "OWASP_ASVS_4_0_3.csv",
                            "size": 70544,
                            "eTag": "48c6dfc7ad34c6c3d4db4ee0c2c4c7e7",  # pragma: allowlist secret
                            "sequencer": "0061E15E4954C16CEF",  # pragma: allowlist secret
                        },
                    },
                }
            ]
        },
        "responseContext": {"statusCode": 200, "executedVersion": "$LATEST"},
        "responsePayload": {
            "source": "serverless-clamscan",
            "input_bucket": "dev-us-east-2-solutionenvi-uploadedvideos8e2112d9-6dgcj4udmwy",
            "input_key": "OWASP_ASVS_4_0_3.csv",
            "status": "CLEAN",
            "message": "Scanning /mnt/lambda/d6950426-64df-4690-9647-f8edc8870b49/OWASP_ASVS_4_0_3.csv\n/mnt/lambda/d6950426-64df-4690-9647-f8edc8870b49/OWASP_ASVS_4_0_3.csv: OK\n\n----------- SCAN SUMMARY -----------\nKnown viruses: 8603193\nEngine version: 0.103.4\nScanned directories: 1\nScanned files: 1\nInfected files: 0\nData scanned: 0.13 MB\nData read: 0.07 MB (ratio 1.94: 1)\nTime: 23.934 sec (0 m 23 s)\nStart Date: 2022: 01: 14 11: 28: 13\nEnd Date: 2022: 01: 14 11: 28: 37\n",
        },
    }


def test_load_event(monkeypatch, clamscan_event):
    monkeypatch.setenv(
        "SOURCE_BUCKET", "dev-us-east-2-solutionenvi-uploadedvideos8e2112d9-6dgcj4udmwy"
    )
    event = load_event(clamscan_event)
    assert isinstance(event, ClamScanPayload)
    assert isinstance(event.status, ClamScanStatus)
    assert isinstance(event.source, ClamScanSource)


def test_region_validation(monkeypatch, clamscan_event):
    monkeypatch.setenv("SOURCE_BUCKET", "foo")
    with pytest.raises(ValueError):
        load_event(clamscan_event)


def test_handler_status_na(monkeypatch, clamscan_event):
    monkeypatch.setenv(
        "SOURCE_BUCKET", "dev-us-east-2-solutionenvi-uploadedvideos8e2112d9-6dgcj4udmwy"
    )
    event = deepcopy(clamscan_event)
    event["responsePayload"]["status"] = "N/A"
    with pytest.raises(ValueError):
        lambda_handler(event, "")


def test_handler_status_infected(monkeypatch, clamscan_event):
    delete_called = False
    monkeypatch.setenv(
        "SOURCE_BUCKET", "dev-us-east-2-solutionenvi-uploadedvideos8e2112d9-6dgcj4udmwy"
    )
    event = deepcopy(clamscan_event)
    event["responsePayload"]["status"] = "INFECTED"

    def _mock_delete(cls, scan_event):
        nonlocal delete_called
        delete_called = True
        assert isinstance(scan_event, ClamScanPayload)
        assert scan_event.status == ClamScanStatus.INFECTED

    monkeypatch.setattr("lambda_function.PublishLambda.delete_file", _mock_delete)
    lambda_handler(event, "")
    assert delete_called


def test_handler_status_clean(monkeypatch, clamscan_event):
    move_called = False
    monkeypatch.setenv(
        "SOURCE_BUCKET", "dev-us-east-2-solutionenvi-uploadedvideos8e2112d9-6dgcj4udmwy"
    )

    def _mock_move(cls, scan_event):
        nonlocal move_called
        move_called = True
        assert isinstance(scan_event, ClamScanPayload)
        assert scan_event.status == ClamScanStatus.CLEAN

    monkeypatch.setattr(
        "lambda_function.PublishLambda.move_video_to_published", _mock_move
    )
    lambda_handler(clamscan_event, "")
    assert move_called
