---
title: "Lesson 3: Persistent Storage — PVs, PVCs, and StorageClasses"
description: "How Kubernetes handles persistent data — PersistentVolumes, PersistentVolumeClaims, StorageClasses, and the patterns for running stateful workloads."
date: 2026-03-06
tags: ["Kubernetes Course"]
readTime: "15 min read"
---

Containers are ephemeral — when a Pod dies, its filesystem is gone. For databases, file uploads, and caches that survive restarts, you need **persistent storage**. Kubernetes abstracts storage through three resources: PersistentVolumes (PVs), PersistentVolumeClaims (PVCs), and StorageClasses.

## The Storage Model

<div class="diagram-box">
KUBERNETES STORAGE ABSTRACTION

┌──────────────────────────────────────────────────┐
│  YOUR POD                                        │
│  ┌────────────────────────────────┐              │
│  │  Container                    │              │
│  │  /data/uploads  ◄── mounted   │              │
│  └──────────────────┬────────────┘              │
│                     │ volumeMount               │
│  ┌──────────────────┴────────────┐              │
│  │  PersistentVolumeClaim (PVC)  │ ◄── Request  │
│  │  "I need 10Gi of SSD storage" │              │
│  └──────────────────┬────────────┘              │
└─────────────────────┼────────────────────────────┘
                      │ binds to
┌─────────────────────┴────────────────────────────┐
│  PersistentVolume (PV)                           │
│  "Here is 10Gi of SSD storage on Azure Disk"    │
│                                                  │
│  Backed by: Azure Disk / AWS EBS / GCE PD /     │
│             NFS / local SSD / ...                │
└──────────────────────────────────────────────────┘
</div>

Think of it like renting:
- **PVC** = "I need a 2-bedroom apartment" (the request)
- **PV** = "Here's apartment 4B on the 3rd floor" (the actual resource)
- **StorageClass** = "Luxury apartments vs economy apartments" (the tier)

## PersistentVolumeClaims (PVCs)

As a developer, you almost always work with PVCs. They request storage without knowing where it comes from.

{% raw %}
```yaml
# pvc.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: app-uploads
spec:
  accessModes:
    - ReadWriteOnce        # One node can mount read-write
  storageClassName: managed-premium   # SSD storage
  resources:
    requests:
      storage: 10Gi        # 10 gigabytes
```
{% endraw %}

### Access Modes

| Mode | Abbreviation | Meaning |
|------|-------------|---------|
| `ReadWriteOnce` | RWO | One node reads/writes — most common for databases |
| `ReadOnlyMany` | ROX | Many nodes read — shared config, static assets |
| `ReadWriteMany` | RWX | Many nodes read/write — shared file storage (NFS, Azure Files) |

### Using a PVC in a Pod

{% raw %}
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: file-server
spec:
  replicas: 1
  selector:
    matchLabels:
      app: file-server
  template:
    metadata:
      labels:
        app: file-server
    spec:
      containers:
        - name: server
          image: my-registry/file-server:1.0.0
          ports:
            - containerPort: 8080
          volumeMounts:
            - name: uploads
              mountPath: /data/uploads    # Where files appear in the container
      volumes:
        - name: uploads
          persistentVolumeClaim:
            claimName: app-uploads        # References the PVC
```
{% endraw %}

When the Pod starts, Kubernetes mounts the PVC at `/data/uploads`. Files written there survive Pod restarts, crashes, and redeployments.

## StorageClasses

StorageClasses define **what kind** of storage is available. Cloud providers come with defaults.

{% raw %}
```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast-ssd
provisioner: disk.csi.azure.com    # Azure Managed Disks
parameters:
  skuName: Premium_LRS             # Premium SSD
  kind: Managed
