[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

# video_management

Repo to manage AWS Pipeline for FCCSedgwick video management

## Purpose

This code is to set up a set of infrastructure used for various functions of
FCCSedgwick

## Initial setup

### Bootstrap AWS Envrionment(s)

Several steps were taken to set up base infrastructure. AWS accounts that are
deployed to must be "bootstrapped". The bootstrapping may be "mostly" completed
by running the [bootstrap_aws_accounts.sh](bootstrap_aws_accounts.sh). When
running the script, you should have environment variables set as shown in
[bootstrap_aws_accounts.sh.env](bootstrap_aws_accounts.sh.env)

Once the pipeline runs initially, you will need the account/role created for
uploading videos. The account will need to have an access key created for it.
You will also need the ARN for the role to be assumed. See AWS IAM
[latest CLI guide](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html)
for complete details. Your aws configs will look something like:

`~/.aws/credentials`
```
[default]
aws_access_key_id=AKIAIOSFODNN7EXAMPLE
aws_secret_access_key=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```
`~/.aws/config`
```
[default]
region=us-west-2
output=json
role_arn=arn:aws:iam::<dev account>:role/VideoStorage-s3uploadrole3778AE89-1ESA90BJN09LM
```

## Deploying stacks

Deploying stacks is completed by cdk synth & cdk deploy. Given that this
repository has multiple CDK stacks, the deploy command will take the stack
as an argument. After the base stack is installed, you will likely only need
to update the VideoManagementStack. Additionally, you will want to provide
the profile for the account to deploy the stack into if you have multiple
AWS accounts. For example, assuming that you have installed cdk as a local
module, running `npx cdk deploy VideoManagementStack --profile fccsedgwickdev`
will deploy the VideoManagementStack to the account where the profile
fccsedgwickdev points to.
