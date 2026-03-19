---
title: "Lesson 2: ConfigMaps, Secrets, and Environment Management"
description: "How to configure applications in Kubernetes — environment variables, config files, secrets management, and the patterns that keep configuration maintainable across environments."
date: 2026-03-07
tags: ["Kubernetes Course"]
readTime: "15 min read"
---

Your application needs configuration — database URLs, API keys, feature flags, log levels. In Kubernetes, you use **ConfigMaps** for non-sensitive config and **Secrets** for sensitive data. They decouple configuration from your container image so the same image runs in dev, staging, and production with different settings.

## ConfigMaps: Non-Sensitive Configuration

A ConfigMap stores key-value pairs or entire configuration files.

### Creating ConfigMaps

{% raw %}
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: api-config
data:
  LOG_LEVEL: "info"
  MAX_CONNECTIONS: "100"
  FEATURE_NEW_CHECKOUT: "true"
  CORS_ORIGINS: "https://app.example.com,https://admin.example.com"
```

**From a configuration file:**

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: nginx-config
data:
  nginx.conf: |
    server {
      listen 80;
      location / {
        proxy_pass http://my-api:8080;
        proxy_set_header Host $host;
      }
    }
```
{% endraw %}

### Using ConfigMaps as Environment Variables

{% raw %}
```yaml
spec:
  containers:
    - name: api
      image: my-registry/my-api:1.0.0

      # Option 1: Individual keys
      env:
        - name: LOG_LEVEL
          valueFrom:
            configMapKeyRef:
              name: api-config
              key: LOG_LEVEL

      # Option 2: All keys at once
      envFrom:
        - configMapRef:
            name: api-config
```
{% endraw %}

### Using ConfigMaps as Files (Volume Mount)

{% raw %}
```yaml
spec:
  containers:
    - name: api
      volumeMounts:
        - name: config-volume
          mountPath: /app/config
          readOnly: true
  volumes:
    - name: config-volume
      configMap:
        name: api-config
```
{% endraw %}

<div class="diagram-box">
CONFIGMAP USAGE PATTERNS

┌──────────────────────────────────────┐
│            CONTAINER                 │
│                                      │
│  Environment Variables:              │
│    LOG_LEVEL=info      ◄── ConfigMap │
│    MAX_CONNECTIONS=100 ◄── (env)     │
│                                      │
│  Files:                              │
│    /app/config/app.yaml ◄── ConfigMap│
│    /etc/nginx/nginx.conf◄── (volume) │
└──────────────────────────────────────┘
</div>

## Secrets: Sensitive Configuration

Secrets store passwords, API keys, and certificates. They work like ConfigMaps but Kubernetes treats them with more care.

### Creating Secrets

{% raw %}
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: api-secrets
type: Opaque
stringData:
  DATABASE_URL: "postgresql://user:password@postgres:5432/mydb"
  JWT_SECRET: "super-secret-key-change-in-production"
  STRIPE_API_KEY: "sk_live_abc123def456"
```

> Use `stringData` (plain text, auto-encoded) instead of `data` (requires manual base64 encoding).

### Using Secrets in Pods

```yaml
spec:
  containers:
    - name: api
      env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: api-secrets
              key: DATABASE_URL
      envFrom:
        - secretRef:
            name: api-secrets
```
{% endraw %}

## Environment-Specific Configuration

The key pattern: **same image, different config per environment**.

<div class="diagram-box">
SAME IMAGE, DIFFERENT CONFIG

Image: my-api:1.0.0 (identical everywhere)
           │
    ┌──────┼──────┐
    ▼      ▼      ▼
   DEV   STAGING  PROD
   ───   ───────  ────
   LOG=  LOG=     LOG=
   debug info     warn
   DB=   DB=      DB=
   dev   staging  prod
</div>

### Using Kustomize for Overlays

```
k8s/
├── base/
│   ├── deployment.yaml
│   ├── service.yaml
│   └── kustomization.yaml
└── overlays/
    ├── dev/
    │   ├── configmap.yaml
    │   └── kustomization.yaml
    └── production/
        ├── configmap.yaml
        └── kustomization.yaml
```

Deploy to production:

```bash
kubectl apply -k k8s/overlays/production/
```

## Secrets Security Best Practices

### 1. Never Commit Secrets to Git

Use one of these instead:
- **Sealed Secrets** — encrypts secrets for safe Git storage
- **External Secrets Operator** — syncs from Azure Key Vault, AWS Secrets Manager, or Vault
- **SOPS** — encrypts specific YAML values

### 2. Use External Secrets Operator for Production

{% raw %}
```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: api-secrets
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: azure-keyvault
    kind: ClusterSecretStore
  target:
    name: api-secrets
  data:
    - secretKey: DATABASE_URL
      remoteRef:
        key: production-database-url
```
{% endraw %}

### 3. Enable Encryption at Rest

By default Kubernetes stores secrets base64-encoded (NOT encrypted) in etcd. Enable encryption in your cluster configuration.

## The Restart Problem

When you update a ConfigMap, Pods using env vars do **NOT** auto-restart:

```bash
# Force a rolling restart after config change
kubectl rollout restart deployment/my-api
```

Volume-mounted ConfigMaps update automatically (within ~60 seconds), but your app needs to watch the file for changes.

## Common Mistakes

1. **Hardcoding config in the image** — use ConfigMaps instead
2. **Using ConfigMaps for secrets** — ConfigMaps have no access controls
3. **Not setting `readOnly: true`** on secret volume mounts
4. **Giant ConfigMaps** — one ConfigMap per concern
5. **Forgetting to restart** after ConfigMap env var changes

## Key Takeaways

1. **ConfigMaps** for non-sensitive config (log levels, feature flags)
2. **Secrets** for sensitive config (passwords, API keys, certificates)
3. **Environment variables** for simple key-value pairs
4. **Volume mounts** for configuration files
5. **Kustomize** for environment-specific overlays
6. **External Secrets Operator** for production secret management
7. **Never commit secrets to Git**

← [Lesson 1: Pods, Deployments, Services](/courses/kubernetes-for-app-devs/01-pods-deployments-services/) | Lesson 3: Health Checks (coming soon) →

*Part of the Kubernetes for Application Developers course by the TechAI Explained Team.*
