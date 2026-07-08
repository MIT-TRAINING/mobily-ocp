# Demo 3 — Capstone: End-to-End Deploy

> **Scenario:** We stand up Mobily's **self-care stack** — a three-tier service
> (`self-care` portal → `subscriber-api` → `subscriber-db`) — using, in one deployment, an object
> from nearly every module: a **Secret** and **PVC** (M7), **Deployments** and **Services** (M3),
> a **Route** (M6), a **NetworkPolicy** (M6), **monitoring** (M11), and finally an **Argo CD
> Application** (M10) so Git becomes the source of truth. This is the course, assembled.

| | |
|---|---|
| **Concepts reinforced** | Secret · PVC · Deployment · Service · Route (edge TLS) · NetworkPolicy · ServiceMonitor · Argo CD Application · dependency order |
| **Maps to** | Guide §11 · Visualization 03 · Exercise 3 |
| **Time** | ~35 minutes |
| **Cluster** | Shared OCP 4.18 — the stack is **project-user**; the Argo CD Operator is **admin-installed** (Module 10). Manifests **render offline**. |

---

> **⎈ Kubernetes note:** Secret, PVC, Deployment, Service, NetworkPolicy are **core Kubernetes**;
> **Route** and the **Argo CD Application** CRD are the OpenShift/GitOps additions. Everything here
> is declarative YAML — commit it and let Argo CD apply it.

> ⚠️ Installing the **OpenShift GitOps (Argo CD)** Operator is admin (Module 10). Creating the
> Secret/PVC/Deployment/Service/Route/NetworkPolicy in **your own project** is project-user.

## Talking points to open with

- **Order is dependencies:** Secret + PVC before the DB; Services before the Route.
- Every object is a module — this graph *is* the course.
- The finish line is **GitOps**: don't `oc apply` by hand forever — let Argo CD sync from Git and
  self-heal.

---

## Step 1 — The project and the Secret (M8 tenant, M7 credentials)

```bash
oc new-project mobily-capstone
oc create secret generic subscriber-db-creds \
  --from-literal=username=mobily \
  --from-literal=password='<your-password>' \
  -n mobily-capstone --dry-run=client -o yaml
```

**Verified render** *(`oc create --dry-run=client -o yaml`, run offline with oc 4.22 — real):*

```yaml
apiVersion: v1
data:
  password: PHlvdXItcGFzc3dvcmQ+
  username: bW9iaWx5
kind: Secret
metadata:
  name: subscriber-db-creds
  namespace: mobily-capstone
```

> **Narrate:** Never hard-code credentials — the DB and API read them from this **Secret** (M7).
> Note the values are **base64**, not encrypted (`PHlvdXItcGFzc3dvcmQ+` decodes to
> `<your-password>`) — that's why Secrets need RBAC (M8), not obscurity. Drop `--dry-run` to apply.

---

## Step 2 — Durable storage for the database (M7)

```bash
oc create -f - --dry-run=client -o yaml <<'EOF'
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: subscriber-db-data
  namespace: mobily-capstone
spec:
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 2Gi
EOF
```

**Verified render** *(`oc create --dry-run=client -o yaml`, run offline with oc 4.22 — real):*

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: subscriber-db-data
  namespace: mobily-capstone
spec:
  accessModes:
  - ReadWriteOnce
  resources:
    requests:
      storage: 2Gi
```

> **Narrate:** The DB's data must survive a pod reschedule (Module 12's node lifecycle!). The
> **PVC** binds to a **PV** via the default StorageClass; the bytes live outside the pod. Recall
> from §2 of the guide: the **etcd backup** would restore *this PVC object* but **not** the data
> inside its PV — that needs its own snapshot/OADP.

---

## Step 3 — The three tiers (M3 Deployments)

```bash
# db tier — render offline to show the shape, then wire in the Secret/PVC before applying:
oc create deployment subscriber-db \
  --image=quay.io/sclorg/postgresql-15-c9s:latest \
  -n mobily-capstone --dry-run=client -o yaml
