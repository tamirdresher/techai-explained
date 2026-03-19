---
title: "The 5 Tools Every Platform Engineer Uses Daily"
description: "A video script covering the essential toolkit for platform engineers in 2026 — from internal developer portals to GitOps controllers to infrastructure cost dashboards."
date: 2026-03-12
tags: ["Video Script"]
---

## Video Metadata

- **Target Duration:** 10 minutes
- **Format:** Screen recording demos of each tool + narrated overview
- **Audience:** DevOps engineers transitioning to platform engineering, and engineering leads building platform teams
- **Thumbnail Concept:** Five tool icons arranged in a circle around a "Platform Engineer" title — text "5 ESSENTIAL Tools"

---

## Script Outline

### INTRO (0:00 - 1:00)

**Hook (0:00 - 0:25)**

> "Platform engineering is the hottest role in DevOps. But what does a platform engineer actually DO all day? And more importantly — what tools do they use? I surveyed 200 platform engineers and these five tools came up in almost every response."

**Visual:** Brief montage of tool dashboards — Backstage, ArgoCD, Terraform, Grafana, Crossplane.

**Agenda (0:25 - 1:00)**

> "We'll cover: the internal developer portal, GitOps for deployment, infrastructure-as-code at scale, observability for platform health, and cost management. For each tool, I'll show what it does, why it matters, and the one configuration most teams get wrong."

---

### TOOL 1: Internal Developer Portal — Backstage (1:00 - 3:00)

**What It Does (1:00 - 1:30)**

> "Backstage is the front door to your platform. It's where developers go to create new services, find documentation, check service health, and discover APIs. Think of it as the 'app store' for your internal infrastructure."

**Visual:** Backstage UI showing service catalog, create new component wizard, API docs, TechDocs.

**Why It Matters (1:30 - 2:00)**

> "Without a portal, developers file tickets to create a new service. With Backstage, they click 'Create,' fill out a form, and get a fully configured repo with CI/CD, monitoring, and deployment in minutes."

**Key Features:**
- **Software Catalog:** Every service, its owner, its dependencies, its docs
- **Scaffolding (Templates):** Golden paths for creating new services
- **TechDocs:** Documentation that lives next to the code
- **Plugin Ecosystem:** Kubernetes, CI/CD, cost, security — all in one place

**Demo (2:00 - 2:30):**
Show creating a new service from a template — from clicking "Create" to having a running service in 3 minutes.

**The Mistake Most Teams Make (2:30 - 3:00)**

> "The #1 mistake: launching Backstage with an empty catalog. If developers open it and see nothing, they never come back. Populate the catalog FIRST — import all existing services, add ownership data, link to CI/CD pipelines. Make it useful on day one."

---

### TOOL 2: GitOps Controller — ArgoCD (3:00 - 5:00)

**What It Does (3:00 - 3:30)**

> "ArgoCD watches your Git repository and keeps your Kubernetes cluster in sync with what's in Git. Push a change to your deployment manifest? ArgoCD automatically applies it. No kubectl, no scripts, no 'I deployed from my laptop.'"

**Visual:** ArgoCD UI showing application tree, sync status, deployment history.

**Why It Matters (3:30 - 4:00)**

> "GitOps gives you three things for free: audit trail (every change is a Git commit), rollback (git revert), and drift detection (ArgoCD tells you when the cluster doesn't match Git)."

**Key Concepts:**
- **Application:** A mapping from a Git repo/path to a Kubernetes namespace
- **Sync:** Making the cluster match Git
- **Drift Detection:** Alerting when someone changes the cluster directly
- **App of Apps:** Bootstrapping pattern — one ArgoCD app manages all other apps

**Demo (4:00 - 4:30):**
Show a Git push → ArgoCD detects change → automatic sync → new version deployed.

**The Mistake Most Teams Make (4:30 - 5:00)**

> "The #1 mistake: not enabling automated sync with pruning. Without `automated.prune: true`, ArgoCD won't delete resources you removed from Git. You end up with orphaned resources that cost money and cause confusion."

```yaml
# Always enable these
spec:
  syncPolicy:
    automated:
      prune: true       # Delete resources removed from Git
      selfHeal: true    # Fix manual changes automatically
```

---

### TOOL 3: Infrastructure-as-Code — Terraform + Crossplane (5:00 - 7:00)

**What It Does (5:00 - 5:30)**

> "Terraform defines your cloud infrastructure as code. Crossplane takes it further — it lets Kubernetes manage your cloud resources. Together, they give platform engineers a complete infrastructure provisioning story."

**Visual:** Terraform plan output → apply → cloud resources created. Then Crossplane CRD creating an RDS database from a Kubernetes manifest.

**Why Both? (5:30 - 6:00)**

