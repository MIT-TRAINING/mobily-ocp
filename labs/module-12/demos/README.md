# Module 12 — Demos (Instructor-Led)

These are **narrated, instructor-driven** walkthroughs of OpenShift's day-2 survival skills:
**etcd backup & recovery**, a repeatable **troubleshooting methodology**, and the **end-to-end
capstone** that ties the whole course together. Each demo is a scenario with copy-paste `oc`
commands, expected output, and talking points that connect what's on screen to the concepts in
the [guide](../../../guides/module-12-backup-recovery-troubleshooting.md).

Module 12 — **"Backup, Recovery, Troubleshooting and Capstone"** — covers **etcd backup/restore**
and node lifecycle, cluster/platform + application **troubleshooting**, and a **capstone** deploy
integrating networking, storage, security, monitoring, and GitOps.

## Demos in this module

| # | Demo | Concepts | Telecom scenario | Time |
|---|------|----------|------------------|------|
| 1 | [Back up etcd (and the restore plan)](demo-01-etcd-backup.md) | `cluster-backup.sh` · `oc debug node` · snapshot files · restore/replace decision | snapshot before a risky **Mobily** change | ~25 min |
| 2 | [The troubleshooting loop](demo-02-troubleshooting.md) | pod status → events → logs · `oc get co` · `oc debug` · `must-gather` | diagnose a broken **subscriber-api** | ~30 min |
| 3 | [Capstone — end-to-end deploy](demo-03-capstone-deploy.md) | Secret · PVC · Deployment · Service · Route · NetworkPolicy · Argo CD | stand up the **self-care stack** | ~35 min |

## Conventions

- **`oc`-first** (this is OpenShift). `kubectl` equivalents are noted where they reinforce
  Kubernetes fundamentals; backup/restore, node ops, and etcd are OpenShift/host-level.
- **What needs cluster-admin:** `cluster-backup.sh` / `cluster-restore.sh`, `oc debug node`,
  `oc adm cordon/drain`, `oc delete node`, reading ClusterOperators/etcd, and `oc adm
  must-gather`. The **capstone** (Secret/PVC/Deployment/Service/Route/NetworkPolicy in your own
  project, and an Argo CD Application) is a **project-user** action once the platform is healthy.
- **Manifest rendering with `oc create --dry-run=client -o yaml` needs no cluster** — several
  capstone objects below are shown as **real offline renders** (verified with oc 4.22).
- **Master node names are captured, not hardcoded** — `$MASTER=$(oc get nodes -l
  node-role.kubernetes.io/master -o jsonpath='{.items[0].metadata.name}')`, since real cluster
  node names are AWS-derived hostnames, not `master-0/1/2`.
- **Secrets are placeholders** (`<cluster-domain>`, `$OCP_PASSWORD`, `<your-password>`) — never
  commit real tokens, kubeconfig, or passwords.
- **Cleanup** is included at the end of every demo (the backup demo is read-only apart from the
  snapshot files it writes).

## Pre-flight check

```bash
oc whoami                                   # confirm you're logged in
oc get clusteroperators | head             # platform self-report (admin view)
oc get nodes                                # nodes Ready?
oc get co etcd                              # etcd healthy before you snapshot it (Module 11)
oc create -f /dev/stdin --dry-run=client -o yaml <<<'apiVersion: v1
kind: PersistentVolumeClaim
metadata: {name: t}
spec: {accessModes: [ReadWriteOnce], resources: {requests: {storage: 1Gi}}}' >/dev/null && echo "dry-run render OK (no cluster needed)"
```

Companion material: the interactive [visualizations](../index.html), the hands-on
[exercises](../exercises/README.md), and the
[concept guide](../../../guides/module-12-backup-recovery-troubleshooting.md).

---

> **● Live-verified — 2026-07-15 (see each demo's footer).** All three demos were re-run against the
> shared **OCP 4.18.45** training cluster while it was up: Demo 1's `cluster-backup.sh` snapshot,
> off-cluster copy, and cleanup all ran for real on a live master; Demo 2's crash-loop/OOMKilled
> chain was reproduced with a real broken `subscriber-db`/`subscriber-api` pair and fixed for real,
> and `must-gather` was run for real (surfacing a genuine stall on the performance-profile
> collector — documented in Demo 2); Demo 3's Secret/PVC/Deployment/Route manifests were rendered
> **and applied** in a real scratch project (surfacing two real behaviors — PVC
> `WaitForFirstConsumer` binding and Route label inheritance — documented in Demo 3). Two real bugs
> were fixed in the process: Demo 2's `oc get co` `awk` filter was matching the wrong column, and
> master-node placeholders (`<master-0>`) were replaced with a captured `$MASTER` variable since
> this cluster's real node names are AWS-derived hostnames, not `master-0/1/2`. Demo 1's
> **restore** (`cluster-restore.sh`) and Demo 2's **degraded-ClusterOperator** example remain
> narrated/representative — not run — because both require deliberately breaking a shared
> training cluster, which isn't safe to demo live. All scratch namespaces created for validation
> (`mobily-apps`, `mobily-capstone`) were deleted afterward.
