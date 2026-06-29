# Module 5 — Guided Demos (Instructor-Led)

These are **instructor-led, narrated walkthroughs**. The instructor runs each step
live against the real **OpenShift 4.18** cluster while explaining *what* each
administrative action does and *why*. Participants watch and follow along, then
practice in the [`../exercises`](../exercises).

Module 5 — **"OpenShift Installation and Cluster Administration"** — is the
administrator's module: verifying **cluster health**, changing nodes safely with the
**Machine Config Operator**, running the **upgrade lifecycle**, and managing
**Projects, users, groups and RBAC**. Commands are **`oc`**, and most are **`oc adm`**
(administrator) verbs — many need **cluster-admin**.

All scenarios use a **telecom domain** framing (CDR pipeline, subscriber-api,
`team-billing`/`team-crm` tenants) so the actions land in context. Data and users are
fictional.

## Demos in this module

| # | Demo | Concepts reinforced | Telecom scenario | Time |
|---|------|---------------------|------------------|------|
| 1 | [Verify cluster health](demo-01-cluster-health-check.md) | `clusterversion` · `co` · `nodes` (topology) · `describe` · events · `must-gather` | Pre-release **platform health check** | ~25 min |
| 2 | [MachineConfig & pools](demo-02-machineconfig-and-pools.md) | `MachineConfig` · `MachineConfigPool` · MCO rollout · `maxUnavailable` · pause | Add a **corporate CA** to workers | ~30 min |
| 3 | [Lifecycle & upgrade](demo-03-lifecycle-upgrade.md) | channels · `oc adm upgrade` · CVO walk · drained reboots · verify | Patch to **4.18.21** with no downtime | ~25 min |
| 4 | [Projects, users & RBAC](demo-04-projects-users-rbac.md) | `new-project` · quota/limit · users/groups · `oc adm policy` · `can-i` | Onboard **team-billing** | ~30 min |

## Conventions

- Commands use **`oc`** — mostly **`oc adm`** admin verbs that `kubectl` lacks. Where a
  command *is* standard Kubernetes, an **⎈** note says so.
- **Permissions matter.** Health *reads* work for a cluster-reader, but applying a
  MachineConfig (Demo 2), running an upgrade (Demo 3), and creating users/groups/RBAC
  (Demo 4) need **cluster-admin**. On the **Developer Sandbox** participants can't do
  cluster-scope actions — they follow the instructor's screen. **Demo 3 (upgrade)** is
  *demonstrated/dry-run only* — never upgrade a shared class cluster mid-course.
- Replace placeholders (`<node>`, `<cluster-domain>`) with real values. **Never type or
  commit real tokens/passwords** — use the console *Copy login command* token or
  `$OCP_PASSWORD`. Secret/htpasswd values are fictional placeholders.
- Each demo ends with a **Cleanup** section (Demo 4 creates a tenant to delete; Demos
  1–3 are read/dry-run).
- Companion material: the
  [concept guide](../../../guides/module-05-installation-cluster-administration.md), the
  interactive [visualizations](../index.html), and the
  [exercises](../exercises/README.md).

## Pre-flight check (run once before Demo 1)

```bash
oc login https://api.<cluster-domain>:6443 -u <user> -p "$OCP_PASSWORD"   # or token
oc whoami                       # confirm identity
oc auth can-i '*' '*' --all-namespaces   # 'yes' => cluster-admin (needed for Demos 2-4)
```

> **Instructor tip:** keep the **web console** open beside the terminal — Module 5 lands
> when participants see the *same fact* in both (e.g. `oc get mcp` next to **Compute →
> MachineConfigPools**, or `oc adm upgrade` next to **Administration → Cluster
> Settings**). For Demo 3, use `oc adm upgrade` (report-only) and the console's update
> screen; do **not** trigger a real upgrade on the class cluster.

---

> **◐ Partially verified.** `oc` **client-side** help (`oc adm policy --help`,
> `oc create role --help`, etc.) was run live with **oc 4.22**. Every command that needs
> a **live OpenShift cluster** (health reads, MCO, upgrade, RBAC actions) is labelled
> **"requires a cluster — output is representative of OpenShift 4.18"** and demo footers
> say **◐ Partially verified**. No cluster-dependent output is presented as
> independently verified — run it live to capture your own.
</content>
