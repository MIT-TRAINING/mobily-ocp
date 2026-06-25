# Assignment 4 — ConfigMaps, Secrets & Persistent Storage

> **Module 3 · Kubernetes Workloads, Storage and Networking**
> **Telecom scenario:** Security review flagged two problems with the self-care
> rollout: (1) the **region/banner are baked into the image**, so promoting the
> same artifact from dev → prod means a rebuild, and (2) the **API key for the
> subscriber endpoints is hard-coded**. You'll externalize configuration into a
> **ConfigMap**, move the API key into a **Secret**, and give the **CDR archive**
> component real **persistent storage** that survives Pod restarts — first with a
> PVC on a Deployment, then with a **StatefulSet** giving each replica its own
> durable volume.

| | |
|---|---|
| **Maps to** | ConfigMaps & Secrets · Volumes & storage · StatefulSets |
| **Tools** | `minikube` + `kubectl` |
| **Provided** | `selfcare-api:1.0.0` (reads `SELFCARE_REGION`, `SELFCARE_BANNER`, `SELFCARE_API_KEY`) |
| **Difficulty** | ⭐⭐⭐ Advanced · ~70 min |
| **Weight** | 20 % of the Modules 1–3 assessment |

---

## Learning objectives

By the end you can:

1. Externalize non-secret config in a **ConfigMap** and inject it with `envFrom`.
2. Store sensitive values in a **Secret** and explain how it differs from a
   ConfigMap (and what base64 does **not** give you).
3. Update config and **trigger a rollout** so Pods pick up the change.
4. Attach a **PersistentVolumeClaim** to a Deployment and prove data **survives a
   Pod delete**.
5. Use a **StatefulSet** with `volumeClaimTemplates` so each replica gets its own
   stable identity and its own volume.

## Prerequisites

```bash
minikube start
kubectl create namespace selfcare 2>/dev/null || true
minikube image load selfcare-api:1.0.0
```

Recall the app's behaviour: when `SELFCARE_API_KEY` is set, `/subscribers*`
requires header `X-API-Key: <value>` (else `401`). `SELFCARE_REGION` and
`SELFCARE_BANNER` surface on `/version` and `/`.

---

## Tasks

### Part A — Externalize config with a ConfigMap (5 pts)
1. Create `selfcare-config` (ConfigMap) with `SELFCARE_REGION: "riyadh-dc1"` and
   `SELFCARE_BANNER: "Mobily Self-Care (Prod)"`.
2. Change your Deployment to consume it with `envFrom.configMapRef` (drop the
   inline `env` region from Assignment 3). `apply` and roll out.
3. Confirm `/version` now reports `"region":"riyadh-dc1"` and `/` shows the prod
   banner — **without rebuilding the image**.

### Part B — Move the API key into a Secret (5 pts)
4. Create `selfcare-secret` (Opaque) with `SELFCARE_API_KEY`. Use `stringData`
   (or `kubectl create secret generic --from-literal`).
5. Add `envFrom.secretRef` to the Deployment and roll out.
6. Prove the endpoint is now **protected**: a plain `GET /subscribers` returns
   `401`, and the same request **with** the `X-API-Key` header returns data.
7. Show that `kubectl get secret selfcare-secret -o yaml` stores the value
   **base64-encoded, not encrypted**. In one or two sentences, state why a Secret
   is still better than a ConfigMap here, and one extra control you'd add in
   production (e.g. RBAC, encryption-at-rest, an external secrets manager).

### Part C — Persistent storage on a Deployment (5 pts)
8. Create a **PVC** `selfcare-data` (`ReadWriteOnce`, 256Mi). Mount it at
   `/app/archive` in the Deployment.
9. `exec` into a Pod and write an archive file, e.g.
   `/app/archive/cdr-2026-06.csv` (copy in `app/data/cdrs.csv` or echo a row).
10. **Delete that Pod.** When the ReplicaSet recreates it, `exec` in again and show
    `/app/archive/cdr-2026-06.csv` **is still there** — data outlived the Pod.
