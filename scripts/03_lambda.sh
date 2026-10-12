#!/usr/bin/env bash
#
# 03_lambda.sh — Lambda: create the function from the ECR image, or update it.
#
# Requires: 01_ecr.sh (image pushed) and 02_iam.sh (role created).

# shellcheck source=config.sh
source "$(dirname "${BASH_SOURCE[0]}")/config.sh"

echo "==> [Lambda] Creating or updating function: ${FUNCTION_NAME}"

# `get-function` succeeds only if the function already exists.
if aws lambda get-function --function-name "$FUNCTION_NAME" >/dev/null 2>&1; then

  # Function exists: point it at the new image.
  # Lambda resolves the tag to an image digest at this moment, so re-pushing the same
  # tag and running this command again deploys the new content.
  aws lambda update-function-code \
    --function-name "$FUNCTION_NAME" \
    --image-uri "$IMAGE_URI" >/dev/null

  # Block until the update has finished and the function is ready to be invoked.
  aws lambda wait function-updated-v2 --function-name "$FUNCTION_NAME"

else

  # First deploy: create the function.
  #   --package-type Image : the code comes from a container image, not a zip file.
  #   --code ImageUri=...  : which ECR image to run (the CMD "app.handler" is in the image).
  #   --role               : the execution role created in 02_iam.sh.
  #   --architectures      : CPU architecture, must match the image platform.
  #   --memory-size        : memory in MB (CPU is allocated proportionally).
  #   --timeout            : maximum run time per invocation, in seconds.
  aws lambda create-function \
    --function-name "$FUNCTION_NAME" \
    --package-type Image \
    --code ImageUri="$IMAGE_URI" \
    --role "$ROLE_ARN" \
    --architectures "$ARCH" \
    --memory-size "$MEMORY_MB" \
    --timeout "$TIMEOUT_S" >/dev/null

  # Block until the function leaves the "Pending" state and becomes "Active".
  aws lambda wait function-active-v2 --function-name "$FUNCTION_NAME"
fi

echo "==> [Lambda] Done: ${FUNCTION_NAME}"
