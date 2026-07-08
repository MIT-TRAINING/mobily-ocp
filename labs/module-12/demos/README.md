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
- **Secrets are placeholders** (`<master-0>`, `<cluster-domain>`, `$OCP_PASSWORD`,
  `<your-password>`) — never commit real tokens, kubeconfig, or passwords.
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

> **◐ Partially verified (see each demo's footer).** Manifest-rendering steps
> (`oc create --dry-run=client -o yaml` for the capstone's **PVC / Secret / Route / Deployment**)
> were **run live offline with oc 4.22** — real output. Steps needing a **live cluster**
> (`cluster-backup.sh` output, broken-pod events, node drain, Argo CD sync) are **representative
> of OpenShift 4.18** and should be validated when the cluster is up (backup/restore, node ops,
> etcd, and `must-gather` as admin; the capstone objects as a project user).
