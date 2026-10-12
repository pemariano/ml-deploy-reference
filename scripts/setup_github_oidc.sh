#!/usr/bin/env bash
#
# setup_github_oidc.sh — ONE-TIME setup so GitHub Actions can access AWS without access keys.
#
# It creates:
#   1. An OIDC identity provider: tells AWS to trust tokens issued by GitHub Actions.
#   2. An IAM role that only YOUR repository, running on ONE branch, can assume.
#
# Usage:
#   GITHUB_REPO=your-user/ml-deploy-reference ./scripts/setup_github_oidc.sh
#
# Safe to re-run: existing resources are reused and the trust policy is refreshed.

source "$(dirname "${BASH_SOURCE[0]}")/config.sh"

# Required: the repository in "owner/name" form. The script stops with a message if it is missing.
: "${GITHUB_REPO:?Set GITHUB_REPO=owner/repo, e.g. GITHUB_REPO=pemariano/ml-deploy-reference}"

CI_ROLE_NAME="${CI_ROLE_NAME:-github-actions-mlops-deploy}"   # name of the role GitHub will assume
DEPLOY_BRANCH="${DEPLOY_BRANCH:-main}"                        # only workflows on this branch may assume it

# Permissions given to the role. AdministratorAccess keeps this sandbox setup simple, because the
# deploy creates IAM roles; the protection comes from the trust policy below. Narrow it later.
CI_POLICY_ARN="${CI_POLICY_ARN:-arn:aws:iam::aws:policy/AdministratorAccess}"

OIDC_HOST="token.actions.githubusercontent.com"
PROVIDER_ARN="arn:aws:iam::${ACCOUNT_ID}:oidc-provider/${OIDC_HOST}"
CI_ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${CI_ROLE_NAME}"

echo "==> [OIDC] Ensuring GitHub identity provider exists"
# `get-open-id-connect-provider` fails when the provider doesn't exist yet.
if ! aws iam get-open-id-connect-provider --open-id-connect-provider-arn "$PROVIDER_ARN" >/dev/null 2>&1; then
  # create-open-id-connect-provider registers GitHub as a trusted token issuer.
  #   --url              : GitHub's OIDC issuer.
  #   --client-id-list   : the audience GitHub tokens are issued for (AWS's token service).
  #   --thumbprint-list  : required by the CLI; AWS validates GitHub's certificate on its own,
  #                        so this value is not used for the check.
  aws iam create-open-id-connect-provider \
    --url "https://${OIDC_HOST}" \
    --client-id-list sts.amazonaws.com \
    --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1 >/dev/null
else
  echo "    Provider already exists, skipping."
fi

# Trust policy: WHO may assume the role.
#   - Federated principal : tokens from the GitHub provider above.
#   - aud condition       : the token must be meant for AWS (sts.amazonaws.com).
#   - sub condition       : the token must come from THIS repo and THIS branch. Any other
#                           repository, fork or branch is rejected.
TRUST_POLICY=$(cat <<POLICY
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Federated": "${PROVIDER_ARN}"},
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {"${OIDC_HOST}:aud": "sts.amazonaws.com"},
      "StringLike":   {"${OIDC_HOST}:sub": "repo:${GITHUB_REPO}:ref:refs/heads/${DEPLOY_BRANCH}"}
    }
  }]
}
POLICY
)

echo "==> [OIDC] Ensuring role exists: ${CI_ROLE_NAME}"
if ! aws iam get-role --role-name "$CI_ROLE_NAME" >/dev/null 2>&1; then
  aws iam create-role \
    --role-name "$CI_ROLE_NAME" \
    --assume-role-policy-document "$TRUST_POLICY" >/dev/null
else
  # Role exists: refresh its trust policy (e.g. if the repo or branch changed).
  aws iam update-assume-role-policy \
    --role-name "$CI_ROLE_NAME" \
    --policy-document "$TRUST_POLICY"
fi

# attach-role-policy is idempotent: attaching a policy that is already attached does nothing.
aws iam attach-role-policy --role-name "$CI_ROLE_NAME" --policy-arn "$CI_POLICY_ARN"

echo
echo "==> [OIDC] Done."
echo "Role ARN: ${CI_ROLE_ARN}"
echo
echo "Next: save it in GitHub as a repository variable named AWS_ROLE_ARN:"
echo "  Settings -> Secrets and variables -> Actions -> Variables -> New repository variable"
echo "  (or: gh variable set AWS_ROLE_ARN --body \"${CI_ROLE_ARN}\")"
