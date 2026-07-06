# Demo 2 — Deploy from Kubernetes Manifests

> **Scenario:** Ship the Mobily **subscriber-api** with plain YAML. We scaffold a manifest
> **offline**, `oc apply` it (and prove idempotency vs `create`), expose it, then use
> **Kustomize** to render dev vs prod from one base.

| | |
|---|---|
| **Concepts reinforced** | scaffold with `--dry-run=client -o yaml` · `apply` idempotency vs `create` · `oc apply -k` · Kustomize overlays |
| **Maps to** | Guide §3, §4 · Visualization 02 · Exercise 2 |
| **Time** | ~25 minutes |
| **Cluster** | Shared OCP 4.18 — a normal project user can do all of this (scaffolding works offline) |

---

> **⎈ Kubernetes equivalent:** identical to `kubectl apply`/`kubectl kustomize`. `oc new-app`
> is an OpenShift scaffolding shortcut.

## Talking points to open with

- Everything (Helm, Operators) ultimately produces **manifests** — this is the base skill.
- **`apply`** is idempotent (create-or-update); **`create`** errors on re-run — that's why
  pipelines use apply.
- **Kustomize** removes copy-paste with base + overlays, no templating.

---

## Step 1 — Scaffold a manifest OFFLINE (verified)

```bash
oc create deployment subscriber-api \
  --image=registry.access.redhat.com/ubi9/httpd-24:latest --port=8080 \
  --dry-run=client -o yaml
```

**Verified output** *(oc 4.22, run offline — no cluster contacted):*

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  labels:
    app: subscriber-api
  name: subscriber-api
spec:
  replicas: 1
  selector:
    matchLabels:
      app: subscriber-api
  template:
    metadata:
      labels:
        app: subscriber-api
    spec:
      containers:
      - image: registry.access.redhat.com/ubi9/httpd-24:latest
        name: httpd-24
        ports:
        - containerPort: 8080
```

> **Narrate:** `--dry-run=client -o yaml` renders a valid manifest **without touching the
> cluster** — redirect it to a file, edit `replicas`, commit it. This is how you start a
> manifest without hand-typing boilerplate.

---

## Step 2 — `apply` vs `create` (idempotency)

```bash
oc create deployment subscriber-api \
  --image=registry.access.redhat.com/ubi9/httpd-24:latest -o yaml --dry-run=client > deploy.yaml
oc apply -f deploy.yaml        # 1st: created
oc apply -f deploy.yaml        # 2nd: unchanged  (idempotent)
oc create -f deploy.yaml       # errors: AlreadyExists
```

**Expected output** *(requires a cluster — representative):*

```
deployment.apps/subscriber-api created
deployment.apps/subscriber-api unchanged
Error from server (AlreadyExists): ... "subscriber-api" already exists
```

> **Narrate:** `apply` re-runs safely (`unchanged`, or `configured` if the YAML changed);
> `create` fails on the second run. GitOps re-applies constantly, so **apply** is the verb.

---

## Step 3 — Expose it

```bash
oc expose deployment subscriber-api --port=8080     # Service
oc expose service subscriber-api                     # Route
oc get deploy,svc,route -l app=subscriber-api
```

**Expected output** *(requires a cluster — representative):*

```
deployment.apps/subscriber-api   1/1   1   1
service/subscriber-api           ClusterIP   172.30.x.x   8080/TCP
route.route.openshift.io/subscriber-api   subscriber-api-mod9-demos.apps.<domain>
```

> **Narrate:** Three manifests (Deployment, Service, Route) = a reachable app — the Module
> 6 chain, created declaratively.

---

## Step 4 — Kustomize: one base, dev vs prod

```bash
# base/kustomization.yaml + base/deployment.yaml ; overlays/dev + overlays/prod patch it
oc kustomize overlays/dev    | grep -E 'replicas|image'
oc kustomize overlays/prod   | grep -E 'replicas|image'
oc apply -k overlays/prod
```

**Expected output** *(requires a cluster to apply; `oc kustomize` renders offline — representative):*

```
# dev
  replicas: 1
      - image: registry.access.redhat.com/ubi9/httpd-24:latest
# prod
  replicas: 6
      - image: registry.access.redhat.com/ubi9/httpd-24:1.0-prod
```

> **Narrate:** One **base**, two tiny **overlays** (replicas + image tag). No templating,
> no copy-paste — and it's the pattern GitOps (Module 10) applies straight from Git.

---

## Step 5 — Cleanup

```bash
oc delete all -l app=subscriber-api
```

**Expected output** *(representative):*

```
deployment.apps "subscriber-api" deleted
service "subscriber-api" deleted
route.route.openshift.io "subscriber-api" deleted
```

---

## Wrap-up questions to pose

1. How do you scaffold a manifest without a cluster?
2. Why does the second `oc create` fail but the second `oc apply` succeed?
3. What does Kustomize give you that copy-pasting per-env YAML doesn't?
4. Which verb do GitOps pipelines rely on, and why?

---

> **◐ Partially verified — Step 1 VERIFIED, cluster steps representative.** The
> `oc create … --dry-run=client -o yaml` scaffold (Step 1) was **run live offline with oc
> 4.22** — that YAML is real. Steps that touch the API (`oc apply`, `oc expose`,
> `oc apply -k`) **require a live cluster** and are **representative of OpenShift 4.18**;
> a normal user can validate them in their own project when the cluster is up. The
> `apply`-idempotent / `create`-AlreadyExists behaviour is real and documented.
