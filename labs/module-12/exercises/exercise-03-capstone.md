# Exercise 3 — Capstone: End-to-End Deploy (Course Capstone)

> **Scenario:** This is the course, assembled. You'll stand up Mobily's **self-care stack**
> (`self-care` → `subscriber-api` → `subscriber-db`) from scratch — a **Secret** and **PVC** (M7),
> three **Deployments** and **Services** (M3), a **Route** (M6), a **NetworkPolicy** (M6),
> **monitoring** (M11), and an **Argo CD Application** (M10) so Git owns it all. Then you'll close
> the day-2 loop: take an etcd snapshot (M12), **break** the stack on purpose, **diagnose** it with
> the Module-12 methodology, fix it, and confirm GitOps reports **Synced / Healthy**.

| | |
|---|---|
| **Practice** | Secret · PVC · Deployment · Service · Route · NetworkPolicy · ServiceMonitor · Argo CD Application · troubleshooting · backup |
| **Maps to** | Guide §11 (+ §2–§10) · Visualization 03 · Demo 3 · **all prior modules** |
| **Difficulty** | ⭐⭐⭐ Advanced (course capstone) · ~45 min · stack is project-user; Argo CD/backup need admin |

> ⚠️ The stack objects are **project-user** in `mobily-capstone`. The **Argo CD Operator** install
> (M10) and the **etcd snapshot** (Task 6) are **cluster-admin** — pair with your instructor.

---

## Tasks

1. **Project + Secret + PVC.** Create `mobily-capstone`, a `Secret` `subscriber-db-creds`
   (username/password), and a 2Gi `PVC` `subscriber-db-data`. **Render each offline**
   (`--dry-run=client -o yaml`) before applying.

   > **Gotcha (found live):** if you plan to wire this Secret into `subscriber-db` with
   > `oc set env --from=secret/...` (Task 2), name its keys **`POSTGRESQL_USER`** /
   > **`POSTGRESQL_PASSWORD`** exactly — not `username`/`password`. `oc set env --from=secret`
   > **uppercases** the secret's key name to form the env var name (a key named `username` becomes
   > env var `USERNAME`, confirmed live), so a secret keyed `username`/`password` produces env vars
   > `USERNAME`/`PASSWORD` — neither of which the sclorg postgres image recognizes. It requires the
   > env vars named exactly `POSTGRESQL_USER`/`POSTGRESQL_PASSWORD`/`POSTGRESQL_DATABASE`, so the
   > Secret's keys need to already be spelled that way. Get this wrong and the container never
   > starts (`CreateContainerConfigError`, or a "you must specify POSTGRESQL_USER..." log).
   > Confirmed by actually running it — see the exercise footer.
2. **Three tiers.** Deploy `subscriber-db` (`quay.io/sclorg/postgresql-15-c9s`, mounting the Secret
   as env + the PVC for data), `subscriber-api`, and `self-care` (both `ubi9/httpd-24` stand-ins).
3. **Wire + expose.** A `Service` per tier; an **edge-TLS `Route`** on `self-care` only. Confirm the
   Route resolves and the Service has **endpoints**.
4. **Guard + watch.** A `NetworkPolicy` allowing only `self-care` → `subscriber-api`; a
   `ServiceMonitor` (+ alert) on `subscriber-api` (M11 — needs UWM).
5. **GitOps.** Commit all manifests to Git, create an **Argo CD `Application`** pointing at the repo,
   and confirm it reports **Synced / Healthy**.
6. **Close the day-2 loop.** Take an **etcd snapshot** (Ex 1). Then **break** the stack (e.g.,
   `oc scale deploy/subscriber-db --replicas=0`), watch `subscriber-api` fail, **diagnose** with the
   Ex-2 loop, fix it, and confirm Argo CD is **Healthy** again.

> **Hint (Task 3):** a Route with no ready endpoints → **503**. `oc get endpoints self-care` must be
> non-empty.

> **Hint (Task 6):** deleting an Argo-CD-managed object triggers **self-heal**; *scaling* the
> deployment is a cleaner way to inject a fault to diagnose.

---

## Validation

```bash
# 1. manifests are valid offline:
oc create -f secret.yaml  --dry-run=client -o yaml >/dev/null && echo "Secret ok"
oc create -f pvc.yaml     --dry-run=client -o yaml >/dev/null && echo "PVC ok"
oc create -f route.yaml   --dry-run=client -o yaml >/dev/null && echo "Route ok"

# 3. exposed with endpoints (after apply):
oc -n mobily-capstone get route self-care
oc -n mobily-capstone get endpoints self-care          # must be non-empty
oc -n mobily-capstone get pods                          # all Running/Ready

# 5. GitOps:
oc -n openshift-gitops get application mobily-capstone  # Synced / Healthy

# 6. break -> diagnose -> fix:
oc -n mobily-capstone scale deploy/subscriber-db --replicas=0   # inject fault
oc -n mobily-capstone get pods                                   # subscriber-api errors/crashes
oc -n mobily-capstone scale deploy/subscriber-db --replicas=1    # fix
```

