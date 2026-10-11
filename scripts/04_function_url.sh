#!/usr/bin/env bash
#
# 04_function_url.sh — Lambda Function URL: give the function an HTTPS endpoint.
#
# AUTH_TYPE=AWS_IAM (default): only requests signed with AWS credentials are accepted.
# AUTH_TYPE=NONE            : anyone on the internet can call it. Use only for quick tests.
#
# Safe to re-run: it creates the URL if missing, switches its auth type if it changed,
# and keeps the permissions in sync with the chosen auth type.

source "$(dirname "${BASH_SOURCE[0]}")/config.sh"

# Adds a statement to the function's resource-based policy, unless it already exists.
# `get-policy` returns the current policy (and fails if there is none yet).
add_permission_if_missing() {
  local statement_id="$1"; shift
  if aws lambda get-policy --function-name "$FUNCTION_NAME" \
       --query Policy --output text 2>/dev/null | grep -q "$statement_id"; then
    echo "    Permission ${statement_id} already exists, skipping."
  else
    aws lambda add-permission \
      --function-name "$FUNCTION_NAME" \
      --statement-id "$statement_id" "$@" >/dev/null
  fi
}

# Removes a statement from the resource-based policy, if it is there.
remove_permission_if_present() {
  local statement_id="$1"
  if aws lambda get-policy --function-name "$FUNCTION_NAME" \
       --query Policy --output text 2>/dev/null | grep -q "$statement_id"; then
    aws lambda remove-permission \
      --function-name "$FUNCTION_NAME" \
      --statement-id "$statement_id"
  fi
}

echo "==> [URL] Ensuring function URL exists (auth type: ${AUTH_TYPE})"

# `get-function-url-config` fails if the function has no URL yet.
if aws lambda get-function-url-config --function-name "$FUNCTION_NAME" >/dev/null 2>&1; then

  # The URL already exists: read its current auth type and update it only if it differs.
  CURRENT_AUTH_TYPE="$(aws lambda get-function-url-config \
    --function-name "$FUNCTION_NAME" --query AuthType --output text)"

  if [ "$CURRENT_AUTH_TYPE" != "$AUTH_TYPE" ]; then
    echo "    Changing auth type: ${CURRENT_AUTH_TYPE} -> ${AUTH_TYPE}"
    aws lambda update-function-url-config \
      --function-name "$FUNCTION_NAME" \
      --auth-type "$AUTH_TYPE" >/dev/null
  else
    echo "    Auth type is already ${AUTH_TYPE}."
  fi

else
  # create-function-url-config: creates a dedicated https://<id>.lambda-url.<region>.on.aws address.
  aws lambda create-function-url-config \
    --function-name "$FUNCTION_NAME" \
    --auth-type "$AUTH_TYPE" >/dev/null
fi

if [ "$AUTH_TYPE" = "NONE" ]; then
  # Public URL: the resource-based policy must explicitly allow everyone.
  # When set up through the CLI, BOTH statements are required, added separately.

  # Allows anyone ("*") to call the function URL (only while the URL's auth type is NONE).
  add_permission_if_missing UrlPolicyInvokeURL \
    --action lambda:InvokeFunctionUrl \
    --principal "*" \
    --function-url-auth-type NONE

  # Allows anyone to invoke the function, but only when the call comes through the function URL.
  add_permission_if_missing UrlPolicyInvokeFunction \
    --action lambda:InvokeFunction \
    --principal "*" \
    --invoked-via-function-url
else
  # Private URL: make sure no public-access statements are left over from a previous NONE setup.
  remove_permission_if_present UrlPolicyInvokeURL
  remove_permission_if_present UrlPolicyInvokeFunction
fi

# Read the URL back so we can show it. --query picks one field; --output text removes the JSON quotes.
FUNCTION_URL="$(aws lambda get-function-url-config \
  --function-name "$FUNCTION_NAME" \
  --query FunctionUrl --output text)"

echo "==> [URL] Done: ${FUNCTION_URL}"