#!/usr/bin/env bash
#
# 02_iam.sh — IAM: create the execution role the Lambda function runs as.
#
# A Lambda function needs a role to be allowed to run and to write its logs to CloudWatch.

source "$(dirname "${BASH_SOURCE[0]}")/config.sh"

echo "==> [IAM] Ensuring role exists: ${ROLE_NAME}"

# `get-role` fails when the role doesn't exist, so this block only runs on the first deploy.
if ! aws iam get-role --role-name "$ROLE_NAME" >/dev/null 2>&1; then

  # create-role: creates the role together with its TRUST POLICY, which says WHO may use it.
  # Here only the Lambda service (lambda.amazonaws.com) is allowed to assume this role.
  aws iam create-role \
    --role-name "$ROLE_NAME" \
    --assume-role-policy-document '{
      "Version": "2012-10-17",
      "Statement": [{
        "Effect": "Allow",
        "Principal": {"Service": "lambda.amazonaws.com"},
        "Action": "sts:AssumeRole"
      }]
    }' >/dev/null

  # attach-role-policy: grants the role its PERMISSIONS.
  # AWSLambdaBasicExecutionRole is an AWS-managed policy that only allows writing logs
  # to CloudWatch Logs. Add more policies here if the function later needs S3, etc.
  aws iam attach-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

  # A new role can take a few seconds to become usable by other services.
  # Without this pause, create-function may fail with "role cannot be assumed".
  echo "    Waiting for IAM propagation..."
  sleep 10
else
  echo "    Role already exists, skipping."
fi

echo "==> [IAM] Done: ${ROLE_ARN}"