Expected: every manifest renders offline; the Route has non-empty endpoints and serves the portal
(`httpd-24` → 403 on `/` proves connectivity); Argo CD shows **Synced / Healthy**; scaling the db to
0 makes `subscriber-api` fail (traced via events/logs), and restoring it recovers the stack.

---

## Reflection

- Trace one customer request through **every module** it touches, naming the object at each hop.
- The etcd snapshot would restore the **PVC object** — but not the database's **data**. What's your
  plan for the data itself?
- You have **two** recovery nets here: Argo CD self-heal and the etcd snapshot. What class of
  failure does each cover, and where do they *not* overlap?

---

<details>
<summary><strong>✅ Solution</strong> (try the tasks first — Argo CD + snapshot need admin)</summary>

```bash
oc new-project mobily-capstone

# 1. Secret + PVC (render offline first)
# NOTE: keys are named to match what postgres needs directly (POSTGRESQL_USER/PASSWORD) —
# oc set env --from=secret uppercases the key name to make the env var name, so `username`/
# `password` would become USERNAME/PASSWORD, which the image doesn't recognize (verified live).
oc create secret generic subscriber-db-creds \
  --from-literal=POSTGRESQL_USER=mobily --from-literal=POSTGRESQL_PASSWORD='<your-password>' \
  -n mobily-capstone --dry-run=client -o yaml | tee secret.yaml
oc create -f - --dry-run=client -o yaml <<'EOF' | tee pvc.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata: { name: subscriber-db-data, namespace: mobily-capstone }
spec: { accessModes: [ReadWriteOnce], resources: { requests: { storage: 2Gi } } }
EOF
oc apply -f secret.yaml -f pvc.yaml
# the PVC stays Pending until Task 2's pod mounts it — this cluster's default StorageClass
# (gp3-csi) uses WaitForFirstConsumer binding (verified live); that's expected, not a fault.

# 2. three tiers (skeletons; add envFrom Secret + volumeMount PVC to the db)
oc create deployment subscriber-db  --image=quay.io/sclorg/postgresql-15-c9s:latest -n mobily-capstone
oc set env deploy/subscriber-db --from=secret/subscriber-db-creds \
  POSTGRESQL_DATABASE=subscribers -n mobily-capstone
oc set volume deploy/subscriber-db --add --name=data --type=pvc \
  --claim-name=subscriber-db-data --mount-path=/var/lib/pgsql/data -n mobily-capstone
oc create deployment subscriber-api --image=registry.access.redhat.com/ubi9/httpd-24 -n mobily-capstone
oc create deployment self-care      --image=registry.access.redhat.com/ubi9/httpd-24 -n mobily-capstone

# 3. Services + Route (edge TLS on the portal only)
oc expose deployment self-care      --port=8080 -n mobily-capstone
oc expose deployment subscriber-api --port=8080 -n mobily-capstone
oc expose deployment subscriber-db  --port=5432 -n mobily-capstone
oc create route edge self-care --service=self-care --port=8080 -n mobily-capstone | tee route.yaml
# rendering AFTER the self-care Service exists means the Route inherits the Service's
# labels (verified live: metadata.labels: {app: self-care} appears on the created Route) —
# render it before `oc expose` and that label is absent.
oc -n mobily-capstone get endpoints self-care        # non-empty = Service has ready pods
# verified live: right after `oc create route`, endpoints show <none> until the self-care
# pod actually reaches Ready — it populates itself once that happens, no action needed.

# 4. NetworkPolicy (only self-care -> subscriber-api) + ServiceMonitor (M11, needs UWM)
oc apply -n mobily-capstone -f - <<'EOF'
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: { name: allow-portal-to-api }
spec:
  podSelector: { matchLabels: { app: subscriber-api } }
  ingress:
    - from: [ { podSelector: { matchLabels: { app: self-care } } } ]
EOF

# 5. GitOps: commit the manifests, then an Argo CD Application points at the repo
oc apply -f - <<'EOF'
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata: { name: mobily-capstone, namespace: openshift-gitops }
spec:
  project: default
  source: { repoURL: https://github.com/<you>/mobily-capstone.git, path: manifests, targetRevision: main }
  destination: { server: https://kubernetes.default.svc, namespace: mobily-capstone }
  syncPolicy: { automated: { prune: true, selfHeal: true } }
EOF
oc -n openshift-gitops get application mobily-capstone     # Synced / Healthy

# 6. day-2 loop: snapshot (Ex1) -> break -> diagnose (Ex2) -> fix
#   (snapshot via oc debug node/<master> + cluster-backup.sh — see Exercise 1)
oc -n mobily-capstone scale deploy/subscriber-db --replicas=0    # inject fault
oc -n mobily-capstone get pods                                    # subscriber-api starts failing
oc -n mobily-capstone logs -l app=subscriber-api --previous --tail=5   # connection refused: subscriber-db
oc -n mobily-capstone scale deploy/subscriber-db --replicas=1    # fix; Argo CD stays/returns Healthy
```

