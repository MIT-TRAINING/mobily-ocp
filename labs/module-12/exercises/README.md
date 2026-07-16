# Module 12 — Exercises (Hands-On Practice)

These are **participant-driven** tasks. You drive **`oc`** plus the backup/troubleshooting/deploy
objects, then verify with the provided **validation** commands. Each exercise has a fully worked
**solution** — try the tasks first, then check.

Module 12 — **"Backup, Recovery, Troubleshooting and Capstone"** — covers **etcd backup/restore**
and node lifecycle, cluster/platform + application **troubleshooting**, and the **end-to-end
capstone** that integrates networking, storage, security, monitoring, and GitOps. Backup/restore
and node ops are **cluster-admin**; the capstone is mostly **project-user**.

## Where to run these

| Target | What you can do | Notes |
|--------|-----------------|-------|
| **Shared OpenShift 4.18 cluster** (preferred) | full capstone; observe backup files; troubleshoot real pods | `cluster-backup.sh`, node drain, etcd, `must-gather` need **cluster-admin** |
| **[Developer Sandbox](https://developers.redhat.com/developer-sandbox)** | build most of the capstone in your project | No cluster-admin → can't back up etcd or drain nodes |
| **Local (no cluster)** | `oc create --dry-run=client -o yaml` renders the capstone Secret/PVC/Route/Deployment offline | Manifest authoring is fully offline |

> **CLIs:** `oc` (+ the console). Manifest rendering with `oc create --dry-run=client -o yaml`
> needs **no cluster** — great for checking your capstone objects before applying.

## Exercises in this module

| # | Exercise | What you'll practice | Telecom scenario | Difficulty |
|---|----------|----------------------|------------------|------------|
| 1 | [Back up etcd & plan recovery](exercise-01-etcd-backup.md) | `cluster-backup.sh`, snapshot files, off-cluster copy, restore-vs-replace | snapshot before a **Mobily** change | ⭐ Beginner |
| 2 | [Diagnose a broken app](exercise-02-troubleshooting.md) | pod status → events → `logs --previous`, app vs. platform, `must-gather` | fix a crash-looping **subscriber-api** | ⭐⭐ Intermediate |
| 3 | [Capstone: end-to-end deploy](exercise-03-capstone.md) | Secret+PVC+Deploy+Service+Route+NetworkPolicy+monitoring+GitOps, then break & recover | ship the **self-care stack** | ⭐⭐⭐ Advanced (capstone) |

## Before you start

```bash
oc login https://api.<cluster-domain>:6443 -u <user> -p "$OCP_PASSWORD"   # or token
oc whoami
oc get clusteroperators etcd                          # etcd healthy before you snapshot it?
oc get nodes                                          # nodes Ready?
oc get csv -n openshift-gitops 2>/dev/null | grep -i gitops   # Argo CD present (for Ex 3 GitOps)?
oc new-project mobily-capstone 2>/dev/null || oc project mobily-capstone
```

- App image: **`ubi9/httpd-24`** (rootless, HTTP on **8080**) stands in for `subscriber-api`/
  `self-care`; a bare `GET /` → **403** proves connectivity. Database:
  **`quay.io/sclorg/postgresql-15-c9s`** (freely pullable; `POSTGRESQL_USER`/`_PASSWORD`/
  `_DATABASE` env). Instrument a real app for true `/metrics`.
- Replace placeholders (`<cluster-domain>`, `<your-password>`). **Never commit real
  tokens/passwords** — use `$OCP_PASSWORD` or a token file you supply. For a master node, capture
  the real name instead of guessing — real cluster hostnames aren't `master-0/1/2`:
  `MASTER=$(oc get nodes -l node-role.kubernetes.io/master -o jsonpath='{.items[0].metadata.name}')`.
- **Cluster-admin needed for:** `cluster-backup.sh`/`cluster-restore.sh`, `oc debug node`,
  `oc adm cordon/drain`, `oc delete node`, reading etcd/ClusterOperators, and `oc adm must-gather`.
  The capstone objects in your namespace and reading your own pods/logs are project-user actions.
- Cleanup: `oc delete project mobily-capstone`; remove any drill snapshot files and local dumps.

## How to self-assess

Each exercise's **Validation** section gives commands whose output confirms success.
`oc create --dry-run=client -o yaml` lets you check the capstone manifests **without a cluster**.
Stuck? The **Solution** walks one correct approach.

Companion material: the guided [demos](../demos/README.md), the interactive
[visualizations](../index.html), and the
[concept guide](../../../guides/module-12-backup-recovery-troubleshooting.md).

---

> **● Live-verified — 2026-07-16 (see each exercise's footer).** All three exercises were re-run
> against the shared **OCP 4.18.45** training cluster while it was up: Exercise 1's
> `cluster-backup.sh` snapshot, off-cluster copy, and cleanup all ran for real on a live master;
> Exercise 2's crash-loop/OOMKilled scenario was reproduced with real broken pods; Exercise 3's full
> stack (Secret/PVC/Deployments/Services/Route) was applied for real in a scratch project. Three
> real bugs were found and fixed in the process: this page's own pre-flight check
> (`grep -i argocd`, which never matches — the GitOps operator's CSV says "GitOps," not "argocd";
> now `grep -i gitops`), a stale `<master-0>` placeholder (real cluster node names are AWS-derived
> hostnames — replaced with a captured `$MASTER` variable), and Exercise 3's `awk` filter mismatch
> plus its Secret key names (`username`/`password` don't match what `oc set env --from=secret`
> produces or what the postgres image requires — must be `POSTGRESQL_USER`/`POSTGRESQL_PASSWORD`).
> All scratch namespaces created for validation were deleted afterward. Exercise 1's `restore` and
> Exercise 2's degraded-ClusterOperator example remain narrated/representative, since triggering
> those safely requires deliberately breaking a shared training cluster.
