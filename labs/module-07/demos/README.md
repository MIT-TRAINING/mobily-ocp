# Module 7 — Guided Demos (Instructor-Led)

These are **instructor-led, narrated walkthroughs**. The instructor runs each step live
against the real **OpenShift 4.18** cluster while explaining *what* each object does and
*why*. Participants watch and follow along, then practice in the
[`../exercises`](../exercises).

Module 7 — **"Storage and Security Fundamentals"** — covers durable **storage** (PV, PVC,
StorageClass, dynamic provisioning, ODF) and core **security** (Security Context
Constraints, ServiceAccounts, Secrets). Commands are **`oc`**; PV/PVC/SA/Secret are
standard Kubernetes, **SCC** is OpenShift-specific.

All scenarios use a **telecom domain** framing (CDR archive, subscriber-db, billing app
DB password, carrier API key). Data and credentials are fictional placeholders.

## Demos in this module

| # | Demo | Concepts reinforced | Telecom scenario | Time |
|---|------|---------------------|------------------|------|
| 1 | [Persistent storage](demo-01-persistent-storage.md) | PVC → StorageClass → PV binding · dynamic provisioning · persistence across pods · access modes/reclaim | **CDR archive** that must survive | ~30 min |
| 2 | [Security Context Constraints](demo-02-security-context-constraints.md) | `restricted-v2` · non-root/random UID · `oc adm policy add-scc-to-user` · the SCC ladder | Run a **root-requiring** legacy image | ~30 min |
| 3 | [ServiceAccounts & Secrets](demo-03-serviceaccounts-secrets.md) | dedicated SA · `-z` role grants · Secret (base64≠encryption) · env vs mounted | **billing** DB creds + identity | ~30 min |

## Conventions

- Commands use **`oc`**. PV/PVC, StorageClass, ServiceAccount, Secret are pure `kubectl`
  (an **⎈** note flags this); **SCC** and `oc adm policy add-scc-to-user` are
  OpenShift-specific.
- **Podman-first images:** **`ubi9/httpd-24`** (rootless, HTTP on **8080**, doc-root
  `/var/www/html`; run its default command) is the well-behaved app; a stock
  root-requiring image is used to *demonstrate* an SCC denial. `ubi9/ubi-minimal` is the
  throwaway client.
- **Permissions.** A normal project user can do storage (PVC), ServiceAccounts, and
  Secrets **in their own project**. **Granting an SCC** to a ServiceAccount
  (`oc adm policy add-scc-to-user`) needs **cluster-admin** — that step (Demo 2) is
  instructor-led. Each demo marks which steps need admin.
- Replace placeholders (`<cluster-domain>`, `<your-password>`). **Never commit real
  secrets/keys** — all credential values are fictional placeholders.
- Each demo ends with a **Cleanup** section (delete the demo project).
- Companion material: the
  [concept guide](../../../guides/module-07-storage-security.md), the interactive
  [visualizations](../index.html), and the [exercises](../exercises/README.md).

## Pre-flight check (run once before Demo 1)

```bash
oc login https://api.<cluster-domain>:6443 -u <user> -p "$OCP_PASSWORD"   # or token
oc whoami
oc new-project mod7-demos --display-name="Module 7 Demos" 2>/dev/null || oc project mod7-demos
oc get storageclass          # note which is (default) — Demo 1 relies on a default class
```

> **Instructor tip:** keep the **web console** open — **Storage → PersistentVolumeClaims**
> and a pod's **Details → Annotations** (`openshift.io/scc`) mirror the CLI. Pre-check
> that a **default StorageClass** exists (Demo 1) and that you have a **cluster-admin**
> session available for the SCC grant (Demo 2). Pre-pull `ubi9/httpd-24` and
> `ubi9/ubi-minimal`.

---

> **◐ Partially verified (cluster asleep at authoring time).** `oc create secret|serviceaccount --help`,
> `oc set volume|serviceaccount --help`, and `oc adm policy add-scc-to-user --help` were
> run live with **oc 4.22** (client-side). Every command that needs a **live OpenShift
> cluster** (PVC binding, pod SCC assignment, secret/SA creation) is labelled
> **"requires a cluster — output is representative of OpenShift 4.18"**. These can be
> validated as **learner25** when the cluster is up (storage/SA/Secret steps run as a
> normal user; the SCC grant needs an admin) — the same way Module 6 was validated.
