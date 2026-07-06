# Module 9 — Exercises (Hands-On Practice)

These are **participant-driven** tasks. You drive **`oc`** and **`helm`**, then verify with
the provided **validation** commands. Each exercise has a fully worked **solution** — try
the tasks first, then check.

Module 9 — **"Operators, Helm and Application Deployment"** — covers the three deployment
methods: **Operators via OLM**, **Kubernetes manifests**, and **Helm charts**. Manifests +
Helm are standard Kubernetes; OLM/OperatorHub are OpenShift's Operator packaging.

## Where to run these

| Target | What you can do | Notes |
|---|---|---|
| **Shared OpenShift 4.18 cluster** (preferred) | Manifests + Helm in your project | Installing an Operator (Ex 1) needs **cluster-admin** |
| **[Developer Sandbox](https://developers.redhat.com/developer-sandbox)** | Manifests + Helm | No cluster-admin → Operator install is instructor-demoed |
| **Local (no cluster)** | `helm create/lint/template`, `oc create --dry-run=client -o yaml` | Chart authoring + manifest scaffolding are fully offline |

> **Helm 3** is a client tool — install it (`brew install helm` or grab the binary from
> get.helm.sh). `helm template`/`lint` and `oc create --dry-run=client` need **no cluster**.

## Exercises in this module

| # | Exercise | What you'll practice | Telecom scenario | Difficulty |
|---|----------|----------------------|------------------|------------|
| 1 | [Install & use an Operator](exercise-01-operators-olm.md) | Subscription → CSV, inspect, create a CR | **PostgreSQL** for CDRs | ⭐ Beginner (admin for install) |
| 2 | [Deploy from manifests](exercise-02-manifests.md) | scaffold, `apply` vs `create`, Kustomize overlays | Ship **subscriber-api** | ⭐⭐ Intermediate |
| 3 | [Package an app with Helm (capstone)](exercise-03-helm-capstone.md) | create/lint/template, values, install/upgrade/rollback | Package **self-care** | ⭐⭐⭐ Advanced |

## Before you start

```bash
oc login https://api.<cluster-domain>:6443 -u <user> -p "$OCP_PASSWORD"   # or token
oc whoami
helm version                 # Helm 3 (Ex 3)
oc new-project mod9-ex --display-name="Module 9 Exercises" 2>/dev/null || oc project mod9-ex
```

- Images: **`ubi9/httpd-24`** (rootless, HTTP on **8080**; bare `GET /` → **403** proves
  connectivity).
- Replace placeholders (`<cluster-domain>`). **Never commit real secrets** — sample values
  are fictional.
- **Operator install** (Ex 1) needs **cluster-admin**; a normal user does the inspect/CR
  parts once the Operator exists (or follows the instructor).
- Cleanup: `oc delete project mod9-ex`; `helm uninstall <release>`; delete chart dirs.

## How to self-assess

Each exercise's **Validation** section gives commands whose output confirms success. Note
that **`helm template`/`lint`** and **`oc create --dry-run=client -o yaml`** let you check
your work **without a cluster**. Stuck? The **Solution** walks one correct approach.

Companion material: the guided [demos](../demos/README.md), the interactive
[visualizations](../index.html), and the
[concept guide](../../../guides/module-09-operators-helm-deployment.md).

---

> **✅ Verified (Helm & manifest authoring) / ◐ representative (cluster ops).** Chart
> authoring (`helm create/lint/template/show values`, helm v3.16.3) and manifest scaffolding
> (`oc create … --dry-run=client -o yaml`, oc 4.22) were **run live offline** — that output
> is real. Steps needing a **live cluster** (Operator install, `oc apply`, `helm install`)
> are **representative of OpenShift 4.18** and can be validated when the cluster is up
> (manifests/Helm as a normal user; Operator install as admin).
