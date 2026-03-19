---
title: "GitHub Actions Advanced: Matrix Builds, Reusable Workflows, and OIDC"
description: "Level up your CI/CD with GitHub Actions advanced patterns — matrix strategies for multi-platform testing, reusable workflows for DRY pipelines, and OIDC for secretless cloud deployments."
date: 2026-03-10
tags: ["DevOps"]
readTime: "12 min read"
---

If your GitHub Actions workflows are still a single YAML file with hardcoded values, you're leaving most of the platform's power on the table. This guide covers the three patterns that separate basic CI/CD from production-grade pipelines: matrix builds, reusable workflows, and OIDC authentication.

## Matrix Builds: Test Everything in Parallel

Matrix strategies let you run the same job across multiple configurations simultaneously — different OS versions, language versions, or any variable you define.

### Basic Matrix

{% raw %}```yaml
name: CI
on: [push, pull_request]

jobs:
  test:
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        node-version: [18, 20, 22]
      fail-fast: false  # Don't cancel other jobs if one fails

    runs-on: ${{ matrix.os }}
    
    steps:
      - uses: actions/checkout@v4
      
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node-version }}
          cache: npm
      
      - run: npm ci
      - run: npm test
```{% endraw %}

This creates **9 parallel jobs** (3 OS × 3 Node versions). Without matrix, you'd copy-paste the same job 9 times.

<div class="diagram-box">
MATRIX EXPANSION: 3 OS × 3 Node = 9 parallel jobs

ubuntu-latest + Node 18  ──► ✅
ubuntu-latest + Node 20  ──► ✅
ubuntu-latest + Node 22  ──► ✅
windows-latest + Node 18 ──► ✅
windows-latest + Node 20 ──► ❌ (test failure)
windows-latest + Node 22 ──► ✅
macos-latest + Node 18   ──► ✅
macos-latest + Node 20   ──► ✅
macos-latest + Node 22   ──► ✅

fail-fast: false → all 9 run even if one fails
fail-fast: true  → cancel remaining after first failure
</div>

### Advanced Matrix: Include and Exclude

{% raw %}```yaml
strategy:
  matrix:
    os: [ubuntu-latest, windows-latest]
    node-version: [18, 20, 22]
    
    # Add specific combinations with extra variables
    include:
      - os: ubuntu-latest
        node-version: 22
        coverage: true        # Only run coverage on one combo
        experimental: false
      
      - os: ubuntu-latest
        node-version: 23      # Add a version not in the base matrix
        experimental: true    # Mark as allowed-to-fail
    
    # Remove specific combinations
    exclude:
      - os: windows-latest
        node-version: 18      # Don't test Node 18 on Windows
```

### Using Matrix Variables in Steps

```yaml
steps:
  - run: npm test
  
  - name: Upload coverage
    if: matrix.coverage == true
    run: npm run coverage && npx codecov
  
  - name: Mark experimental as non-blocking
    if: matrix.experimental == true
    continue-on-error: true
    run: npm run test:experimental
```

### Dynamic Matrix from JSON

For maximum flexibility, generate the matrix dynamically:

```yaml
jobs:
  determine-matrix:
    runs-on: ubuntu-latest
    outputs:
      matrix: ${{ steps.set-matrix.outputs.matrix }}
    steps:
      - id: set-matrix
        run: |
          # Could read from a file, API, or compute dynamically
          echo 'matrix={"include":[
            {"project":"api","dockerfile":"api/Dockerfile"},
            {"project":"web","dockerfile":"web/Dockerfile"},
            {"project":"worker","dockerfile":"worker/Dockerfile"}
          ]}' >> $GITHUB_OUTPUT

  build:
    needs: determine-matrix
    strategy:
      matrix: ${{ fromJSON(needs.determine-matrix.outputs.matrix) }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: docker build -f ${{ matrix.dockerfile }} -t ${{ matrix.project }} .
```{% endraw %}

## Reusable Workflows: DRY CI/CD

If you have 20 repositories with nearly identical CI workflows, reusable workflows let you define the pipeline once and call it from everywhere.

### Create a Reusable Workflow

