#!/usr/bin/env bash
#
# destroy.sh — deletes everything created by deploy.sh, to avoid leftover costs.
#
# Usage:
#   ./scripts/destroy.sh            # asks for confirmation first
#   YES=1 ./scripts/destroy.sh      # skips the confirmation (e.g. in automation)
#
# Every step checks that the resource exists first, so it is safe to run more than once.

source "$(dirname "${BASH_SOURCE[0]}")/config.sh"

# ---- Confirmation -----------------------------------------------------------
# Deleting is irreversible, so require typing the function name unless YES=1 is set.
if [ "${YES:-}" != "1" ]; then
  echo "This will permanently delete, in account ${ACCOUNT_ID} (${AWS_REGION}):"
  echo "  - Lambda function and function URL: ${FUNCTION_NAME}"
  echo "  - CloudWatch log group:             /aws/lambda/${FUNCTION_NAME}"
  echo "  - ECR repository and ALL images:    ${REPO_NAME}"
  echo "  - IAM role:                         ${ROLE_NAME}"
  read -r -p "Type the function name to confirm: " ANSWER
  [ "$ANSWER" = "$FUNCTION_NAME" ] || { echo "Aborted."; exit 1; }
fi

# ---- 1. Function URL --------------------------------------------------------
echo "==> [URL] Deleting function URL"
# `get-function-url-config` succeeds only if a URL exists.
if aws lambda get-function-url-config --function-name "$FUNCTION_NAME" >/dev/null 2>&1; then
  aws lambda delete-function-url-config --function-name "$FUNCTION_NAME"
else
  echo "    Not found, skipping."
fi

# ---- 2. Lambda function -----------------------------------------------------
echo "==> [Lambda] Deleting function: ${FUNCTION_NAME}"
# Deleting the function also removes its resource-based policy (the public-access permissions).
if aws lambda get-function --function-name "$FUNCTION_NAME" >/dev/null 2>&1; then
  aws lambda delete-function --function-name "$FUNCTION_NAME"
else
  echo "    Not found, skipping."
fi

# ---- 3. CloudWatch logs -----------------------------------------------------
echo "==> [Logs] Deleting log group: /aws/lambda/${FUNCTION_NAME}"
# Lambda creates this log group automatically on the first invocation and does NOT
# delete it with the function, so logs would keep being stored (and billed).
# `describe-log-groups` with a name prefix returns the group's name if it exists.
if [ -n "$(aws logs describe-log-groups \
      --log-group-name-prefix "/aws/lambda/${FUNCTION_NAME}" \
      --query 'logGroups[].logGroupName' --output text)" ]; then
  aws logs delete-log-group --log-group-name "/aws/lambda/${FUNCTION_NAME}"
else
  echo "    Not found, skipping."
fi

# ---- 4. ECR repository ------------------------------------------------------
echo "==> [ECR] Deleting repository: ${REPO_NAME}"
# --force deletes the repository even though it still contains images.
if aws ecr describe-repositories --repository-names "$REPO_NAME" >/dev/null 2>&1; then
  aws ecr delete-repository --repository-name "$REPO_NAME" --force >/dev/null
else
  echo "    Not found, skipping."
fi

# ---- 5. IAM role ------------------------------------------------------------
echo "==> [IAM] Deleting role: ${ROLE_NAME}"
if aws iam get-role --role-name "$ROLE_NAME" >/dev/null 2>&1; then
  # A role can only be deleted after every policy is detached from it.
  # list-attached-role-policies returns the ARNs of all attached managed policies.
  for POLICY_ARN in $(aws iam list-attached-role-policies \
      --role-name "$ROLE_NAME" \
      --query 'AttachedPolicies[].PolicyArn' --output text); do
    aws iam detach-role-policy --role-name "$ROLE_NAME" --policy-arn "$POLICY_ARN"
  done
  aws iam delete-role --role-name "$ROLE_NAME"
else
  echo "    Not found, skipping."
fi

echo
echo "Everything was deleted."