```

**Verified render** *(`oc create --dry-run=client -o yaml`, run offline with oc 4.22 — real, trimmed):*

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  labels:
    app: subscriber-db
  name: subscriber-db
  namespace: mobily-capstone
spec:
  replicas: 1
  selector:
    matchLabels:
      app: subscriber-db
  template:
    metadata:
      labels:
        app: subscriber-db
    spec:
      containers:
      - image: quay.io/sclorg/postgresql-15-c9s:latest
        name: postgresql-15-c9s
```

> **Narrate:** This is the skeleton — in the real manifest you add `envFrom` the **Secret** and a
> `volumeMount` for the **PVC**. Then two more Deployments (`subscriber-api`, `self-care`). The
> `app:` **label** is the thread Services and NetworkPolicies select on — get it right and the rest
> wires up.

---

## Step 4 — Services + the Route (M3/M6 — expose it)

```bash
oc expose deployment self-care --port=8080 -n mobily-capstone          # Service (repeat for api, db)
oc create route edge self-care --service=self-care --port=8080 \
  -n mobily-capstone --dry-run=client -o yaml
```

**Verified render** *(`oc create route edge --dry-run=client -o yaml`, run offline with oc 4.22 — real):*

```yaml
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: self-care
  namespace: mobily-capstone
spec:
  port:
    targetPort: 8080
  tls:
    termination: edge
  to:
    kind: ""
    name: self-care
    weight: null
status: {}
```

> **Narrate:** The **Service** gives each tier a stable in-cluster address; the **Route** (edge TLS
> terminated at the router) exposes only the `self-care` portal to customers. Key gotcha: a Route
> with **no ready endpoints** behind its Service → **503**. `oc get endpoints self-care` must be
> non-empty. Only the portal is exposed — api and db stay internal.

---

## Step 5 — Guard it, watch it, then hand it to GitOps (M6, M11, M10)

```bash
# NetworkPolicy: only the portal may reach the api (M6). ServiceMonitor + alert on api 5xx (M11).
# Then commit ALL the manifests to Git and point Argo CD at them:
oc get application -n openshift-gitops                 # after the Argo CD Application syncs
```

**Expected output** *(requires a cluster + Argo CD — representative):*

```
NAME              SYNC STATUS   HEALTH STATUS
mobily-capstone   Synced        Healthy
```

> **Narrate:** The finish line. Instead of `oc apply`-ing nine objects forever, they live in
> **Git**; an **Argo CD Application** syncs them and reports **Synced / Healthy**. Delete the Route
> by hand and Argo CD **self-heals** it back — declarative recovery that complements the etcd
> snapshot. That's the whole course: build it (M3–M8), watch it (M11), deliver it by GitOps (M10),
> recover it (M12).

---

## Step 6 — Cleanup

```bash
# if managed by Argo CD, delete the Application first (or it self-heals the namespace back):
oc delete application mobily-capstone -n openshift-gitops 2>/dev/null || true
oc delete project mobily-capstone
```

---

## Wrap-up questions to pose

1. Why create the **Secret** and **PVC** before the database **Deployment**?
2. The Route returns **503** but the pod is healthy — what's the most likely cause?
3. An etcd restore brings back the **PVC object** — does it bring back the database's **data**? Why
   not?
4. Someone deletes the Route by hand. With Argo CD managing the app, what happens next?

---

> **◐ Partially verified:** the capstone **manifests render for real** — the **Secret**, **PVC**,
> **Deployment**, and **Route** YAML above were produced by `oc create --dry-run=client -o yaml`
> **run live offline with oc 4.22** (real output). Steps needing a **live cluster** (actual pod
> readiness, endpoints, Argo CD `Synced/Healthy`) are **representative of OpenShift 4.18** — the
> stack objects apply as a project user; the **Argo CD Operator** install is admin (Module 10).
> Validate live when the cluster is up. Image `quay.io/sclorg/postgresql-15-c9s` is the freely
> pullable PostgreSQL used across this course.
