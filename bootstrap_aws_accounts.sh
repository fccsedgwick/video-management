#!/bin/bash

CDK_NEW_BOOTSTRAP=1

export AWS_ACCESS_KEY_ID=$AWS_PIPELINE_ACCESS_KEY
export AWS_SECRET_ACCESS_KEY=$AWS_PIPELINE_ACCESS_SECRET
export AWS_DEFAULT_REGION=$AWS_PIPELINE_REGION

npx cdk bootstrap aws://$AWS_PIPELINE_ACCOUNT/$AWS_DEFAULT_REGION \
    --cloudformation-execution-policies arn:aws:iam::aws:policy/AdministratorAccess

export AWS_ACCESS_KEY_ID=$AWS_DEV_ACCESS_KEY
export AWS_SECRET_ACCESS_KEY=$AWS_DEV_ACCESS_SECRET
export AWS_DEFAULT_REGION=$AWS_DEV_REGION

npx cdk bootstrap aws://$AWS_DEV_ACCOUNT/$AWS_DEFAULT_REGION \
    --cloudformation-execution-policies arn:aws:iam::aws:policy/AdministratorAccess \
    --trust $AWS_PIPELINE_ACCOUNT

export AWS_ACCESS_KEY_ID=$AWS_PROD_ACCESS_KEY
export AWS_SECRET_ACCESS_KEY=$AWS_PROD_ACCESS_SECRET
export AWS_DEFAULT_REGION=$AWS_PROD_REGION

npx cdk bootstrap aws://$AWS_PROD_ACCOUNT/$AWS_DEFAULT_REGION \
    --cloudformation-execution-policies arn:aws:iam::aws:policy/AdministratorAccess \
    --trust $AWS_PIPELINE_ACCOUNT

export AWS_ACCESS_KEY_ID=
export AWS_SECRET_ACCESS_KEY=