11. Contrast this with writing the same file to a path *not* on the volume (e.g.
    `/tmp`) and deleting the Pod. What happens, and why?

### Part D — StatefulSet for per-replica volumes (5 pts)
12. Write a **StatefulSet** `cdr-archive` (2 replicas) + a **headless Service**,
    using `volumeClaimTemplates` so each Pod gets its **own** PVC.
13. Show the Pods have **stable ordinal names** (`cdr-archive-0`, `cdr-archive-1`)
    and **one PVC each** (`kubectl get pvc -n selfcare`).
14. Write a *different* file into `cdr-archive-0` vs `cdr-archive-1`, delete both
    Pods, and after they restart show each Pod **still has its own** file — proving
    the volume is bound to the Pod identity, not shared. When would a telecom CDR
    archive want this over a plain Deployment+PVC?

---

## Deliverables

`submission-04.md` with: `configmap.yaml`, `secret.yaml` (key redacted to a
placeholder), the updated `deployment.yaml`, `pvc.yaml`, and `statefulset.yaml`;
the before/after `/version` + banner; the `401`-vs-`200` proof for the API key;
the persistence proof (file survives Pod delete); the `kubectl get pvc` listing;
and written answers to Tasks 7, 11, and 14.

---

## Validation (self-check)

```bash
# A — config came from the ConfigMap:
curl -s $(minikube ip):30080/version | grep -q '"region": "riyadh-dc1"' && echo "PASS config"

# B — Secret protects the endpoint:
curl -s -o /dev/null -w '%{http_code}\n' $(minikube ip):30080/subscribers            # 401
curl -s -H "X-API-Key: <your-key>" $(minikube ip):30080/subscribers/966500000001 | grep -q msisdn && echo "PASS secret"

# C — data survives a Pod delete:
POD=$(kubectl get pod -n selfcare -l app=selfcare-api -o name | head -1)
kubectl exec -n selfcare $POD -- sh -c 'echo "CDR-0000001,966500000001" > /app/archive/cdr-2026-06.csv'
kubectl delete -n selfcare $POD
sleep 8; NEW=$(kubectl get pod -n selfcare -l app=selfcare-api -o name | head -1)
kubectl exec -n selfcare $NEW -- cat /app/archive/cdr-2026-06.csv && echo "PASS persistence"

# D — each StatefulSet replica has its own PVC:
kubectl get pvc -n selfcare | grep archive-cdr-archive    # archive-cdr-archive-0, -1
```

---

## Grading rubric (20 pts)

| Criteria | Pts |
|---|---|
| ConfigMap injected via `envFrom`; config change without rebuild proven | 5 |
| Secret protects endpoint (401 vs 200); base64≠encryption explained | 5 |
| PVC on Deployment; data survives Pod delete; ephemeral contrast explained | 5 |
| StatefulSet with per-replica PVCs; stable identity + use-case explained | 5 |
| **Total** | **20** |

> Deduction: putting the API key in the ConfigMap, or committing a real key value
> (−5, automatic). Keys are placeholders; the *mechanism* is what's graded.

---

## Stretch goals (not graded)

- Mount the ConfigMap as a **file** (volume) instead of env vars, e.g. project
  `subscribers.json` over `/app/data`. When is file-mounting better than env?
- Set `kubectl rollout restart deploy/selfcare-api` after editing a ConfigMap —
  why doesn't a ConfigMap change *automatically* restart Pods?
- Enable a Secret as an `imagePullSecret` concept discussion: how would a private
  registry pull differ from this app-level Secret?

---

<details>
<summary><strong>✅ Reference solution</strong> (attempt the tasks first)</summary>

**configmap.yaml / secret.yaml**
```yaml
apiVersion: v1
kind: ConfigMap
metadata: { name: selfcare-config, namespace: selfcare }
data:
  SELFCARE_REGION: "riyadh-dc1"
  SELFCARE_BANNER: "Mobily Self-Care (Prod)"
---
apiVersion: v1
kind: Secret
metadata: { name: selfcare-secret, namespace: selfcare }
type: Opaque
stringData:
  SELFCARE_API_KEY: "<your-key>"      # placeholder — never commit a real key
```