reclaimPolicy: Delete              # Delete disk when PVC is deleted
volumeBindingMode: WaitForFirstConsumer  # Don't provision until Pod is scheduled
allowVolumeExpansion: true         # Allow resizing
```
{% endraw %}

### Common StorageClasses by Provider

| Provider | Default Class | SSD Class | Shared Storage |
|----------|--------------|-----------|----------------|
| AKS | `default` (Standard HDD) | `managed-premium` | `azurefile-premium` |
| EKS | `gp2` | `gp3` | `efs-sc` |
| GKE | `standard` | `premium-rwo` | `standard-rwx` |

### Reclaim Policies

| Policy | Behavior | Use Case |
|--------|----------|----------|
| `Delete` | PV and disk deleted when PVC is deleted | Dev/test environments |
| `Retain` | PV and disk preserved when PVC is deleted | Production databases |

**Always use `Retain` for production databases.** If someone accidentally deletes the PVC, you don't want the data gone too.

## Dynamic vs Static Provisioning

### Dynamic Provisioning (Recommended)

You create a PVC, Kubernetes automatically creates the PV and underlying disk:

```
Developer creates PVC → StorageClass provisions PV → Cloud creates disk
```

This is the default behavior. You almost never create PVs manually.

### Static Provisioning

For pre-existing disks (migrated data, shared NFS), create the PV manually:

{% raw %}
```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: legacy-data
spec:
  capacity:
    storage: 100Gi
  accessModes:
    - ReadWriteOnce
  persistentVolumeReclaimPolicy: Retain
  storageClassName: ""           # Empty = no dynamic provisioning
  azureDisk:
    diskName: my-existing-disk
    diskURI: /subscriptions/.../my-existing-disk
    kind: Managed
```
{% endraw %}

## StatefulSets: Storage for Replicated Services

Deployments share one PVC across all replicas (problematic for databases). **StatefulSets** give each replica its own persistent storage.

{% raw %}
```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
spec:
  serviceName: postgres          # Required headless service name
  replicas: 3
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
        - name: postgres
          image: postgres:16
          ports:
            - containerPort: 5432
          volumeMounts:
            - name: pgdata
              mountPath: /var/lib/postgresql/data
          env:
            - name: POSTGRES_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: postgres-secret
                  key: password
  volumeClaimTemplates:          # Each replica gets its OWN PVC
    - metadata:
        name: pgdata
      spec:
        accessModes: ["ReadWriteOnce"]
        storageClassName: managed-premium
        resources:
          requests:
            storage: 50Gi
```
{% endraw %}

<div class="diagram-box">
STATEFULSET: postgres (replicas: 3)

  postgres-0 ──► pgdata-postgres-0 (50Gi PVC) ──► Azure Disk 1
  postgres-1 ──► pgdata-postgres-1 (50Gi PVC) ──► Azure Disk 2
  postgres-2 ──► pgdata-postgres-2 (50Gi PVC) ──► Azure Disk 3

Each replica has:
  - Stable hostname: postgres-0, postgres-1, postgres-2
  - Stable DNS:      postgres-0.postgres.default.svc.cluster.local
  - Its OWN persistent disk
  - Ordered startup (0 → 1 → 2)
  - Ordered shutdown (2 → 1 → 0)
</div>

StatefulSets also need a **headless Service** for DNS:

{% raw %}
```yaml
apiVersion: v1
kind: Service
metadata:
  name: postgres
spec:
  selector:
    app: postgres
  clusterIP: None               # Headless — no load balancing
  ports:
    - port: 5432
```
{% endraw %}

## Expanding Volumes

If your StorageClass has `allowVolumeExpansion: true`, you can grow PVCs:

```bash
kubectl patch pvc app-uploads -p '{"spec":{"resources":{"requests":{"storage":"20Gi"}}}}'
```

The underlying disk grows automatically. **You cannot shrink volumes** — only expand.

## Common Mistakes

1. **Using `ReadWriteOnce` with multiple replicas** — only one node can mount RWO. Use RWX (Azure Files, EFS) for shared access.
2. **`Delete` reclaim policy on production data** — use `Retain` to prevent accidental data loss.
3. **Not setting `volumeBindingMode: WaitForFirstConsumer`** — without this, the disk may be provisioned in a zone where no node exists.
4. **Storing state in container filesystem** — any data not on a PVC is lost when the Pod restarts.
5. **Using Deployments for databases** — use StatefulSets for stable network IDs and per-replica storage.

## Key Takeaways

1. **PVCs** request storage — this is what developers interact with
2. **PVs** are the actual storage — usually auto-created by the StorageClass
3. **StorageClasses** define storage tiers — SSD vs HDD, Delete vs Retain
4. **StatefulSets** give each replica its own persistent storage
5. **Dynamic provisioning** is the default — you rarely create PVs manually
6. Always use **`Retain`** reclaim policy for production data

← [Lesson 2: ConfigMaps and Secrets](/courses/kubernetes-for-app-devs/02-configmaps-secrets-environment/) | [Lesson 4: Networking →](/courses/kubernetes-for-app-devs/04-networking-ingress/)

*Part of the Kubernetes for Application Developers course by the TechAI Explained Team.*