{% raw %}```yaml
# .github/workflows/build-and-deploy.yml (in your shared repo)
name: Build and Deploy

on:
  workflow_call:  # This makes it reusable
    inputs:
      environment:
        required: true
        type: string
        description: "Target environment (staging, production)"
      node-version:
        required: false
        type: number
        default: 20
      run-e2e:
        required: false
        type: boolean
        default: true
    secrets:
      DEPLOY_TOKEN:
        required: true
      SLACK_WEBHOOK:
        required: false

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ inputs.node-version }}
          cache: npm
      
      - run: npm ci
      - run: npm run build
      - run: npm test
      
      - name: E2E Tests
        if: inputs.run-e2e
        run: npm run test:e2e
      
      - uses: actions/upload-artifact@v4
        with:
          name: build-output
          path: dist/

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment: ${{ inputs.environment }}
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: build-output
          path: dist/
      
      - name: Deploy
        run: ./deploy.sh ${{ inputs.environment }}
        env:
          DEPLOY_TOKEN: ${{ secrets.DEPLOY_TOKEN }}
      
      - name: Notify Slack
        if: always() && secrets.SLACK_WEBHOOK != ''
        run: |
          curl -X POST ${{ secrets.SLACK_WEBHOOK }} \
            -H 'Content-Type: application/json' \
            -d '{"text":"Deploy to ${{ inputs.environment }}: ${{ job.status }}"}'
```{% endraw %}

### Call the Reusable Workflow

{% raw %}```yaml
# In any consuming repository
name: Deploy to Staging

on:
  push:
    branches: [main]

jobs:
  deploy:
    uses: my-org/shared-workflows/.github/workflows/build-and-deploy.yml@main
    with:
      environment: staging
      node-version: 22
      run-e2e: true
    secrets:
      DEPLOY_TOKEN: ${{ secrets.DEPLOY_TOKEN }}
      SLACK_WEBHOOK: ${{ secrets.SLACK_WEBHOOK }}
```{% endraw %}

### Composite Actions: Reusable Steps

For reusing a sequence of steps (not full workflows), use composite actions:

{% raw %}```yaml
# .github/actions/setup-and-build/action.yml
name: Setup and Build
description: Install dependencies and build the project

inputs:
  node-version:
    description: Node.js version
    default: '20'

runs:
  using: composite
  steps:
    - uses: actions/setup-node@v4
      with:
        node-version: ${{ inputs.node-version }}
        cache: npm
    
    - run: npm ci
      shell: bash
    
    - run: npm run build
      shell: bash
    
    - run: npm run lint
      shell: bash
```{% endraw %}

Use it in any workflow:

{% raw %}```yaml
steps:
  - uses: actions/checkout@v4
  - uses: my-org/shared-actions/.github/actions/setup-and-build@main
    with:
      node-version: 22
  - run: npm test
```

<div class="diagram-box">
REUSABLE WORKFLOWS vs COMPOSITE ACTIONS

Reusable Workflows              Composite Actions
────────────────────            ──────────────────
Reuse entire JOBS               Reuse STEPS within a job
Called with `uses:` at job      Called with `uses:` at step
level                           level

Can define multiple jobs        Single sequence of steps
Have their own runner           Run on the caller's runner
Can accept secrets              Cannot accept secrets
Separate workflow file          action.yml in a directory

USE WHEN:                       USE WHEN:
Full CI/CD pipeline             Shared setup/teardown steps
Multi-job orchestration         Linting, building, caching
Environment-specific deploys    Common action sequences
</div>

## OIDC: Secretless Cloud Deployments

OpenID Connect (OIDC) eliminates stored cloud credentials. Instead of storing an AWS access key or Azure service principal secret in GitHub, the workflow requests a short-lived token directly from the cloud provider.

### How OIDC Works

<div class="diagram-box">
TRADITIONAL (with secrets)       OIDC (secretless)
──────────────────────────       ─────────────────

1. Store cloud credentials      1. Configure trust between
   in GitHub Secrets               GitHub and cloud provider

2. Workflow reads secret         2. Workflow requests JWT
   from secrets context             from GitHub's OIDC provider