**Deployment env wiring (snippet)**
```yaml
      containers:
        - name: selfcare-api
          image: selfcare-api:1.0.0
          imagePullPolicy: IfNotPresent
          envFrom:
            - configMapRef: { name: selfcare-config }
            - secretRef:    { name: selfcare-secret }
          volumeMounts:
            - { name: archive, mountPath: /app/archive }
      volumes:
        - name: archive
          persistentVolumeClaim: { claimName: selfcare-data }
```

**pvc.yaml**
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata: { name: selfcare-data, namespace: selfcare }
spec:
  accessModes: ["ReadWriteOnce"]
  resources: { requests: { storage: 256Mi } }
```

**statefulset.yaml**
```yaml
apiVersion: v1
kind: Service
metadata: { name: cdr-archive, namespace: selfcare }
spec:
  clusterIP: None
  selector: { app: cdr-archive }
  ports: [{ port: 8080, targetPort: 8080 }]
---
apiVersion: apps/v1
kind: StatefulSet
metadata: { name: cdr-archive, namespace: selfcare }
spec:
  serviceName: cdr-archive
  replicas: 2
  selector: { matchLabels: { app: cdr-archive } }
  template:
    metadata: { labels: { app: cdr-archive } }
    spec:
      containers:
        - name: selfcare-api
          image: selfcare-api:1.0.0
          imagePullPolicy: IfNotPresent
          ports: [{ containerPort: 8080 }]
          volumeMounts: [{ name: archive, mountPath: /app/archive }]
          readinessProbe:
            httpGet: { path: /healthz, port: 8080 }
            initialDelaySeconds: 2
  volumeClaimTemplates:
    - metadata: { name: archive }
      spec:
        accessModes: ["ReadWriteOnce"]
        resources: { requests: { storage: 128Mi } }
```

```bash
kubectl apply -f configmap.yaml -f secret.yaml -f pvc.yaml
kubectl apply -f deployment.yaml         # now with envFrom + volume
kubectl rollout status deploy/selfcare-api -n selfcare
curl -s $(minikube ip):30080/version                       # region riyadh-dc1
curl -s -o /dev/null -w '%{http_code}\n' $(minikube ip):30080/subscribers   # 401
curl -s -H "X-API-Key: <your-key>" $(minikube ip):30080/subscribers/966500000001
kubectl get secret selfcare-secret -n selfcare -o yaml      # value is base64, NOT encrypted

# persistence
POD=$(kubectl get pod -n selfcare -l app=selfcare-api -o name | head -1)
kubectl exec -n selfcare $POD -- sh -c 'echo row > /app/archive/cdr-2026-06.csv'
kubectl delete -n selfcare $POD
sleep 8
kubectl exec -n selfcare $(kubectl get pod -n selfcare -l app=selfcare-api -o name | head -1) \
  -- cat /app/archive/cdr-2026-06.csv     # survived

# stateful
kubectl apply -f statefulset.yaml
kubectl get pod,pvc -n selfcare | grep cdr-archive          # -0 and -1, one PVC each
```

**Key point:** ConfigMaps and Secrets decouple **config from image** so one tested
artifact promotes across environments. A Secret is base64 (encoding, *not*
encryption) — its value is RBAC-restricted and can be encrypted at rest, which is
why secrets still don't belong in a ConfigMap or in git. A **PVC** gives a
Deployment durable storage that outlives Pods; a **StatefulSet** goes further,
binding a *distinct* volume to each stable Pod identity — what a sharded CDR
archive or a database needs.
</details>

---

> **✅ Verified:** the app's env-driven config and `SELFCARE_API_KEY` auth (401
> without the header, data with it) were exercised on podman 5.8.2 · 2026-06-25.
> All manifests pass `kubectl apply --dry-run=client` (v1.34). Run on minikube for
> the live PVC/StatefulSet persistence output (cluster-specific).
