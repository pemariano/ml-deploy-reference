#!/usr/bin/env bash
#
# 01_ecr.sh — Amazon ECR: create the repository, log in, build and push the image.
#
# ECR is AWS's private container registry. Lambda pulls your image from here.

# shellcheck source=config.sh
source "$(dirname "${BASH_SOURCE[0]}")/config.sh"

echo "==> [ECR] Checking that Docker is running"
# `docker info` fails if the Docker daemon is not up; the output is discarded (>/dev/null 2>&1).
docker info >/dev/null 2>&1 || { echo "Docker is not running. Start Docker and try again." >&2; exit 1; }

echo "==> [ECR] Ensuring repository exists: ${REPO_NAME}"
# `describe-repositories` fails when the repo doesn't exist; `||` then runs the create command.
# This makes the step safe to run many times (idempotent).
aws ecr describe-repositories --repository-names "$REPO_NAME" >/dev/null 2>&1 \
  || aws ecr create-repository \
       --repository-name "$REPO_NAME" \
       --image-scanning-configuration scanOnPush=true >/dev/null
       # scanOnPush=true: ECR scans every pushed image for known vulnerabilities.

echo "==> [ECR] Logging Docker in to ${REGISTRY}"
# `get-login-password` prints a temporary (12h) password for ECR.
# It is piped into `docker login`, which reads it from stdin so it never shows up in shell history.
aws ecr get-login-password \
  | docker login --username AWS --password-stdin "$REGISTRY"

echo "==> [ECR] Building and pushing ${IMAGE_URI} for ${PLATFORM}"
# buildx build: builds the image from the Dockerfile in the project root.
#   --platform     : CPU architecture of the image (must match the Lambda architecture).
#   --provenance=false : don't attach build attestations. By default buildx creates a
#                    multi-manifest image that Lambda rejects with a media type error.
#   -t             : name:tag the image will have in ECR.
#   --push         : push straight to the registry after building (no local copy needed).
docker buildx build \
  --platform "$PLATFORM" \
  --provenance=false \
  -t "$IMAGE_URI" \
  --push \
  "$PROJECT_ROOT"

echo "==> [ECR] Done: ${IMAGE_URI}"
