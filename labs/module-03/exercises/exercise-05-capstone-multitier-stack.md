# Exercise 5 — Capstone: A Multi-Tier Self-Care Stack

> **Scenario:** Bring everything together. Stand up a small but realistic slice of
> the **Mobily self-care platform** in one namespace: a **stateless API tier**
> (Deployment) configured by a **ConfigMap** and a **Secret**, fronted by a
> **Service** for discovery, plus a **stateful CDR store** (StatefulSet with
> per-pod storage). Then exercise the operational muscles — scale, self-heal,
> roll out, and prove persistence — on the whole stack.

| | |
|---|---|
| **Practice** | Deployment + ConfigMap + Secret + Service + StatefulSet + PVC, combined; scaling, rollout, persistence |
| **Maps to** | Guide §3–11 · Demos 1–5 |
| **Difficulty** | ⭐⭐⭐ Advanced · ~45 min · single-node OK (multi-node enriches DaemonSet stretch) |

---

## The target architecture

```
self-care namespace
├── ConfigMap  subscriber-config   (PLAN_TIER, DATA_QUOTA_GB, ROAMING)
├── Secret     subscriber-secret   (DB_USER, DB_PASSWORD)
├── Deployment subscriber-api  x3  ── consumes ConfigMap + Secret
│      └── Service subscriber-api (ClusterIP)  ── stable discovery name
└── StatefulSet cdr-store       x2  ── per-pod PVC (volumeClaimTemplates)
       └── headless Service cdr-store          ── per-pod DNS
```

## Tasks

1. Create (and switch to) a namespace **`self-care`**.
2. Create a ConfigMap **`subscriber-config`** (`PLAN_TIER=gold`, `DATA_QUOTA_GB=50`,
   `ROAMING=enabled`) and a Secret **`subscriber-secret`**
   (`DB_USER=mobily_app`, placeholder `DB_PASSWORD`).
3. Create a Deployment **`subscriber-api`** (3 replicas, `ubi9/httpd-24`) whose pods
   receive the ConfigMap via `envFrom` and `DB_USER` via `secretKeyRef`.
4. Expose `subscriber-api` as a **ClusterIP** Service (port 80 → 8080) and confirm
   it resolves by DNS from a client pod.
5. Create a **StatefulSet `cdr-store`** (2 replicas) with a headless Service and a
   `volumeClaimTemplates` PVC; confirm ordinal pods `cdr-store-0/-1` and one PVC
   each.
6. **Operate the stack:**
   a. Scale `subscriber-api` to 5, then back to 3.
   b. Delete a `subscriber-api` pod and confirm self-heal back to 3/3.
   c. Roll the API onto a new env value by editing the ConfigMap **and** restarting
      the rollout (`kubectl rollout restart`), confirming pods pick up the change.
7. **Prove persistence:** write a CDR into `cdr-store-0`'s volume, delete the pod,
   and confirm the StatefulSet recreates `cdr-store-0` with the **same data**.

> **Stretch (multi-node):** add a **DaemonSet** `node-probe` and confirm one pod
> lands per worker (control-plane stays empty due to its `NoSchedule` taint).

> **Hint (6c):** a ConfigMap change isn't picked up by *running* env-var pods
> automatically — `kubectl rollout restart deployment/subscriber-api` cycles them so
> they re-read it.

---

## Validation

```bash
# 3/4 — API up and discoverable
kubectl get deploy subscriber-api
kubectl get svc subscriber-api

# 5 — ordinal StatefulSet pods + one PVC each
kubectl get pods -l app=cdr-store
kubectl get pvc -l app=cdr-store

# 6b — self-heal keeps 3
kubectl get pods -l app=subscriber-api

# 7 — data survives pod deletion
kubectl exec cdr-store-0 -- cat /var/www/html/cdr.log
```

---

## Reflection

- Which tiers are **stateless** and which are **stateful**, and how does that drive
  your choice of Deployment vs StatefulSet?
- Why does a ConfigMap edit require a `rollout restart` for env-var consumers, but a
  *mounted-file* consumer would eventually see the change without one?
- If you `kubectl delete statefulset cdr-store`, is the CDR data gone? How would you
  guarantee it isn't?
- Where would RBAC, ResourceQuotas, and NetworkPolicies attach to make this stack
  safe for multiple teams? (Foreshadows Module 4.)

---

<details>
<summary><strong>✅ Solution</strong> (try the tasks first)</summary>

