import configparser
import json
import subprocess
from os import listdir
from os import mkdir
from os import path
from shutil import move
from shutil import rmtree
from tempfile import mkdtemp
from zipfile import PyZipFile

from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_signer as signer
from aws_cdk.aws_logs import RetentionDays
from constructs import Construct


class PackageLambda:
    def __init__(self, construct: Construct) -> None:
        self._construct = construct

    def _package_lambda(self, lambda_location: str):
        temp_dir = mkdtemp()
        zip_temp_dir = path.join(temp_dir, "zip")
        package_dir = path.join(temp_dir, "packages")
        mkdir(package_dir)
        mkdir(zip_temp_dir)
        zip_file = path.join(zip_temp_dir, "lambda_package.zip")
        target_zip_file = path.join("./", "lambda_package.zip")

        for requirement in self._get_requirements_from_Pipfile(lambda_location):
            subprocess.run(
                ["bash", "-c", f"pip install -t '{package_dir}' '{requirement}'"],
                shell=True,
            )  # nosec
        with PyZipFile(zip_file, "x", optimize=2) as lambda_zip:
            for x in listdir(package_dir):
                lambda_zip.write(path.join(package_dir, x))
            lambda_zip.write(
                path.join(lambda_location, "lambda_function.py"),
                arcname="lambda_function.py",
            )
        move(zip_file, target_zip_file)
        rmtree(temp_dir)
        return target_zip_file

    def _get_requirements_from_Pipfile(self, location: str) -> list:
        pipfile = configparser.ConfigParser()
        pipfile.read(path.join(location, "Pipfile"))
        requirements = [x for x in pipfile["packages"]]
        requirement_versions = []
        if path.isfile(path.join(location, "Pipfile.lock")):
            with open(path.join(location, "Pipfile.lock"), "r") as fn:
                pipfile_lock = json.load(fn)
            requirement_versions = [
                f"{key}{pipfile_lock['default'][key]['version']}"
                for key in requirements
            ]
        else:
            requirement_versions = requirements
        return requirement_versions

    def create_function(self, lambda_location: str, role: iam.Role) -> lambda_.Function:
        temp_file = self._package_lambda(lambda_location)
        signing_profile = signer.SigningProfile(
            self._construct,
            "SigningProfile",
            platform=signer.Platform.AWS_LAMBDA_SHA384_ECDSA,
        )

        code_signing_config = lambda_.CodeSigningConfig(
            self._construct, "CodeSigningConfig", signing_profiles=[signing_profile]
        )

        return lambda_.Function(
            self._construct,
            "videoPublishingFunction",
            code_signing_config=code_signing_config,
            log_retention=RetentionDays.ONE_WEEK,
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset(temp_file),
            role=role,
        )
