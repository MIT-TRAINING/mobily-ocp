# Exercise 1 — Back Up etcd & Plan Recovery

> **Scenario:** Before Mobily's platform team runs a risky cert rotation, they must have a fresh
> **etcd snapshot** and a clear recovery plan. You'll verify etcd is healthy, take a snapshot with
> `cluster-backup.sh`, confirm what it produced, copy it off-cluster, and articulate the
> **restore-vs-replace** decision.

| | |
|---|---|
| **Practice** | `oc get co etcd` · `oc debug node` + `chroot /host` · `cluster-backup.sh` · snapshot files · off-cluster copy · restore vs. replace |
| **Maps to** | Guide §2–§4 · Visualization 01 · Demo 1 |
| **Difficulty** | ⭐ Beginner · ~20 min · needs cluster-admin + a control-plane host shell |

> ⚠️ `cluster-backup.sh` and `oc debug node` are **cluster-admin, control-plane** actions — pair
> with your instructor. **Do not** run `cluster-restore.sh` on the shared cluster; you'll only
> *describe* the restore path.

---

## Tasks

1. Confirm etcd is healthy **before** snapshotting — the etcd ClusterOperator `Available=True,
   Degraded=False`, and all three masters `Ready`. (Why does a snapshot of a degraded member help
   no one?)
2. Open a root host shell on a master (`oc debug node/<master>` → `chroot /host`) and run
   `cluster-backup.sh` into a directory you choose.
3. List the backup directory. Identify the **two** artifacts it produced and say what each is for.
4. Copy the snapshot **off** the cluster (to your workstation or object storage). Explain why a
   snapshot left only on that master isn't a backup.
5. **On paper:** for (a) one master lost, (b) two masters lost — state whether you *replace* or
   *restore*, and what a restore costs you.

> **Hint (Task 1):** `oc get co etcd` and `oc get nodes -l node-role.kubernetes.io/master`.

> **Hint (Task 2):** don't hardcode a master name — on a real (e.g. AWS IPI) cluster, master
> hostnames aren't `master-0/1/2`. Capture one first:
> `MASTER=$(oc get nodes -l node-role.kubernetes.io/master -o jsonpath='{.items[0].metadata.name}')`,
> then `oc debug node/$MASTER`.

> **Hint (Task 5):** quorum of 3 = 2. Holds with 1 down (replace); lost with 2 down (restore =
> whole-cluster rewind to the snapshot).

---

## Validation

```bash
# 1. etcd healthy:
oc get co etcd                                    # AVAILABLE=True DEGRADED=False

# 2-3. after the backup (on the master host, via oc debug node):
#   sudo /usr/local/bin/cluster-backup.sh /home/core/etcd-backup
#   ls -lh /home/core/etcd-backup                 # snapshot_*.db + static_kuberesources_*.tar.gz

# 4. off-cluster copy exists:
ls -lh mobily-etcd-backup-*.tgz
```

Expected: `etcd` operator healthy; the backup dir contains **`snapshot_<ts>.db`** and
**`static_kuberesources_<ts>.tar.gz`**; a local tarball of the backup exists off the master.

---

## Reflection

- Why must etcd be healthy *before* the snapshot — what's a "sick snapshot"?
- Your last snapshot is 6 hours old when disaster hits. What have you lost, and what's that gap
  called (RPO)? How would you shrink it?
- An etcd snapshot restores the **PVC object** for `subscriber-db`. Does it restore the database's
  **data**? What protects that?

---

<details>
<summary><strong>✅ Solution</strong> (try the tasks first — needs cluster-admin)</summary>

```bash
# 1. Health gate — snapshot a healthy quorum only
oc get co etcd                                    # AVAILABLE=True, DEGRADED=False
oc get nodes -l node-role.kubernetes.io/master    # 3x Ready

# 2. Take the snapshot from a master's host shell — capture the name, don't hardcode it
MASTER=$(oc get nodes -l node-role.kubernetes.io/master -o jsonpath='{.items[0].metadata.name}')
oc debug node/$MASTER
chroot /host
sudo /usr/local/bin/cluster-backup.sh /home/core/etcd-backup

# 3. Two artifacts
ls -lh /home/core/etcd-backup
#   snapshot_<ts>.db                 -> the etcd point-in-time snapshot (all cluster objects)
#   static_kuberesources_<ts>.tar.gz -> static-pod manifests/certs cluster-restore.sh needs
exit    # chroot
exit    # debug pod

# 4. Copy it OFF the cluster
oc debug node/$MASTER -- chroot /host tar czf - /home/core/etcd-backup \
  > mobily-etcd-backup-$(date +%F).tgz
ls -lh mobily-etcd-backup-*.tgz

# 5. Recovery decision (paper):
#    (a) 1 master lost  -> quorum 2/3 HOLDS -> REPLACE the etcd member (no rewind, no data loss)
#    (b) 2 masters lost -> quorum LOST      -> RESTORE on one master from this snapshot
#        (rewinds the WHOLE cluster to the snapshot; then approve CSRs, revalidate operators)
```

**Live output** *(captured 2026-07-16, real run on the OCP 4.18.45 training cluster):*

```
NAME   VERSION   AVAILABLE   PROGRESSING   DEGRADED   SINCE   MESSAGE
etcd   4.18.45   True        False         False      11d

NAME                                         STATUS   ROLES                  AGE   VERSION
ip-10-0-23-236.ap-south-1.compute.internal   Ready    control-plane,master   11d   v1.31.14
ip-10-0-61-153.ap-south-1.compute.internal   Ready    control-plane,master   11d   v1.31.14
ip-10-0-93-108.ap-south-1.compute.internal   Ready    control-plane,master   11d   v1.31.14

# ls -lh /home/core/etcd-backup
total 174M
-rw-------. 1 root root 174M Jul 16 02:23 snapshot_2026-07-16_022314.db
-rw-------. 1 root root  81K Jul 16 02:23 static_kuberesources_2026-07-16_022314.tar.gz

# off-cluster copy
-rw-r--r--  1 saravana  wheel    48M Jul 16 07:53 mobily-etcd-backup-2026-07-16.tgz
```

**Why:** etcd is the cluster's only source of truth, so the snapshot is the difference between a
*restore* and a *rebuild from scratch*. You snapshot only a **healthy** member (a degraded one
gives an inconsistent/incomplete snapshot), take them **regularly + before risky changes** (fresh
snapshot = small **RPO**), and **copy them off** the node you might lose. Restore is **break-glass**
— only when quorum is permanently gone — and it **rewinds the whole cluster**; for a single failed
master you *replace the member* instead. The snapshot restores the *PVC object* but **not** the PV's
data bytes — that needs PV snapshots / OADP.
</details>

---

> **● Live-verified — 2026-07-16**, cluster-admin, on the shared **OCP 4.18.45** training cluster
> (3 masters, real AWS IPI hostnames). Tasks 1–4 and their solution commands were **run for real**:
> a live `cluster-backup.sh` snapshot (real 174 MB `.db` + 81K `static_kuberesources` tarball), the
> file listing, and the off-cluster `tar czf` copy (real 48 MB `.tgz`). The drill snapshot and
> local tarball were cleaned up afterward. Fixed a stale placeholder: master node names on this
> cluster are **not** `master-0/1/2` (real names are AWS-derived, e.g. `ip-10-0-23-236...`) — the
> solution now captures the name into `$MASTER` instead of hardcoding it. **`cluster-restore.sh`
> was intentionally not run** — it's break-glass and must never be practised for the first time on
> a shared cluster; Task 5 stays a paper exercise.
