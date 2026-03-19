---
title: "Lesson 5: Production Readiness — Health Checks, Resource Limits, and PDBs"
description: "The final checklist before deploying to production — readiness probes, liveness probes, resource requests and limits, Pod Disruption Budgets, and graceful shutdown."
date: 2026-03-04
tags: ["Kubernetes Course"]
readTime: "15 min read"
---

Your app works on Kubernetes. But is it production-ready? This lesson covers the five configurations that separate "it runs" from "it survives real traffic, node failures, and cluster upgrades without dropping requests."

## Health Checks: Probes

Kubernetes uses probes to know whether your Pod is alive and whether it should receive traffic.

### Readiness Probe: "Can this Pod handle requests?"

If the readiness probe fails, the Pod is removed from the Service's endpoints. Traffic stops flowing to it, but the Pod keeps running.

{% raw %}
```yaml
spec:
  containers:
    - name: api
      readinessProbe:
        httpGet:
          path: /health/ready
          port: 8080
        initialDelaySeconds: 5     # Wait 5s before first check
        periodSeconds: 10          # Check every 10s
        failureThreshold: 3        # 3 failures = not ready
        successThreshold: 1        # 1 success = ready again
```
{% endraw %}

**Use for:** checking that your app is fully initialized — database connections established, caches warmed, configuration loaded.

### Liveness Probe: "Is this Pod alive?"

If the liveness probe fails, Kubernetes **kills and restarts** the Pod.

{% raw %}
```yaml
spec:
  containers:
    - name: api
      livenessProbe:
        httpGet:
          path: /health/live
          port: 8080
        initialDelaySeconds: 15    # Give app time to start
        periodSeconds: 20          # Check every 20s
        failureThreshold: 3        # 3 failures = restart Pod
        timeoutSeconds: 5          # Max time per check
```
{% endraw %}

**Use for:** detecting deadlocks, infinite loops, or corrupted state that only a restart can fix.

### Startup Probe: "Has this Pod finished starting?"

For slow-starting apps, the startup probe prevents liveness kills during initialization.

{% raw %}
```yaml
spec:
  containers:
    - name: api
      startupProbe:
        httpGet:
          path: /health/live
          port: 8080
        initialDelaySeconds: 0
        periodSeconds: 5
        failureThreshold: 30      # 30 × 5s = 150s max startup time
```
{% endraw %}

While the startup probe is checking, liveness and readiness probes are disabled. Once the startup probe succeeds, they activate.

<div class="diagram-box">
PROBE DECISION FLOW

Pod starts
   │
   ▼
Startup Probe ──── Failing ──► Keep waiting (up to failureThreshold)
   │                              │
   │ Passes                       ▼ Exceeded
   ▼                           Kill and restart Pod
Liveness Probe ◄─── active
   │
   │ Passes              Fails
   ▼                       ▼
Readiness Probe        Kill and restart Pod
   │
   │ Passes              Fails
   ▼                       ▼
Receives traffic       Removed from Service
                       (no traffic, but Pod lives)
</div>

### Health Check Endpoints

```typescript
// Express health endpoints
app.get('/health/live', (req, res) => {
  // Liveness: is the process alive and not deadlocked?
  res.status(200).json({ status: 'alive' });
});

app.get('/health/ready', async (req, res) => {
  // Readiness: can we handle requests right now?
  try {
    await db.query('SELECT 1');           // DB connection works
    await redis.ping();                    // Cache is reachable
    res.status(200).json({ status: 'ready' });
  } catch (err) {
    res.status(503).json({ status: 'not ready', error: err.message });
  }
});
```

**Critical rule:** Liveness checks should be cheap and local. Never make a liveness probe depend on external services — if the database is down, you don't want Kubernetes restarting every Pod.

## Resource Requests and Limits

Requests and limits control how much CPU and memory your Pods use.

{% raw %}
```yaml
spec:
  containers:
    - name: api
      resources:
        requests:
          cpu: 250m          # 0.25 CPU cores (guaranteed minimum)
          memory: 256Mi      # 256 MB RAM (guaranteed minimum)
        limits:
          cpu: 1000m         # 1.0 CPU cores (hard ceiling)
          memory: 512Mi      # 512 MB RAM (OOM-killed if exceeded)
```
{% endraw %}

### How They Work

| Resource | Request | Limit |
|----------|---------|-------|
| **CPU** | Guaranteed minimum. Used for scheduling. | Hard cap. Pod is throttled, never killed. |
| **Memory** | Guaranteed minimum. Used for scheduling. | Hard cap. Pod is **OOM-killed** if exceeded. |

<div class="diagram-box">
RESOURCE REQUESTS vs LIMITS

CPU (soft limit):
├── Request (250m): guaranteed, used for scheduling
├── Burstable: Pod can use up to Limit when available
└── Limit (1000m): throttled if exceeded (NOT killed)

Memory (hard limit):
├── Request (256Mi): guaranteed, used for scheduling
└── Limit (512Mi): OOM-KILLED if exceeded ☠️
                    (no warning, no graceful shutdown)
</div>

### Choosing the Right Values

1. **Run your app under load** and observe actual CPU/memory usage
2. **Set requests** to the P50 (typical) usage
3. **Set limits** to 2-4× the request (room for spikes)
4. **Never set memory limit == request** — leaves no room for garbage collection spikes

**A starting template:**

{% raw %}
```yaml
# Web API (moderate traffic)
resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 500m
    memory: 512Mi

# Background worker (CPU-intensive)
resources:
  requests:
    cpu: 500m
    memory: 256Mi
  limits:
    cpu: 2000m
    memory: 1Gi

# Database (memory-intensive)
resources:
  requests:
    cpu: 250m
    memory: 1Gi
  limits:
    cpu: 2000m
    memory: 4Gi
```
{% endraw %}