> "Terraform is for platform engineers — managing the base infrastructure: VPCs, clusters, DNS, IAM. Crossplane is for developer self-service — letting developers request databases, caches, and queues through Kubernetes manifests without needing cloud console access."

```
TERRAFORM (platform team)        CROSSPLANE (developer self-service)
─────────────────────────        ──────────────────────────────────
VPC, subnets, security groups    Database for my service
Kubernetes cluster               Redis cache for my service
DNS zones, certificates          S3 bucket for my service
IAM roles, policies              
                                 Developers apply a YAML manifest.
Platform team runs terraform.    Crossplane provisions the cloud
                                 resource automatically.
```

**Demo (6:00 - 6:30):**

Developer creates a `PostgreSQLInstance` custom resource in their namespace → Crossplane provisions an actual RDS instance in AWS → connection string injected into the pod automatically.

```yaml
apiVersion: database.example.org/v1
kind: PostgreSQLInstance
metadata:
  name: my-service-db
spec:
  size: small
  version: "16"
```

**The Mistake Most Teams Make (6:30 - 7:00)**

> "The #1 mistake with Terraform: not using remote state with locking. Without it, two people running terraform apply simultaneously will corrupt your infrastructure. Always use S3 + DynamoDB (AWS) or Azure Storage with locking."

---

### TOOL 4: Observability Platform — Grafana Stack (7:00 - 8:30)

**What It Does (7:00 - 7:30)**

> "The Grafana stack — Grafana for dashboards, Prometheus for metrics, Loki for logs, Tempo for traces — gives platform engineers visibility into everything. Not just application health, but platform health."

**Visual:** Grafana dashboard with golden signals (request rate, error rate, latency, saturation) for the platform itself.

**Platform-Specific Metrics (7:30 - 8:00)**

> "Platform engineers don't just monitor applications. They monitor the platform:"

- **Developer experience metrics:** Time from PR merge to production. Deployment frequency per team.
- **Platform reliability:** API gateway error rate. Certificate expiry countdown. Cluster utilization.
- **Self-service metrics:** How many resources provisioned per week. Failed provisioning requests.
- **Cost metrics:** Spend per team. Idle resource detection. Reserved capacity utilization.

**Demo (8:00 - 8:15):**
Show a "Platform Health" dashboard with: deployment pipeline success rate, mean time from merge to production, cluster resource utilization, and cost-per-team breakdown.

**The Mistake Most Teams Make (8:15 - 8:30)**

> "The #1 mistake: monitoring infrastructure but not developer experience. If your deployments take 45 minutes and you're not tracking that, you're missing the metric that matters most to your users — the developers."

---

### TOOL 5: Cost Management — Kubecost / OpenCost (8:30 - 9:30)

**What It Does (8:30 - 9:00)**

> "Kubecost and OpenCost allocate Kubernetes costs to teams, namespaces, and individual services. Without it, your cloud bill is a black box — you know the total, but not who's spending what."

**Visual:** Kubecost dashboard showing cost breakdown by namespace, team, and efficiency score.

**Why It Matters (9:00 - 9:15)**

> "I've seen Kubecost save teams 30-50% on their cloud bill within the first month. Not through magic — just by showing teams that their dev environment is running 24/7, their staging environment has 4x the resources of production, and nobody turned off the load test cluster from last quarter."

**The Mistake Most Teams Make (9:15 - 9:30)**

> "The #1 mistake: installing Kubecost but not sharing the dashboards with development teams. Cost visibility only works when the people making resource decisions can see the cost impact. Give every team their own cost dashboard."

---

### OUTRO (9:30 - 10:00)

**Summary (9:30 - 9:45)**

> "Five tools, five capabilities: Backstage for the developer portal. ArgoCD for deployment. Terraform plus Crossplane for infrastructure. Grafana for observability. And Kubecost for cost management. Together, they form the core of a modern internal developer platform."

**CTA (9:45 - 10:00)**

> "If you're building a platform team, start with these five. Get them right before adding anything else. Subscribe for a deep-dive into each tool. Next week: setting up Backstage from scratch."

**End Screen:** Two suggested videos.

---

## Production Notes

- **B-Roll:** Heavy screen recording of each tool's UI. Real dashboards, real data (anonymized).
- **Graphics:** Tool comparison tables, architecture diagrams showing how the tools connect
- **Music:** Professional, confident — this is for senior engineers making tool decisions
- **Pacing:** Each tool gets exactly 2 minutes. Fast but thorough.
- **SEO Tags:** platform engineering, internal developer platform, Backstage, ArgoCD, Terraform, Crossplane, Kubecost, GitOps, DevOps tools, developer experience, cloud cost
- **Sponsor fit:** Any of these tools would be a natural sponsor. Backstage and ArgoCD are open source, but commercial offerings exist.

*Script by the TechAI Explained Team.*
