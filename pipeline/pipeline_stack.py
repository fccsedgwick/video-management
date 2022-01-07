import aws_cdk as cdk
from aws_cdk.pipelines import CodePipeline
from aws_cdk.pipelines import CodePipelineSource
from aws_cdk.pipelines import ShellStep
from constructs import Construct


class PipelineStack(cdk.Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        pipeline = CodePipeline(
            self,
            "Pipeline",
            pipeline_name="MyPipeline",
            synth=ShellStep(
                "Synth",
                input=CodePipelineSource.git_hub(
                    "fccsedgwick/video_management", "main"
                ),
                commands=[
                    "npm install -g aws-cdk",
                    "python -m pip install pipenv",
                    "pipenv install",
                    "pipenv run cdk synth",
                ],
            ),
        )
