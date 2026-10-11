#!/usr/bin/env bash
#
# deploy.sh — runs every deploy step in order.
#
# Usage:
#   ./scripts/deploy.sh
#   AWS_REGION=sa-east-1 AUTH_TYPE=NONE ./scripts/deploy.sh
#
# Each step can also be run on its own, e.g. ./scripts/01_ecr.sh to only rebuild and push.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Order matters: the image must exist (01) and the role must exist (02)
# before the function is created (03), and the URL needs the function (04).
"${SCRIPT_DIR}/01_ecr.sh"
"${SCRIPT_DIR}/02_iam.sh"
"${SCRIPT_DIR}/03_lambda.sh"
"${SCRIPT_DIR}/04_function_url.sh"

echo
echo "Deploy finished."
