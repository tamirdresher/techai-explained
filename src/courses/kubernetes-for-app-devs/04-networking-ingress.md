---
title: "Lesson 4: Networking — Ingress, NetworkPolicies, and Service Mesh Basics"
description: "How traffic reaches your Kubernetes applications — Ingress controllers for external access, NetworkPolicies for security, and an introduction to service mesh concepts."
date: 2026-03-05
tags: ["Kubernetes Course"]
readTime: "15 min read"
---

In Lesson 1, Services gave your Pods a stable internal address. But how does traffic from the internet reach those Services? That's where **Ingress** comes in. And how do you control which services can talk to each other? That's **NetworkPolicies**. This lesson covers both, plus a primer on service meshes.

## Ingress: Exposing Your App to the Internet

An Ingress routes external HTTP/HTTPS traffic to internal Services based on hostnames and paths.

<div class="diagram-box">
INTERNET TRAFFIC FLOW

Internet
   │
   ▼
┌──────────────────┐
│  Load Balancer   │  (cloud provider)
│  (public IP)     │
└────────┬─────────┘
         │
┌────────┴─────────┐
│  Ingress         │  (NGINX, Traefik, etc.)
│  Controller      │
│                  │
│  Rules:          │
│  api.example.com │──► api-service:80
│  app.example.com │──► web-service:80
│  *.example.com/  │
│    docs/*        │──► docs-service:80
└──────────────────┘
</div>

### Setting Up Ingress

**Step 1:** Install an Ingress Controller (you need one in the cluster):

```bash
# NGINX Ingress Controller (most common)
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm install ingress-nginx ingress-nginx/ingress-nginx
```

**Step 2:** Create Ingress rules:

{% raw %}
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: app-ingress
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - api.example.com
        - app.example.com
      secretName: app-tls-cert        # TLS certificate
  rules:
    - host: api.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: api-service
                port:
                  number: 80

    - host: app.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: web-service
                port:
                  number: 80
```
{% endraw %}

### Path-Based Routing

Route different URL paths to different services:

{% raw %}
```yaml
spec:
  rules:
    - host: example.com
      http:
        paths:
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: api-service
                port:
                  number: 80
          - path: /docs
            pathType: Prefix
            backend:
              service:
                name: docs-service
                port:
                  number: 80
          - path: /
            pathType: Prefix
            backend:
              service:
                name: web-frontend
                port:
                  number: 80
```
{% endraw %}

### TLS with cert-manager

Automate HTTPS certificates with Let's Encrypt:

```bash
# Install cert-manager
helm repo add jetstack https://charts.jetstack.io
helm install cert-manager jetstack/cert-manager --set installCRDs=true
```

{% raw %}
```yaml
# ClusterIssuer for Let's Encrypt
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: team@example.com
    privateKeySecretRef:
      name: letsencrypt-prod-key
    solvers:
      - http01:
          ingress:
            class: nginx
```
{% endraw %}

With the `cert-manager.io/cluster-issuer` annotation on your Ingress, cert-manager automatically provisions and renews TLS certificates.

## NetworkPolicies: Internal Firewalls

By default, every Pod can talk to every other Pod in the cluster. **NetworkPolicies** restrict this.

<div class="diagram-box">
WITHOUT NetworkPolicy          WITH NetworkPolicy
(default)                      (restricted)

┌─────┐    ┌─────┐            ┌─────┐    ┌─────┐
│ API │◄──►│ DB  │            │ API │───►│ DB  │  ✅ allowed
└──┬──┘    └─────┘            └─────┘    └─────┘
   │                             ▲
┌──┴──┐    ┌─────┐            ┌──┴──┐    ┌─────┐
│ Web │◄──►│ DB  │            │ Web │───►│ DB  │  ❌ denied!
└─────┘    └─────┘            └─────┘    └─────┘

Everything talks to             Only API can reach DB
everything                     
</div>

### Deny All by Default

Start with a deny-all policy, then allow specific traffic:

{% raw %}
```yaml
# Deny all ingress to the database namespace
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-all
  namespace: database
spec:
  podSelector: {}           # Apply to ALL pods in namespace
  policyTypes:
    - Ingress
  ingress: []               # Empty = deny all incoming
```
{% endraw %}

### Allow Specific Traffic

{% raw %}
```yaml
# Only allow API pods to connect to PostgreSQL
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-api-to-postgres
  namespace: database
spec:
  podSelector:
    matchLabels:
      app: postgres            # Apply to postgres pods
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: production
          podSelector:
            matchLabels:
              app: api         # Only from api pods
      ports:
        - protocol: TCP
          port: 5432           # Only PostgreSQL port
```
{% endraw %}

### Common NetworkPolicy Patterns

**Allow same-namespace traffic only:**

{% raw %}
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-same-namespace
spec:
  podSelector: {}
  policyTypes:
    - Ingress
  ingress:
    - from:
        - podSelector: {}      # Any pod in the SAME namespace
```
{% endraw %}

**Allow traffic from Ingress controller:**

{% raw %}
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-ingress-controller
spec:
  podSelector:
    matchLabels:
      app: web-frontend
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              app.kubernetes.io/name: ingress-nginx
      ports:
        - protocol: TCP
          port: 8080
```
{% endraw %}

## Service Mesh Basics

A service mesh adds observability, security, and traffic control to service-to-service communication — without changing application code.

<div class="diagram-box">
WITHOUT SERVICE MESH             WITH SERVICE MESH

┌─────────┐    ┌─────────┐     ┌─────────────────┐    ┌─────────────────┐
│  API    │───►│ Payment │     │  API  │ Sidecar │───►│Payment│ Sidecar │
│  (HTTP) │    │ (HTTP)  │     │       │  Proxy  │    │       │  Proxy  │
└─────────┘    └─────────┘     └───────┴─────────┘    └───────┴─────────┘
                                         │                      │
Plain HTTP                               └──── mTLS ────────────┘
No encryption                            Encrypted, authenticated
No retries                               Auto-retries, circuit breaking
No metrics                               Latency, error metrics per route
</div>

### What a Service Mesh Adds

| Feature | Without Mesh | With Mesh |
|---------|-------------|-----------|
| Encryption | Manual TLS setup | Automatic mTLS between all services |
| Retries | Code in each service | Configured at mesh level |
| Observability | Manual instrumentation | Automatic latency/error metrics |
| Traffic splitting | Not possible | Route 5% to canary, 95% to stable |
| Circuit breaking | Library-specific | Configured per route |

### Popular Service Meshes

- **Istio** — most features, most complex
- **Linkerd** — lightweight, simple, fast
- **Cilium** — eBPF-based, no sidecars needed

### When You Need a Service Mesh

**YES:** 20+ services, strict mTLS requirements, canary deployments, detailed per-route observability.

**NO:** Fewer than 10 services, simple networking needs, team is new to Kubernetes. Start with NetworkPolicies and Ingress — add a mesh only when complexity demands it.

## Debugging Networking Issues

```bash
# Check Ingress status and address
kubectl get ingress
kubectl describe ingress app-ingress

# Check if Service has endpoints (Pods)
kubectl get endpoints api-service

# DNS resolution test from inside the cluster
kubectl run tmp --rm -it --image=busybox -- nslookup api-service

# Test connectivity between pods
kubectl run tmp --rm -it --image=curlimages/curl -- \
  curl -v http://api-service:80/health

# Check NetworkPolicy is applied
kubectl get networkpolicy -A
kubectl describe networkpolicy allow-api-to-postgres
```

## Key Takeaways

1. **Ingress** routes external HTTP/HTTPS traffic to Services by hostname and path
2. **cert-manager** automates TLS certificates with Let's Encrypt
3. **NetworkPolicies** are your internal firewall — deny by default, allow explicitly
4. **Service meshes** add mTLS, retries, and observability — but only when you need them
5. **Debug with endpoints** — if `kubectl get endpoints` shows no IPs, the Service can't find any Pods

← [Lesson 3: Persistent Storage](/courses/kubernetes-for-app-devs/03-persistent-storage/) | [Lesson 5: Production Readiness →](/courses/kubernetes-for-app-devs/05-production-readiness/)

*Part of the Kubernetes for Application Developers course by the TechAI Explained Team.*
