# Module 5 — Exercises (Hands-On Practice)

These are **participant-driven** tasks. You drive the **`oc`** CLI on the shared
**OpenShift 4.18** cluster, then verify with the provided **validation** commands. Each
exercise has a fully worked **solution** — try the tasks first, then check.

Module 5 — **"OpenShift Installation and Cluster Administration"** — is the
administrator's module: verify **cluster health**, change nodes with the **Machine
Config Operator**, understand the **upgrade lifecycle**, and manage **Projects, users,
and RBAC**. Several tasks need **cluster-admin**; each marks what it requires.

## Where to run these

| Target | What you can do | Notes |
|---|---|---|
| **Shared OpenShift 4.18 cluster** (preferred) | Health reads; MCO/upgrade/RBAC if admin | You may be **non-admin** — admin-only steps are marked, do them with the instructor |
| **[Developer Sandbox](https://developers.redhat.com/developer-sandbox)** (fallback) | Project-scoped RBAC reasoning, `can-i` | **not** cluster-admin → no node/MCO/upgrade/group actions; follow the instructor |

> **`oc adm` = admin verbs.** Much of this module uses `oc adm …`, which `kubectl` does
> not have. Standard reads (`get`, `describe`, `auth can-i`) are pure `kubectl`/`oc`.

## Exercises in this module

| # | Exercise | What you'll practice | Telecom scenario | Difficulty |
|---|----------|----------------------|------------------|------------|
| 1 | [Verify cluster health](exercise-01-verify-cluster-health.md) | `clusterversion`/`co`/`nodes` · topology · triage reads | Pre-release **health gate** | ⭐ Beginner |
| 2 | [Explore MachineConfig & pools](exercise-02-explore-machineconfig-pools.md) | `mcp`/`machineconfig` · rendered config · (admin) apply | Worker **node config** | ⭐⭐ Intermediate |
| 3 | [Lifecycle & channels](exercise-03-lifecycle-and-channels.md) | `oc adm upgrade` (report) · channels · pre/post gates | Plan the **4.18.21 patch** | ⭐⭐ Intermediate |
| 4 | [Multi-tenant + RBAC capstone](exercise-04-multitenant-rbac-capstone.md) | Project + quota + LimitRange + group + RBAC + `can-i` | Onboard **team-crm** | ⭐⭐⭐ Advanced |

## Before you start

```bash
oc login https://api.<cluster-domain>:6443 -u <user> -p "$OCP_PASSWORD"   # or token
oc whoami
oc auth can-i '*' '*' --all-namespaces      # 'yes' => cluster-admin (needed for Ex 2 apply, Ex 4)
```

- Replace placeholders (`<cluster-domain>`, `<node>`, `<mcp>`) with your own values.
  **Never commit real tokens/passwords**; htpasswd/Secret values are fictional.
- **Admin-only** steps are clearly flagged. If you're not admin, do the **read/`can-i`**
  parts and watch the instructor for the rest — the *reasoning* is what's assessed.
- Cleanup is per-exercise (Ex 4 creates a tenant to delete). Read-only exercises need
  none.

## How to self-assess

Each exercise's **Validation** section gives commands whose output confirms success. If
your output matches the *shape* shown, you've completed the task. Stuck? The
**Solution** walks one correct approach.

Companion material: the guided [demos](../demos/README.md), the interactive
[visualizations](../index.html), and the
[concept guide](../../../guides/module-05-installation-cluster-administration.md).

---

> **◐ Partially verified.** `oc` **client-side** help (`oc adm policy --help`,
> `oc create role --help`, …) was run live with **oc 4.22**. Commands that need a **live
> OpenShift cluster** (health reads, MCO, upgrade, RBAC actions) are labelled
> **"requires a cluster — output is representative of OpenShift 4.18"**; run them on the
> shared cluster/Sandbox for your own values. No cluster-dependent output is presented as
> independently verified.
</content>