3. Use credential to auth       3. Exchange JWT for short-lived
   with cloud provider              cloud credential

4. Credential is long-lived     4. Credential expires in minutes
   (rotate manually)               (no rotation needed)

RISK: Secret leak = full        RISK: Minimal — tokens are
access until rotated            scoped and short-lived
</div>

### Azure OIDC Setup

**Step 1: Create a federated credential in Azure**

```bash
# Create an app registration
az ad app create --display-name "github-actions-deploy"
APP_ID=$(az ad app list --display-name "github-actions-deploy" --query '[0].appId' -o tsv)

# Create a service principal
az ad sp create --id $APP_ID

# Add federated credential for GitHub Actions
az ad app federated-credential create --id $APP_ID --parameters '{
  "name": "github-main-branch",
  "issuer": "https://token.actions.githubusercontent.com",
  "subject": "repo:my-org/my-repo:ref:refs/heads/main",
  "audiences": ["api://AzureADTokenExchange"]
}'

# Assign roles
az role assignment create \
  --assignee $APP_ID \
  --role "Contributor" \
  --scope "/subscriptions/YOUR_SUB_ID"
```

**Step 2: Use in your workflow**

```yaml
name: Deploy to Azure

on:
  push:
    branches: [main]

permissions:
  id-token: write   # Required for OIDC
  contents: read

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: azure/login@v2
        with:
          client-id: ${{ vars.AZURE_CLIENT_ID }}
          tenant-id: ${{ vars.AZURE_TENANT_ID }}
          subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}
          # No secret needed! OIDC handles authentication

      - run: az webapp deploy --name myapp --src-path ./dist
```{% endraw %}

### AWS OIDC Setup

{% raw %}```yaml
permissions:
  id-token: write
  contents: read

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789:role/github-actions
          aws-region: us-east-1
          # No AWS_ACCESS_KEY_ID or AWS_SECRET_ACCESS_KEY needed!
      
      - run: aws s3 sync ./dist s3://my-bucket/
```

### OIDC Subject Claims

Control which workflows can assume which roles:

```
repo:my-org/my-repo:ref:refs/heads/main         → Only main branch
repo:my-org/my-repo:environment:production       → Only production env
repo:my-org/my-repo:pull_request                 → Any PR
repo:my-org/my-repo:ref:refs/tags/v*             → Only version tags
```

This means a PR workflow **cannot** assume the production deployment role. Security by design.

## Putting It All Together

Here's a production pipeline combining all three patterns:

```yaml
name: Full Pipeline

on:
  push:
    branches: [main]
  pull_request:

permissions:
  id-token: write
  contents: read

jobs:
  # Matrix: test across platforms
  test:
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest]
        node: [20, 22]
      fail-fast: false
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: ./.github/actions/setup-and-build  # Composite action
        with:
          node-version: ${{ matrix.node }}
      - run: npm test

  # Reusable workflow: deploy to staging
  deploy-staging:
    if: github.ref == 'refs/heads/main'
    needs: test
    uses: ./.github/workflows/deploy.yml
    with:
      environment: staging
    secrets: inherit

  # OIDC: deploy to production
  deploy-production:
    if: github.ref == 'refs/heads/main'
    needs: deploy-staging
    runs-on: ubuntu-latest
    environment: production  # Requires approval
    steps:
      - uses: actions/checkout@v4
      - uses: azure/login@v2
        with:
          client-id: ${{ vars.AZURE_CLIENT_ID }}
          tenant-id: ${{ vars.AZURE_TENANT_ID }}
          subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}
      - run: ./deploy.sh production
```{% endraw %}

## Common Pitfalls

1. **Not using `fail-fast: false`** — one flaky test cancels all matrix jobs
2. **Storing cloud secrets** — use OIDC instead; it's more secure and no rotation needed
3. **Copy-pasting workflows** — use reusable workflows and composite actions
4. **No caching** — always cache `node_modules`, `~/.m2`, `~/.gradle`, etc.
5. **Overly broad OIDC subjects** — scope to specific branches and environments

*Published by the TechAI Explained Team.*
