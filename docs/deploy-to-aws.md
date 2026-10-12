# How to deploy this project to AWS Lambda

A step-by-step guide to reproduce the infrastructure of this repository in **your own AWS account**: from cloning the repo to a working Lambda function, and back to an empty account.

There are two ways to deploy. They use the same scripts and create the same resources:

| Path | Where it runs | Best for |
|---|---|---|
| **A. From your terminal** | Your machine (Docker + AWS CLI) | The first deploy, debugging, learning how each step works |
| **B. From GitHub Actions** (manual CD) | GitHub runners, signed in to AWS with OIDC | Repeatable deploys without storing any AWS key |

Nothing is ever deployed automatically: no push, merge or pull request touches AWS. You decide when to deploy and when to destroy.

## What gets created

| Resource | Created by | Purpose |
|---|---|---|
| ECR repository `mlops-model` | `scripts/01_ecr.sh` | Stores the container image |
| IAM role `mlops-model-lambda-role` | `scripts/02_iam.sh` | Lets the function run and write logs |
| Lambda function `mlops-model` | `scripts/03_lambda.sh` | Runs the image |
| Function URL (private by default) | `scripts/04_function_url.sh` | HTTPS endpoint of the function |
| CloudWatch log group `/aws/lambda/mlops-model` | Lambda, on first invocation | Function logs |
| OIDC provider and role `github-actions-mlops-deploy` (Path B only) | `scripts/setup_github_oidc.sh` | Lets GitHub Actions deploy without access keys |

