#!/usr/bin/env bash
#
# config.sh — shared settings for every deploy step.
#
# This file is SOURCED by the other scripts (`source config.sh`); it is not meant
# to be executed on its own. Every value can be overridden from the shell, e.g.:
#   AWS_REGION=sa-east-1 ./scripts/deploy.sh

# -e: exit as soon as a command fails
# -u: treat unset variables as errors
# -o pipefail: a pipeline fails if ANY command in it fails (not only the last one)
set -euo pipefail

# Absolute path of the folder where this file lives, and of the project root (one level up).
# Resolving paths this way lets you run the scripts from any directory.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# ---- Settings you may want to change ---------------------------------------
AWS_REGION="${AWS_REGION:-us-east-1}"             # region where everything is created
FUNCTION_NAME="${FUNCTION_NAME:-mlops-model}"     # Lambda function name
REPO_NAME="${REPO_NAME:-mlops-model}"             # ECR repository name
ROLE_NAME="${ROLE_NAME:-mlops-model-lambda-role}" # IAM execution role name
MEMORY_MB="${MEMORY_MB:-1024}"                    # Lambda memory (CPU scales with it)
TIMEOUT_S="${TIMEOUT_S:-30}"                      # max seconds per invocation
ARCH="${ARCH:-arm64}"                             # arm64 | x86_64 (image and function must match)
AUTH_TYPE="${AUTH_TYPE:-NONE}"                 # function URL: AWS_IAM (private) | NONE (public)

# Translate the Lambda architecture name into the Docker platform name.
case "$ARCH" in
  arm64)  PLATFORM="linux/arm64" ;;
  x86_64) PLATFORM="linux/amd64" ;;
  *) echo "ARCH must be 'arm64' or 'x86_64' (got '$ARCH')" >&2; exit 1 ;;
esac

# Make the AWS CLI use the chosen region for every command.
export AWS_DEFAULT_REGION="$AWS_REGION"

# ---- Values derived from your AWS account ----------------------------------
# Account ID of the credentials currently configured in the AWS CLI.
ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"

# Address of your private container registry (ECR).
REGISTRY="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

# Image tag = short git commit hash, so each image can be traced back to a commit.
# Override with IMAGE_TAG=... if you are not inside a git repository.
IMAGE_TAG="${IMAGE_TAG:-$(git -C "$PROJECT_ROOT" rev-parse --short HEAD)}"

# Full image address and the role ARN, reused by several steps.
IMAGE_URI="${REGISTRY}/${REPO_NAME}:${IMAGE_TAG}"
ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"
