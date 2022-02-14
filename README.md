[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/fccsedgwick/video-management/main.svg)](https://results.pre-commit.ci/latest/github/__user__/__project__/__branch__)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

# video_management

Repo to manage AWS Pipeline for FCCSedgwick video management

## Purpose

This code is to set up a deployment pipeline and set of infrastructure for
publishing videos. The videos published will be sent to an S3 bucket, where
they will be publicly available. In the general case, they will be served up in
an website (WordPress site).

In this solution, there is no optimization of the videos for general on-demand
viewing in multiple form-factors. The original uploaded resolution is retained.

## Upload Process

```mermaid.css
sequenceDiagram
    User->>UploadBucket: Upload video
    UploadBucket->>ClamShell: S3 Trigger on upload
    ClamShell->>PublishLambda: Output Event
    alt scan is clean
        PublishLambda->>PublishBucket: Copy clean video file
        PublishLambda->>UploadBucket: Delete video after copying to PublishBucket
        PublishBucket->>WordPressLambda: S3 Trigger on upload
        WordPressLambda->>WordPressSite: Post video
        WordPressLambda->>PublishBucket: Add WordPress Site post info as metadata on video
    else scan not clean
        PublishLambda->>UploadBucket: Delete non-clean video file
    end
```

## Weekly Process
```mermaid.css
sequenceDiagram
    CloudWatchEvent->>BucketLambda: Event triggers weekly
    BucketLambda->>PublishBucket: Get videos older than 60 days and their WordPress Site post metadata
    BucketLambda->>WordpressSite: Delete posts for videos > 60 days old
    BucketLambda->>PublishBucket: Delete videos > 60 days old
```

## Initial setup

### Bootstrap AWS Envrionment(s)

Several steps were taken to set up base infrastructure. See:
[AWC CDK Pipeline page](https://docs.aws.amazon.com/cdk/v2/guide/cdk_pipeline.html).
Three AWS accounts in an organization used. (pipeline, development,
production). For the GitHub API token, the scope granted was public_repo.

The bootstrapping may be "mostly" completed by running the
[bootstrap_aws_accounts.sh](bootstrap_aws_accounts.sh). When running the
script, you should have environment variables set as shown in
[bootstrap_aws_accounts.sh.env](bootstrap_aws_accounts.sh.env)

Once the bootstrap is complete, attempt to deploy the solution `cdk deploy`.
If you have errors about inability for CodeBuild to assume roles, manually give
the account the necessary permissions. For me that was adding a policy like the
following to the appropriate account. You can find the exact details in the
logs of the step that failed
```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "CodeBuildAssumeCrossAccountLookupRoles",
            "Effect": "Allow",
            "Action": "sts:AssumeRole",
            "Resource": [
                "arn:aws:iam::308828263283:role/cdk-hnb659fds-lookup-role-308828263283-us-east-2",
                "arn:aws:iam::747096213102:role/cdk-hnb659fds-lookup-role-747096213102-us-east-2"
            ]
        }
    ]
}
```

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

### Setup WordPress Account

It is assumed that you already have a WordPress site you will be posting to, if
not create that.

1. Create a [developer account](https://developer.wordpress.com/apps) and an
   application.
2. Become an author on the site you will be publishing to
3. Find the Site_id - Retrieve an access token and then get site info by domain
   name. The [Postman collection](chores_and_setup/WordPress.postman_collection.json)
   has the calls needed. The site_id you will need is the `ID` value in the
   response for the WP Site Info by domain name call. It is beyond the scope of
   this readme, but you will need to set the following environment variables in
   Postman for the calls to work:
   * `client_id` - from step 1 of create an application
   * `client_secret` - from step 1 of create an application
   * `username` - from step 1 of create a developer account
   * `password` - from step 1 of create a developer account
   * `wordpress_site_domain` - The domain name of the WordPress site

### Add parameter to the AWS account

In Systems Manager -> Parameter Store, create a new parameter. This parameter
name will be added to the app.env file as the 'WPPARAMETER' Use Secret
String and use the following format:
```
{
    "client_id": <client_id>,
    "client_secret": "<client_secret>",
    "username": "<username>",
    "password": "<password>",
    "wp_site_id": <site_id>,
    "post_category": "<tag to add to the post>"
}
```