**Live-verified renders** *(`oc create --dry-run=client -o yaml` with oc 4.22 against the OCP
4.18.45 training cluster; the full stack — Secret, PVC, all three Deployments, Services, Route —
was also applied for real in a scratch project and torn down afterward):*

```yaml
# Secret
apiVersion: v1
data:
  POSTGRESQL_PASSWORD: ZGVtb3Bhc3N3b3Jk
  POSTGRESQL_USER: bW9iaWx5
kind: Secret
metadata:
  name: subscriber-db-creds
  namespace: mobily-capstone
---
# Route (rendered after the self-care Service already existed — note the inherited label)
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  labels:
    app: self-care
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
```

Applying the full stack for real surfaced one bug the offline render alone couldn't catch: with
the Secret keyed `username`/`password` (its render is correct — that's a valid Secret), `oc set
env deploy/subscriber-db --from=secret/subscriber-db-creds` produced env vars `USERNAME`/
`PASSWORD`, and the postgres container failed to start (`CreateContainerConfigError`, then a log
demanding `POSTGRESQL_USER`/`POSTGRESQL_PASSWORD`/`POSTGRESQL_DATABASE`). Re-keying the Secret to
`POSTGRESQL_USER`/`POSTGRESQL_PASSWORD` fixed it — the pod reached `1/1 Running` and the log showed
PostgreSQL genuinely `accepting connections`. The Task 1/2 solution above reflects the fix.

**Why this is the whole course:** a customer request enters through a **Route** (M6) → **Service**
(M3) → **Deployment** (M3), which reads a **Secret** (M7) to reach a DB backed by a **PVC/PV** (M7),
inside an RBAC-scoped **Project** (M8), guarded by a **NetworkPolicy** (M6), watched by **Prometheus**
(M11), delivered by **GitOps** (M10). Then Module 12's day-2 skills make it *survivable*: an **etcd
snapshot** protects the control plane, and the **troubleshooting loop** finds the root cause when you
break it. Two recovery nets, different jobs: **Argo CD self-heal** restores *declared config drift*;
the **etcd snapshot** restores the *whole control plane* after quorum loss — and neither restores PV
**data** (that's OADP). Build it, watch it, recover it — you can run OpenShift.
</details>

---

> **● Live-verified — 2026-07-16**, project-user, on the shared **OCP 4.18.45** training cluster.
> Tasks 1–3 were run for real in a scratch project: Secret, PVC, all three Deployments
> (`subscriber-db`/`subscriber-api`/`self-care`), Services, and the edge Route were **applied**, not
> just rendered. This live run **found and fixed a real bug** in the solution: the original
> `username`/`password` Secret keys don't match what `oc set env --from=secret` produces
> (`USERNAME`/`PASSWORD` — it uppercases the key name) or what the postgres image requires
> (`POSTGRESQL_USER`/`POSTGRESQL_PASSWORD` exactly) — the db container never started until the
> Secret's keys were renamed to match (see inline notes and the "Verified renders" section). Two
> more real behaviors were confirmed: the PVC stays `Pending` under `WaitForFirstConsumer` until a
> pod mounts it, and `oc create route` inherits `app:` labels from a pre-existing target Service.
> The scratch project was deleted after. **Task 4 (NetworkPolicy/ServiceMonitor), Task 5 (Argo CD
> Application + `Synced/Healthy`), and Task 6 (etcd snapshot + break/diagnose/fix loop)** remain
> **representative** — GitOps (OpenShift GitOps operator) is installed on this cluster but wiring a
> real Git-backed Application, and re-running the admin-only etcd snapshot, wasn't repeated here
> (see Demo 1/Exercise 1 and Demo 2/Exercise 2 for those live-verified separately). Images
> `ubi9/httpd-24` (403 on `/` proves connectivity) and `quay.io/sclorg/postgresql-15-c9s` (freely
> pullable) are the course standards.