An idle Lambda function costs nothing. What keeps costing a little are the images stored in ECR and the logs in CloudWatch, and the destroy step removes both. See [Clean up](#7-clean-up).

## 1. Prerequisites

| Tool | Needed for | Check |
|---|---|---|
| [Git](https://git-scm.com/) | cloning, image tag (commit hash) | `git --version` |
| [uv](https://docs.astral.sh/uv/) and Python 3.13 | tests (`make test`) | `uv --version` |
| [Docker](https://docs.docker.com/get-docker/) with `buildx` | building and pushing the image (Path A) | `docker info` |
| [AWS CLI **v2**](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) | every AWS command | `aws --version` (must start with `aws-cli/2.`) |
| [GitHub CLI `gh`](https://cli.github.com/) (optional) | setting variables and triggering the workflow from the terminal | `gh --version` |

Install the AWS CLI with the official installer or `brew install awscli` on macOS. Do **not** install the `awscli` package from PyPI: it is v1, which these scripts do not support.

You also need an **AWS account** and, for Path B, a **GitHub account**.

## 2. Prepare your AWS account

Use a sandbox account for this, not one that runs production workloads: the deploy creates IAM roles, so the simplest setup uses `AdministratorAccess`.

1. **Create a budget alert** before creating anything: **Billing and Cost Management → Budgets → Create budget**. A "Zero spend" budget warns you as soon as any cost appears, and a monthly budget (for example US$ 5) warns you when you pass a limit.
2. **Know the free plan rule.** Enabling IAM Identity Center (next section) turns your account into an AWS Organization, and AWS may automatically upgrade an account on the Free Tier plan to a paid plan when that happens, which also ends the free credits. Read the current Free Tier terms first. If keeping the free plan matters more to you than temporary credentials, use the IAM user alternative in section 3.3.

## 3. Get AWS credentials on your machine

You need credentials that can create ECR repositories, IAM roles and Lambda functions.

### 3.1 Recommended: IAM Identity Center (SSO)

SSO gives the CLI **temporary credentials** after a browser login, so no long-lived access key is stored on your computer.

**In the AWS console (browser):**

1. **Enable Identity Center.** Search for *IAM Identity Center*, choose the region where it will live (note it down: it is your "SSO region") and click **Enable**, creating the AWS Organization if asked.
2. **Create a permission set.** Go to **Permission sets → Create permission set → Predefined → AdministratorAccess**. The default session lasts 1 hour; you can raise it to 8 hours to log in less often.
3. **Create your user.** Go to **Users → Add user** and fill in username, an e-mail you can access, and your name.
4. **Give the user access to your account.** Go to **AWS accounts**, select your account, click **Assign users or groups**, and choose your user and the `AdministratorAccess` permission set. If you cannot find that option, use the other route: **Users → your user → AWS accounts tab → Assign accounts**.
5. **Accept the invitation.** Open the e-mail, set your password and register an MFA authenticator app.
6. **Copy the access portal URL** from the Identity Center home page. It looks like `https://d-xxxxxxxxxx.awsapps.com/start`.

**In the terminal:**

```bash
aws configure sso
```

| Prompt | Answer |
|---|---|
| SSO session name | any name, for example `mlops-sso` |
| SSO start URL | the access portal URL from step 6 |
| SSO region | the region where you enabled Identity Center |
| SSO registration scopes | press Enter (default `sso:account:access`) |
| Configure AWS skills / MCP server for AI coding agents? | `n` (not needed here) |

Your browser opens: sign in with the user from step 3 and approve. Back in the terminal:

| Prompt | Answer |
|---|---|
| Account | select your account |
| Role | `AdministratorAccess` |
| Default client Region | for example `us-east-1` |
| Default output format | Enter, or `json` |
| Profile name | **`default`** |

Naming the profile `default` is what lets the scripts work without extra setup. If you accepted a long suggested name instead, either rename the header in `~/.aws/config` from `[profile <name>]` to `[default]`, or run `export AWS_PROFILE=<name>` in every new terminal.

When the session expires (`Token has expired`), renew it with `aws sso login`.

### 3.2 Check that it works

```bash
aws sts get-caller-identity
```

It must print JSON with your `Account` and an `Arn`. With SSO, the `Arn` contains `AWSReservedSSO_AdministratorAccess`.

### 3.3 Alternative: IAM user with access keys

Quicker to set up, but the key stays on your machine until you delete it. Never use the root user, enable MFA on the user, never commit the keys, and delete the key when you are done.

1. In the console, go to **IAM → Users → Create user** and attach `AdministratorAccess`.
2. Open the user, go to **Security credentials → Create access key** (use case: *Command Line Interface*) and save the keys.
3. In the terminal, run `aws configure` and enter the access key, the secret key and a default region (for example `us-east-1`).

Then check it with `aws sts get-caller-identity`.

## 4. Path A: deploy from your terminal

Make sure Docker is running and `aws sts get-caller-identity` works.

```bash
git clone https://github.com/<your-user>/ml-deploy-reference.git   # or your fork
cd ml-deploy-reference

make install      # installs the dependencies with uv
make test         # optional, but recommended: must pass before deploying
make deploy       # same as ./scripts/deploy.sh
```

The repository must be a git repository with at least one commit, because the image tag is the commit hash. If it is not, set `IMAGE_TAG=...` yourself.

`make deploy` runs four steps in order. Each one can also be run on its own:

| Script | What it does |
|---|---|
| `scripts/01_ecr.sh` | Creates the ECR repository, logs Docker in, builds the image and pushes it |
| `scripts/02_iam.sh` | Creates the Lambda execution role (permission to write logs only) |
| `scripts/03_lambda.sh` | Creates the function from the image, or updates it if it already exists |
| `scripts/04_function_url.sh` | Creates the HTTPS Function URL (private by default) and prints it |

The scripts are idempotent: after changing the code, run `make deploy` again to redeploy. Every script reads its settings from `scripts/config.sh`, which you can override with environment variables, for example:

```bash
AWS_REGION=sa-east-1 ARCH=x86_64 make deploy
```

Go to [Test the deployed function](#6-test-the-deployed-function) when it finishes.

## 5. Path B: deploy with GitHub Actions (manual CD)

The `CD (manual)` workflow (`.github/workflows/cd.yml`) runs the same scripts on a GitHub runner. It authenticates to AWS with **OIDC**: GitHub issues a short-lived token for each run, and AWS exchanges it for temporary credentials. No access key or secret is stored in GitHub.

### 5.1 Get the repository into your own GitHub account

Fork this repository (or push a copy to a new repository of yours). Then, if you forked it, open the **Actions** tab and enable workflows, because GitHub disables them on forks by default.

### 5.2 Create the AWS role that GitHub can assume (one time)

Run this on your machine, with the AWS credentials from section 3, replacing `<owner>/<repo>` with **your** repository exactly as it appears on GitHub (same capitalization):

```bash
GITHUB_REPO=<owner>/<repo> ./scripts/setup_github_oidc.sh
```

The script creates two things:

1. An **OIDC identity provider**, which tells AWS to trust tokens issued by GitHub Actions.
2. An **IAM role** (`github-actions-mlops-deploy`) whose trust policy only accepts tokens from **your repository, running on the `main` branch**. Other repositories, forks and branches are rejected.

It prints the **Role ARN** at the end, in the form `arn:aws:iam::<account-id>:role/github-actions-mlops-deploy`.

> The role is given `AdministratorAccess` to keep this sandbox setup simple, because the deploy creates IAM roles. The protection is the trust policy above. To narrow it, pass your own policy with `CI_POLICY_ARN=<arn>`. To trust a branch other than `main`, pass `DEPLOY_BRANCH=<branch>`.

The script is safe to run again: it reuses what exists and refreshes the trust policy.

### 5.3 Tell GitHub which role to use

Create a repository **variable** (not a secret: the ARN is not sensitive) named `AWS_ROLE_ARN`:

- In the browser: **Settings → Secrets and variables → Actions → Variables tab → New repository variable**.
- Or with the GitHub CLI: `gh variable set AWS_ROLE_ARN --body "<role-arn>"`.

No other key or token is needed.

### 5.4 Run the workflow

Open **Actions → CD (manual) → Run workflow**, choose the `main` branch and fill the inputs. The button only appears when `cd.yml` exists on the default branch.

| Input | Options | Default | Notes |
|---|---|---|---|
| `action` | `deploy` or `destroy` | `deploy` | |
| `aws_region` | any region | `us-east-1` | Use the same region for deploy and destroy |
| `arch` | `arm64` or `x86_64` | `arm64` | Must match the function that already exists |
| `auth_type` | `AWS_IAM` or `NONE` | `AWS_IAM` | `NONE` makes the Function URL public |

The same run from the terminal:

```bash
gh workflow run cd.yml -f action=deploy -f aws_region=us-east-1 -f arch=arm64 -f auth_type=AWS_IAM
```

A `deploy` run does this, in order: runs the tests, signs in to AWS with OIDC, builds and pushes the image, creates or updates the function, and **invokes it as a smoke test** that fails the run unless it returns `200` with a `prediction`. A `destroy` run deletes everything without asking for confirmation, because starting the workflow by hand is the confirmation.

**About the architecture.** The GitHub runner is `x86_64`. With `arch=arm64` it builds the image under QEMU emulation, which works but is slower. If you mostly deploy from GitHub Actions, using `x86_64` everywhere avoids the emulation. Keep the same architecture between deploys: the scripts only set it when the function is created, so changing it later means destroying and recreating the function.

## 6. Test the deployed function

Invoke it through the Lambda API (works with any auth type). Replace `us-east-1` if you used another region.

```bash
aws lambda invoke \
  --function-name mlops-model \
  --region us-east-1 \
  --cli-binary-format raw-in-base64-out \
  --payload '{"body": "{\"features\": [1.0, -0.5, 2.3, 0.1]}"}' \
  response.json

cat response.json
```

The terminal shows `{"StatusCode": 200, ...}`, which only means the invocation ran. The handler's answer is in `response.json`:

```json
{
  "statusCode": 200,
  "headers": {"Content-Type": "application/json"},
  "body": "{\"prediction\": 1, \"probability\": 0.7171}"
}
```

The first call is slower (cold start: the model is loaded from the image). Later calls are faster. The exact probability varies between builds because the model is trained on random synthetic data.

**Error paths**, which must both return `"statusCode": 400`:

```bash
# wrong number of features
aws lambda invoke --function-name mlops-model --region us-east-1 \
  --cli-binary-format raw-in-base64-out \
  --payload '{"body": "{\"features\": [1, 2]}"}' response.json && cat response.json

# body is not JSON
aws lambda invoke --function-name mlops-model --region us-east-1 \
  --cli-binary-format raw-in-base64-out \
  --payload '{"body": "not json"}' response.json && cat response.json
```

**Logs:**

```bash
aws logs tail /aws/lambda/mlops-model --region us-east-1 --since 10m
```

**Calling the Function URL.** By default it is private (`AWS_IAM`), so a plain `curl` or a browser gets `403 Forbidden`. That is expected. For a quick public test:

```bash
AUTH_TYPE=NONE ./scripts/04_function_url.sh

curl -s -X POST "<function-url>" \
  -H "Content-Type: application/json" \
  -d '{"features": [1.0, -0.5, 2.3, 0.1]}'
```

Here the body is plain JSON, because the Function URL builds the event itself. Opening the URL in a browser sends a `GET` without a body, so you should see a `400` from the function instead of `Forbidden`, which already proves the access works.

A public URL can be called by anyone who knows it. Switch back with `./scripts/04_function_url.sh` (private again, and the public permissions are removed) or clean up right after testing.

## 7. Clean up

Delete everything the deploy created: the function and its URL, the CloudWatch log group, the ECR repository with all its images, and the IAM role.

```bash
make destroy              # asks you to type the function name to confirm
# YES=1 make destroy      skips the confirmation
```

Or run the **CD (manual)** workflow with `action=destroy` and the same `aws_region` you deployed to.

Verify that nothing is left:

```bash
aws lambda list-functions --query 'Functions[].FunctionName'
aws ecr describe-repositories --query 'repositories[].repositoryName'
```

**Remove the GitHub OIDC access (Path B).** The OIDC provider and the role cost nothing and are intentionally not removed by `destroy`, because the workflow needs them. To remove them for good:

```bash
aws iam detach-role-policy \
  --role-name github-actions-mlops-deploy \
  --policy-arn arn:aws:iam::aws:policy/AdministratorAccess

aws iam delete-role --role-name github-actions-mlops-deploy

aws iam delete-open-id-connect-provider \
  --open-id-connect-provider-arn arn:aws:iam::<account-id>:oidc-provider/token.actions.githubusercontent.com
```

The provider is shared by the whole account: skip the last command if another project of yours uses GitHub OIDC.

## 8. Settings reference

Defaults live in `scripts/config.sh`. Override any of them with environment variables, for example `AWS_REGION=sa-east-1 make deploy`.

| Variable | Default | Meaning |
|---|---|---|
| `AWS_REGION` | `us-east-1` | Region for all resources. Use the same one to destroy |
| `FUNCTION_NAME` | `mlops-model` | Lambda function name |
| `REPO_NAME` | `mlops-model` | ECR repository name |
| `ROLE_NAME` | `mlops-model-lambda-role` | Lambda execution role name |
| `MEMORY_MB` | `1024` | Lambda memory (CPU scales with it) |
| `TIMEOUT_S` | `30` | Lambda timeout in seconds |
| `ARCH` | `arm64` | `arm64` or `x86_64`. The image and the function always use the same one |
| `AUTH_TYPE` | `AWS_IAM` | Function URL: `AWS_IAM` (private) or `NONE` (public) |
| `IMAGE_TAG` | git short commit hash | Image tag. Set it if you are not in a git repository |

Variables used only by `scripts/setup_github_oidc.sh`:

| Variable | Default | Meaning |
|---|---|---|
| `GITHUB_REPO` | (required) | Your repository as `owner/name` |
| `CI_ROLE_NAME` | `github-actions-mlops-deploy` | Name of the role GitHub assumes |
| `DEPLOY_BRANCH` | `main` | Only workflows running on this branch can assume the role |
| `CI_POLICY_ARN` | `arn:aws:iam::aws:policy/AdministratorAccess` | Permissions of that role |

## 9. Troubleshooting

| Symptom | Likely cause and fix |
|---|---|
| `docker: command not found`, or cannot connect to the Docker daemon | Install Docker and start it before `make deploy` |
| `aws: command not found` | Install AWS CLI v2 (section 1) |
| `NoCredentials` or `Unable to locate credentials` | The profile is not named `default`. Run `aws configure list-profiles`, then rename it in `~/.aws/config` or `export AWS_PROFILE=<name>`, then `aws sso login` |
| `Token has expired` | Run `aws sso login` |
| `Permission denied` when running a script | The execute bit is missing. Run `chmod +x scripts/*.sh` |
| `GITHUB_REPO: Set GITHUB_REPO=owner/repo` | Pass the variable: `GITHUB_REPO=<owner>/<repo> ./scripts/setup_github_oidc.sh` |
| `Repository variable AWS_ROLE_ARN is empty or missing` (or `Could not load credentials from any providers`) | Create `AWS_ROLE_ARN` as a **repository variable**, not a secret and not inside an Environment (section 5.3) |
| `Not authorized to perform sts:AssumeRoleWithWebIdentity` | The role's trust policy rejected the token. `GITHUB_REPO` does not match your repository exactly, or the workflow ran on a branch other than `DEPLOY_BRANCH`. Run `setup_github_oidc.sh` again with the right values |
| The **Run workflow** button does not appear | `cd.yml` must exist on the default branch, and Actions must be enabled (forks start with Actions disabled) |
| `Forbidden` when opening the Function URL | It is private by default. Use `aws lambda invoke`, or `AUTH_TYPE=NONE ./scripts/04_function_url.sh` for a public test |
| `404 page not found` on `http://localhost:9000` | Normal for the local emulator: it only accepts `POST` on `/2015-03-31/functions/function/invocations` (use `make invoke`) |
| Lambda rejects the image (unsupported media type) | Build with `--provenance=false`, which `01_ecr.sh` already does |
| The function fails to start after deploy | The image architecture does not match the function. Keep `ARCH` the same for build and function, or destroy and recreate it |
| The deploy ran but I see old code | Check `aws lambda get-function --function-name mlops-model --query Code.ImageUri`: the tag must be your latest commit hash. Commit first, then deploy |
