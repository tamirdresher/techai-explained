---
title: "Building Internal Developer Platforms with Backstage"
description: "A practical guide to setting up Backstage as your Internal Developer Portal — software catalog, scaffolding templates, TechDocs, and the plugins that make platform engineering real."
date: 2026-03-07
tags: ["DevOps"]
readTime: "13 min read"
---

Platform engineering is the practice of building a self-service layer on top of your infrastructure so developers can ship without filing tickets. Backstage, created by Spotify and donated to the CNCF, is the leading open-source framework for building these Internal Developer Portals (IDPs).

This guide walks you through setting up Backstage from scratch and configuring the four capabilities that matter most.

## What Backstage Actually Does

<div class="diagram-box">
┌─────────────────────────────────────────────────────────┐
│                  BACKSTAGE PORTAL                       │
│                                                         │
│  ┌─────────────┐ ┌──────────────┐ ┌─────────────────┐  │
│  │  SOFTWARE    │ │ SCAFFOLDER   │ │   TECHDOCS      │  │
│  │  CATALOG     │ │ (Templates)  │ │                 │  │
│  │             │ │              │ │  Docs-as-code   │  │
│  │  Every svc, │ │  Create new  │ │  rendered from  │  │
│  │  its owner, │ │  services    │ │  markdown in    │  │
│  │  its APIs,  │ │  from golden │ │  each repo      │  │
│  │  its deps   │ │  paths       │ │                 │  │
│  └─────────────┘ └──────────────┘ └─────────────────┘  │
│                                                         │
│  ┌─────────────┐ ┌──────────────┐ ┌─────────────────┐  │
│  │  KUBERNETES  │ │  CI/CD       │ │  SEARCH         │  │
│  │  PLUGIN      │ │  PLUGIN      │ │                 │  │
│  │             │ │              │ │  Find anything  │  │
│  │  Pod status, │ │  Pipeline   │ │  across all     │  │
│  │  logs,       │ │  status,    │ │  services,      │  │
│  │  deployments │ │  history    │ │  docs, APIs     │  │
│  └─────────────┘ └──────────────┘ └─────────────────┘  │
└─────────────────────────────────────────────────────────┘
</div>

## Step 1: Create a Backstage App

```bash
npx @backstage/create-app@latest
# Enter app name: my-developer-portal
cd my-developer-portal
yarn dev
```

This starts Backstage at `http://localhost:3000` with a default catalog.

## Step 2: The Software Catalog

The catalog is the foundation — a registry of every service, library, API, and resource in your organization.

### Registering a Service

Each service has a `catalog-info.yaml` in its repo:

```yaml
# catalog-info.yaml (in the service's repository)
apiVersion: backstage.io/v1alpha1
kind: Component
metadata:
  name: order-api
  description: REST API for order management
  tags:
    - typescript
    - rest-api
    - production
  annotations:
    github.com/project-slug: my-org/order-api
    backstage.io/techdocs-ref: dir:.
  links:
    - url: https://grafana.internal/d/order-api
      title: Grafana Dashboard
      icon: dashboard
spec:
  type: service
  lifecycle: production
  owner: team-commerce
  system: commerce-platform
  providesApis:
    - order-api
  consumesApis:
    - payment-api
    - inventory-api
  dependsOn:
    - resource:orders-database
    - resource:redis-cache
```

### Auto-Discovery

Don't register services manually. Use auto-discovery to scan your GitHub org:

```yaml
# app-config.yaml
catalog:
  providers:
    github:
      myOrg:
        organization: 'my-org'
        catalogPath: '/catalog-info.yaml'
        filters:
          branch: 'main'
          repository: '.*'
        schedule:
          frequency: { minutes: 30 }
          timeout: { minutes: 3 }
```

Backstage scans every repo in your org every 30 minutes, discovering and registering any service with a `catalog-info.yaml`.

### System and Domain Modeling

Group services into systems and domains for a birds-eye view:

```yaml
# system: commerce-platform
apiVersion: backstage.io/v1alpha1
kind: System
metadata:
  name: commerce-platform
  description: All services powering the e-commerce experience
spec:
  owner: team-commerce
  domain: shopping

# domain: shopping
apiVersion: backstage.io/v1alpha1
kind: Domain
metadata:
  name: shopping
  description: The end-to-end shopping experience
spec:
  owner: group:engineering-leadership
```

## Step 3: Software Templates (Golden Paths)

Templates let developers create new services in minutes with all the right defaults — CI/CD, monitoring, security, and documentation pre-configured.

### Creating a Template

