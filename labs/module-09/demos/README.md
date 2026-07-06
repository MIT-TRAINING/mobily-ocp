# Module 9 — Guided Demos (Instructor-Led)

These are **instructor-led, narrated walkthroughs**. The instructor runs each step live
while explaining *what* each object does and *why*. Participants watch and follow along,
then practice in the [`../exercises`](../exercises).

Module 9 — **"Operators, Helm and Application Deployment"** — covers the three deployment
methods: **Operators via OLM/OperatorHub**, **Kubernetes manifests**, and **Helm charts**.
Commands are **`oc`** and **`helm`**; manifests + Helm are standard Kubernetes, OLM/
OperatorHub are OpenShift's Operator packaging.

All scenarios use a **telecom domain** framing (`subscriber-api`, `self-care` portal, a
PostgreSQL Operator for the CDR store). Data is fictional.

## Demos in this module

| # | Demo | Concepts reinforced | Telecom scenario | Time |
|---|------|---------------------|------------------|------|
| 1 | [Install an Operator via OLM](demo-01-operators-olm.md) | OperatorHub · Subscription · InstallPlan · CSV · Custom Resource | **PostgreSQL** Operator for CDRs | ~30 min |
| 2 | [Deploy from manifests](demo-02-manifests-deployment.md) | `oc apply` idempotency · scaffold with `--dry-run` · Kustomize overlays | Ship **subscriber-api** | ~25 min |
| 3 | [Package & release with Helm](demo-03-helm-charts.md) | `helm create/lint/template` · values override · install/upgrade/rollback | Package **self-care** | ~30 min |

## Conventions

- Commands use **`oc`** and **`helm`**. Manifests + Helm are pure Kubernetes; OLM/
  OperatorHub/Subscription/CSV are OpenShift-specific (an **⎈** note flags equivalents).
- **Podman-first images:** the sample app is **`ubi9/httpd-24`** (rootless, HTTP on
  **8080**; a bare `GET /` returns **403** — proof of connectivity).
- **Permissions.** Deploying from **manifests** and using **Helm** work for a normal
  project user in their own project. **Installing an Operator** (Demo 1) is cluster-scope
  and needs **cluster-admin** — instructor-led. Each demo marks admin-only steps.
- Replace placeholders (`<cluster-domain>`). **Never commit real secrets**; sample values
  are fictional.
- Each demo ends with a **Cleanup** section.
- Companion material: the
  [concept guide](../../../guides/module-09-operators-helm-deployment.md), the interactive
  [visualizations](../index.html), and the [exercises](../exercises/README.md).

## Pre-flight check (run once before Demo 1)

```bash
oc login https://api.<cluster-domain>:6443 -u <user> -p "$OCP_PASSWORD"   # or token
oc whoami
helm version                 # Helm 3 client (Demo 3)
oc new-project mod9-demos --display-name="Module 9 Demos" 2>/dev/null || oc project mod9-demos
```

> **Instructor tip:** keep the **web console** open — **Operators → OperatorHub /
> Installed Operators** and **Developer → Helm** mirror the CLI. For Demo 1 have a
> **cluster-admin** session (or a pre-installed Operator to inspect). `helm template` and
> `oc create --dry-run=client -o yaml` render **without a cluster** — great for showing
> output even if the cluster is slow.

---

> **◐ Partially verified — Helm & manifests VERIFIED, OLM representative.**
> **Helm** (`helm create`/`lint`/`template`/`show values`) and **manifest scaffolding**
> (`oc create … --dry-run=client -o yaml`) were run **live with helm v3.16.3 / oc 4.22**
> (offline, no cluster) — that output is real. Steps needing a **live cluster** (installing
> an Operator, `oc apply` to the API, `helm install/upgrade` against the cluster) are
> labelled **"requires a cluster — representative of OpenShift 4.18"** and can be validated
> when the cluster is up (manifests/Helm as a normal user; Operator install as admin).