```bash
# 1. Namespace
kubectl create namespace self-care
kubectl config set-context --current --namespace=self-care

# 2. Config + Secret (DB_PASSWORD is a fictional placeholder)
kubectl create configmap subscriber-config \
  --from-literal=PLAN_TIER=gold --from-literal=DATA_QUOTA_GB=50 --from-literal=ROAMING=enabled
kubectl create secret generic subscriber-secret \
  --from-literal=DB_USER=mobily_app --from-literal=DB_PASSWORD='S3cr3t-Pa55'

# 3. API Deployment consuming both (apply a spec so we can wire env)
kubectl apply -f - <<'EOF'
apiVersion: apps/v1
kind: Deployment
metadata: { name: subscriber-api, labels: { app: subscriber-api } }
spec:
  replicas: 3
  selector: { matchLabels: { app: subscriber-api } }
  template:
    metadata: { labels: { app: subscriber-api } }
    spec:
      containers:
        - name: api
          image: registry.access.redhat.com/ubi9/httpd-24:latest
          ports: [ { containerPort: 8080 } ]
          envFrom: [ { configMapRef: { name: subscriber-config } } ]
          env:
            - name: DB_USER
              valueFrom: { secretKeyRef: { name: subscriber-secret, key: DB_USER } }
EOF
kubectl rollout status deployment/subscriber-api

# 4. Service + DNS check
kubectl expose deployment subscriber-api --port=80 --target-port=8080 --name=subscriber-api
kubectl run dnstest --image=registry.access.redhat.com/ubi9/ubi-minimal:latest \
  --restart=Never --command -- sleep 60
kubectl wait --for=condition=Ready pod/dnstest --timeout=60s
kubectl exec dnstest -- getent hosts subscriber-api
kubectl delete pod dnstest --force --grace-period=0

# 5. StatefulSet + headless Service
kubectl apply -f - <<'EOF'
apiVersion: v1
kind: Service
metadata: { name: cdr-store }
spec: { clusterIP: None, selector: { app: cdr-store }, ports: [ { port: 80 } ] }
---
apiVersion: apps/v1
kind: StatefulSet
metadata: { name: cdr-store }
spec:
  serviceName: cdr-store
  replicas: 2
  selector: { matchLabels: { app: cdr-store } }
  template:
    metadata: { labels: { app: cdr-store } }
    spec:
      containers:
        - name: store
          image: registry.access.redhat.com/ubi9/httpd-24:latest
          volumeMounts: [ { name: data, mountPath: /var/www/html } ]
  volumeClaimTemplates:
    - metadata: { name: data }
      spec: { accessModes: ["ReadWriteOnce"], resources: { requests: { storage: 256Mi } } }
EOF
kubectl rollout status statefulset/cdr-store
kubectl get pods -l app=cdr-store
kubectl get pvc -l app=cdr-store

# 6a. Scale
kubectl scale deployment subscriber-api --replicas=5
kubectl get pods -l app=subscriber-api --no-headers | wc -l    # 5
kubectl scale deployment subscriber-api --replicas=3

# 6b. Self-heal
POD=$(kubectl get pods -l app=subscriber-api -o jsonpath='{.items[0].metadata.name}')
kubectl delete pod "$POD"
kubectl get pods -l app=subscriber-api      # back to 3/3

# 6c. Config change -> rollout restart so env-var pods re-read it
kubectl patch configmap subscriber-config --type merge -p '{"data":{"ROAMING":"disabled"}}'
kubectl rollout restart deployment/subscriber-api
kubectl rollout status deployment/subscriber-api
POD=$(kubectl get pods -l app=subscriber-api -o jsonpath='{.items[0].metadata.name}')
kubectl exec "$POD" -- printenv ROAMING     # disabled

# 7. Persistence on the StatefulSet pod
kubectl exec cdr-store-0 -- sh -c "echo '8821001234,8821005678,2026-06-25,180,VOICE' >> /var/www/html/cdr.log"
kubectl delete pod cdr-store-0
kubectl wait --for=condition=Ready pod/cdr-store-0 --timeout=90s
kubectl exec cdr-store-0 -- cat /var/www/html/cdr.log     # the CDR is still there

# Stretch — DaemonSet (multi-node)
kubectl apply -f - <<'EOF'
apiVersion: apps/v1
kind: DaemonSet
metadata: { name: node-probe }
spec:
  selector: { matchLabels: { app: node-probe } }
  template:
    metadata: { labels: { app: node-probe } }
    spec:
      containers:
        - name: probe
          image: registry.access.redhat.com/ubi9/ubi-minimal:latest
          command: ["sh","-c","while true; do sleep 30; done"]
EOF
kubectl get pods -l app=node-probe -o wide    # one per worker, none on control-plane

# Cleanup — delete the whole namespace (removes everything, including PVCs)
kubectl delete namespace self-care
```

**Verified output (key lines):**

```
deployment "subscriber-api" successfully rolled out
10.96.x.x   subscriber-api.self-care.svc.cluster.local       # DNS resolves

NAME          READY   STATUS    AGE
cdr-store-0   1/1     Running   ...
cdr-store-1   1/1     Running   ...
data-cdr-store-0   Bound   ...   256Mi   RWO   standard
data-cdr-store-1   Bound   ...   256Mi   RWO   standard

disabled                                              # ROAMING after config change + restart
8821001234,8821005678,2026-06-25,180,VOICE            # CDR survived cdr-store-0 deletion
```

**Key point:** a real app is a *composition* — stateless tiers (Deployment) for
elastic, interchangeable work; stateful tiers (StatefulSet + per-pod PVC) for data
that must persist with identity; Services for discovery; ConfigMaps/Secrets for
environment-specific behaviour. Each primitive does one job; together they make an
operable system.
</details>

---

> **✅ Verified:** kubectl 1.34 · Kubernetes 1.33 (3-node kind, equivalent plain
> Kubernetes) · images `ubi9/httpd-24`, `ubi9/ubi-minimal`. The full stack —
> Deployment consuming ConfigMap+Secret, ClusterIP discovery by DNS, StatefulSet
> with per-pod PVCs, scale, self-heal, `rollout restart` picking up a ConfigMap
> change (`ROAMING=disabled`), and CDR persistence across a `cdr-store-0` deletion —
> was run live end-to-end and the output above is from that run.