```yaml
# templates/node-service/template.yaml
apiVersion: scaffolder.backstage.io/v1beta3
kind: Template
metadata:
  name: node-service
  title: Node.js Microservice
  description: Create a production-ready Node.js service with Express, TypeScript, CI/CD, and monitoring
  tags:
    - nodejs
    - typescript
    - recommended
spec:
  owner: team-platform
  type: service

  parameters:
    - title: Service Details
      required: [name, description, owner]
      properties:
        name:
          title: Service Name
          type: string
          pattern: '^[a-z][a-z0-9-]*$'
          description: Lowercase with hyphens (e.g., order-api)
        description:
          title: Description
          type: string
        owner:
          title: Owner Team
          type: string
          ui:field: OwnerPicker
          ui:options:
            catalogFilter:
              kind: Group

    - title: Infrastructure
      properties:
        database:
          title: Database
          type: string
          enum: [none, postgresql, mongodb]
          default: none
        cache:
          title: Cache
          type: string
          enum: [none, redis]
          default: none
        messageQueue:
          title: Message Queue
          type: string
          enum: [none, rabbitmq, kafka]
          default: none

  steps:
    - id: fetch-template
      name: Fetch Template
      action: fetch:template
      input:
        url: ./skeleton
        values:
          name: '${{ parameters.name }}'
          description: '${{ parameters.description }}'
          owner: '${{ parameters.owner }}'
          database: '${{ parameters.database }}'
          cache: '${{ parameters.cache }}'

    - id: publish
      name: Create Repository
      action: publish:github
      input:
        allowedHosts: ['github.com']
        repoUrl: 'github.com?owner=my-org&repo=${{ parameters.name }}'
        description: '${{ parameters.description }}'
        defaultBranch: main

    - id: register
      name: Register in Catalog
      action: catalog:register
      input:
        repoContentsUrl: '${{ steps.publish.output.repoContentsUrl }}'
        catalogInfoPath: /catalog-info.yaml

  output:
    links:
      - title: Repository
        url: '${{ steps.publish.output.remoteUrl }}'
      - title: Open in Catalog
        icon: catalog
        entityRef: '${{ steps.register.output.entityRef }}'
```

What happens when a developer uses this template:
1. Fill out the form (name, owner, database choice)
2. Template generates a full project from the skeleton
3. GitHub repo is created with CI/CD, Dockerfile, and monitoring pre-configured
4. Service is automatically registered in the Backstage catalog

**Time to production-ready service: ~3 minutes** instead of 2-3 days.

## Step 4: TechDocs

TechDocs renders Markdown documentation from each service's repository directly in Backstage. Documentation lives next to the code, always current.

### Enable in a Service

Add to the service's repo:

```yaml
# docs/
# ├── index.md
# ├── architecture.md
# └── runbook.md

# mkdocs.yml (in repo root)
site_name: Order API
nav:
  - Home: index.md
  - Architecture: architecture.md
  - Runbook: runbook.md

plugins:
  - techdocs-core
```

The `backstage.io/techdocs-ref: dir:.` annotation in `catalog-info.yaml` tells Backstage to build docs from this repo. Developers see rendered documentation directly in the service's Backstage page.

## Step 5: Essential Plugins

### Kubernetes Plugin

Shows pod status, deployments, and logs for each service:

```yaml
# catalog-info.yaml annotation
metadata:
  annotations:
    backstage.io/kubernetes-id: order-api
    backstage.io/kubernetes-namespace: production
```

Developers see:
- Pod count and status (Running, Pending, CrashLoopBackOff)
- Recent deployments with rollout status
- Resource usage (CPU, memory)
- Pod logs (without needing `kubectl` access)

### CI/CD Plugin (GitHub Actions)

```yaml
metadata:
  annotations:
    github.com/project-slug: my-org/order-api
```

Shows workflow runs, build status, and deployment history directly in Backstage.

### API Documentation Plugin

Register APIs alongside services:

```yaml
apiVersion: backstage.io/v1alpha1
kind: API
metadata:
  name: order-api
  description: Order management REST API
spec:
  type: openapi
  lifecycle: production
  owner: team-commerce
  definition:
    $text: ./openapi.yaml
```

Renders interactive OpenAPI documentation in Backstage.

## Measuring Platform Success

Track these metrics to know if your IDP is working:

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Time to first deploy | < 30 min | Track template usage → first pipeline run |
| Catalog coverage | > 90% | Services in Backstage / total services |
| Self-service rate | > 80% | Infra requests via templates / total requests |
| Developer satisfaction | > 4/5 | Quarterly survey |
| Onboarding time | < 1 week | New hire → first PR merged |

## Common Mistakes

1. **Empty catalog on launch** — pre-populate before announcing to the org
2. **Too many templates** — start with 2-3 golden paths, not 20 options
3. **No ownership data** — a catalog without owners is just a list
4. **Building alone** — platform engineering is a product; talk to your developer-customers
5. **Perfection before launch** — ship with the catalog + one template; iterate from there

The portal is only as good as the data in it and the golden paths it provides. Start small, measure adoption, and expand based on what developers actually need.

*Published by the TechAI Explained Team.*