### Why Requests Matter for Scheduling

Kubernetes uses **requests** (not limits) to decide which node to place a Pod on. If you don't set requests:
- The scheduler assumes the Pod needs 0 CPU and 0 memory
- It packs Pods onto already-full nodes
- Nodes become overcommitted → everything slows down or gets OOM-killed

**Always set requests.** They're not optional for production.

## Pod Disruption Budgets (PDBs)

During cluster upgrades, node maintenance, or autoscaling, Kubernetes needs to evict Pods. A **PodDisruptionBudget** limits how many Pods can be evicted simultaneously.

{% raw %}
```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: api-pdb
spec:
  minAvailable: 2              # At least 2 Pods must stay running
  selector:
    matchLabels:
      app: my-api
```
{% endraw %}

Alternative — use percentage:

{% raw %}
```yaml
spec:
  maxUnavailable: "25%"        # At most 25% of Pods can be down
  selector:
    matchLabels:
      app: my-api
```
{% endraw %}

### How PDBs Work

<div class="diagram-box">
SCENARIO: Cluster upgrade, node is draining

WITHOUT PDB:
  Node being drained has 3 of your 4 Pods
  All 3 evicted simultaneously → only 1 Pod handles all traffic
  → Requests drop, latency spikes

WITH PDB (minAvailable: 2):
  Kubernetes evicts 1 Pod → waits for replacement to start
  Then evicts next Pod → waits for replacement
  At least 2 Pods always handle traffic → no disruption
</div>

**Rule of thumb:** `minAvailable` should be at least `replicas - 1`. For 3 replicas, set `minAvailable: 2`.

## Graceful Shutdown

When Kubernetes kills a Pod, it sends SIGTERM and waits (default 30 seconds) before sending SIGKILL. Your app must handle SIGTERM properly.

```typescript
// Express graceful shutdown
const server = app.listen(8080);

process.on('SIGTERM', () => {
  console.log('SIGTERM received, shutting down gracefully...');

  // Stop accepting new connections
  server.close(() => {
    console.log('HTTP server closed');

    // Close database connections
    db.end().then(() => {
      console.log('Database connections closed');
      process.exit(0);
    });
  });

  // Force shutdown after 25s (before K8s sends SIGKILL at 30s)
  setTimeout(() => {
    console.error('Forced shutdown');
    process.exit(1);
  }, 25000);
});
```

### Graceful Shutdown Sequence

<div class="diagram-box">
KUBERNETES POD TERMINATION

1. Pod marked for termination
2. Pod removed from Service endpoints (no new traffic)
3. preStop hook runs (if configured)
4. SIGTERM sent to container
5. App handles SIGTERM:
   - Stops accepting new connections
   - Finishes in-flight requests
   - Closes database connections
   - Exits cleanly
6. If still running after terminationGracePeriodSeconds (default 30s):
   SIGKILL sent (forced kill, no cleanup)
</div>

For apps that need more than 30 seconds:

{% raw %}
```yaml
spec:
  terminationGracePeriodSeconds: 60   # Give 60s instead of 30s
  containers:
    - name: api
      lifecycle:
        preStop:
          exec:
            command: ["sh", "-c", "sleep 5"]  # Wait for endpoints to update
```
{% endraw %}

The `preStop` sleep gives the Service time to remove the Pod from its endpoints before the app starts rejecting connections.

## Production Readiness Checklist

{% raw %}
```yaml
# Complete production-ready Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-api
  namespace: production
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0          # Zero-downtime deploys
  selector:
    matchLabels:
      app: my-api
  template:
    metadata:
      labels:
        app: my-api
    spec:
      terminationGracePeriodSeconds: 45
      containers:
        - name: api
          image: my-registry/my-api:1.2.0
          ports:
            - containerPort: 8080

          # Resource management
          resources:
            requests:
              cpu: 250m
              memory: 256Mi
            limits:
              cpu: 1000m
              memory: 512Mi

          # Health checks
          startupProbe:
            httpGet:
              path: /health/live
              port: 8080
            periodSeconds: 5
            failureThreshold: 30

          livenessProbe:
            httpGet:
              path: /health/live
              port: 8080
            periodSeconds: 15
            failureThreshold: 3

          readinessProbe:
            httpGet:
              path: /health/ready
              port: 8080
            periodSeconds: 10
            failureThreshold: 3

          # Graceful shutdown
          lifecycle:
            preStop:
              exec:
                command: ["sh", "-c", "sleep 5"]

          # Environment from ConfigMap and Secret
          envFrom:
            - configMapRef:
                name: api-config
            - secretRef:
                name: api-secrets
---
# Pod Disruption Budget
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: api-pdb
  namespace: production
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: my-api
```
{% endraw %}

## Key Takeaways

1. **Readiness probes** control traffic routing — use for dependency checks
2. **Liveness probes** trigger restarts — keep them simple and local
3. **Startup probes** protect slow-starting apps from premature kills
4. **Resource requests** are for scheduling — always set them
5. **Resource limits** are hard caps — memory exceeding limits means OOM-kill
6. **PDBs** prevent mass evictions during maintenance
7. **Graceful shutdown** means handling SIGTERM and draining connections

**Congratulations!** You've completed the Kubernetes for Application Developers course. You now know the five resource categories that matter most: Pods/Deployments/Services, ConfigMaps/Secrets, Persistent Storage, Networking, and Production Readiness.

← [Lesson 4: Networking](/courses/kubernetes-for-app-devs/04-networking-ingress/) | [Back to Course Index](/courses/kubernetes-for-app-devs/)

*Part of the Kubernetes for Application Developers course by the TechAI Explained Team.*
