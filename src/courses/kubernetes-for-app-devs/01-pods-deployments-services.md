---
title: "Lesson 1: Pods, Deployments, Services — The Core Three"
description: "The three Kubernetes resources every developer must understand — how Pods run your containers, Deployments manage replicas, and Services route traffic."
date: 2026-03-08
tags: ["Kubernetes Course"]
readTime: "15 min read"
---

Every Kubernetes application uses three core resources: **Pods**, **Deployments**, and **Services**. A Pod runs your container. A Deployment manages your Pods. A Service routes traffic to your Pods. Understand these three, and you understand 80% of what matters for deploying applications.

## Pods: Where Your Code Runs

A Pod is the smallest deployable unit in Kubernetes. It wraps one or more containers that share the same network and storage.

### Your First Pod

{% raw %}
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: my-api
  labels:
    app: my-api
spec:
  containers:
    - name: api
      image: my-registry/my-api:1.0.0
      ports:
        - containerPort: 8080
```
{% endraw %}

Apply it:

```bash
kubectl apply -f pod.yaml
kubectl get pods
kubectl logs my-api
kubectl describe pod my-api
```

### What's Inside a Pod

<div class="diagram-box">
┌────────────────────────────────────────────────┐
│                     POD                        │
│                                                │
│  ┌──────────────────┐  ┌───────────────────┐   │
│  │  Container: api  │  │ Container: sidecar│   │
│  │                  │  │ (optional)        │   │
│  │  Your app code   │  │ Logging, proxy,   │   │
│  │  Port 8080       │  │ service mesh      │   │
│  └──────────────────┘  └───────────────────┘   │
│                                                │
│  Shared: Network (localhost), Storage (volumes)│
│  Unique: Pod IP (cluster-internal)             │
└────────────────────────────────────────────────┘
</div>

Key facts about Pods:
- Each Pod gets its own **IP address** (internal to the cluster)
- Containers in the same Pod share `localhost`
- Pods are **ephemeral** — Kubernetes can kill and replace them at any time
- You almost **never create Pods directly** — you use Deployments instead

## Deployments: Managing Your Pods

A Deployment tells Kubernetes: "I want N replicas of this Pod running at all times." If a Pod crashes, the Deployment creates a new one. If you update the image, the Deployment rolls out the new version gradually.

### Your First Deployment

{% raw %}
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: my-api
  template:
    metadata:
      labels:
        app: my-api
    spec:
      containers:
        - name: api
          image: my-registry/my-api:1.0.0
          ports:
            - containerPort: 8080
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 256Mi
```
{% endraw %}

### How Deployments Work

<div class="diagram-box">
DEPLOYMENT: my-api (replicas: 3)
│
├── Pod: my-api-7d4f8b6c5-abc12   [Running] ✅
├── Pod: my-api-7d4f8b6c5-def34   [Running] ✅
└── Pod: my-api-7d4f8b6c5-ghi56   [Running] ✅

What happens when a Pod crashes:
  Pod: my-api-7d4f8b6c5-abc12   [CrashLoopBackOff] ❌
  → Deployment creates: my-api-7d4f8b6c5-jkl78 ✅
  → Back to 3/3 ✅
</div>

### Rolling Updates

When you change the image, Pods update gradually with zero downtime:

```bash
kubectl set image deployment/my-api api=my-registry/my-api:2.0.0
kubectl rollout status deployment/my-api
kubectl rollout undo deployment/my-api    # Roll back if needed
```

<div class="diagram-box">
ROLLING UPDATE: v1 → v2

Step 1:  v1 ✅  v1 ✅  v1 ✅  v2 🔄 (starting)
Step 2:  v1 ✅  v1 ✅  v2 ✅  (v1 terminating)
Step 3:  v1 ✅  v2 ✅  v2 🔄 (starting)
Step 4:  v2 ✅  v2 ✅  v2 ✅  — Zero downtime!
</div>

## Services: Routing Traffic to Your Pods

Pods have IP addresses, but those IPs change every time a Pod is recreated. **Services** provide a stable network endpoint.

### Your First Service

{% raw %}
```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-api
spec:
  selector:
    app: my-api
  ports:
    - port: 80
      targetPort: 8080
  type: ClusterIP
```
{% endraw %}

### How Services Work

<div class="diagram-box">
SERVICE: my-api (ClusterIP: 10.96.45.12)
│
│  Stable DNS: my-api.default.svc.cluster.local
│
│  Request ──► Service ──┬──► Pod A (10.244.1.5)
│                        ├──► Pod B (10.244.2.3)
│                        └──► Pod C (10.244.1.8)
│
│  Pod IPs change. Service IP stays the same.
│  Other services connect to: http://my-api:80
</div>

### Service Types

| Type | Access | Use Case |
|------|--------|----------|
| `ClusterIP` | Internal only | Service-to-service |
| `NodePort` | Via NodeIP:Port | Dev/testing |
| `LoadBalancer` | External LB | Production traffic |

### Service Discovery

Kubernetes has built-in DNS. Every Service gets a name:

```typescript
// Just use the service name in your code
const response = await fetch('http://my-api:80/api/orders');
```

## Putting It All Together

{% raw %}
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: my-api
  template:
    metadata:
      labels:
        app: my-api
    spec:
      containers:
        - name: api
          image: my-registry/my-api:1.2.0
          ports:
            - containerPort: 8080
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 256Mi
---
apiVersion: v1
kind: Service
metadata:
  name: my-api
spec:
  selector:
    app: my-api
  ports:
    - port: 80
      targetPort: 8080
  type: ClusterIP
```
{% endraw %}

## Common Debugging Commands

```bash
kubectl describe pod <pod-name>       # Events and status
kubectl logs <pod-name>               # App logs
kubectl logs <pod-name> --previous    # Crashed container logs
kubectl rollout status deployment/X   # Deployment progress
kubectl get endpoints my-api          # Service target Pods
kubectl exec -it <pod-name> -- sh     # Shell into a Pod
```

## Key Takeaways

1. **Pods** run containers but are ephemeral — never create them directly
2. **Deployments** manage Pods with self-healing, scaling, and rolling updates
3. **Services** provide stable networking — use service names, not Pod IPs
4. **Labels** connect everything — Deployments and Services find Pods by labels
5. Always set **resource requests/limits** for production

Next: [Lesson 2 — ConfigMaps, Secrets, and Environment Management →](/courses/kubernetes-for-app-devs/02-configmaps-secrets-environment/)

*Part of the Kubernetes for Application Developers course by the TechAI Explained Team.*
