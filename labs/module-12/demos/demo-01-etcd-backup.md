# Demo 1 — Back Up etcd (and the Restore Plan)

> **Scenario:** Mobily's platform team is about to make a risky change (a cert rotation before an
> upgrade window). Before touching anything, they take an **etcd snapshot** — the one backup that
> can resurrect a dead control plane — and confirm they know the **restore-vs-replace** decision
> if it goes wrong. We take the snapshot on a healthy master, look at what it produced, and copy
> it off-cluster.

| | |
|---|---|
| **Concepts reinforced** | `cluster-backup.sh` · `oc debug node` + `chroot /host` · snapshot + static-resources files · off-cluster copy · restore vs. replace |
| **Maps to** | Guide §2–§4 · Visualization 01 · Exercise 1 |
| **Time** | ~25 minutes |
| **Cluster** | Shared OCP 4.18 — backup runs on a **master**; `oc debug node` + `cluster-backup.sh` are **cluster-admin** |

---

> **⎈ Kubernetes note:** the store being snapshotted is the same **etcd** behind any Kubernetes
> API server. OpenShift adds the on-master `cluster-backup.sh`/`cluster-restore.sh` scripts and
> the **etcd Operator** that manages membership; the underlying snapshot is standard `etcdctl`.

> ⚠️ **Backup/restore is cluster-admin and control-plane.** You run it from a **master's host
> shell** via `oc debug node`. Only *snapshot a healthy etcd* (Module 11: check `oc get co etcd`
> and endpoint health first) — a snapshot of a sick member is a sick snapshot.

## Talking points to open with

- etcd holds **every** cluster object; the snapshot is the difference between **restore** (an
  inconvenience) and **rebuild from scratch** (a catastrophe).
- Take snapshots **regularly and before risky changes** — the freshest snapshot loses the least
  (that gap is your **RPO**).
- A snapshot that only lives on the node you might lose is **not a backup** — copy it off.

---

## Step 1 — Confirm etcd is healthy *before* you snapshot it

```bash
oc get co etcd
oc get nodes -l node-role.kubernetes.io/master
```

**Expected output** *(requires a cluster + admin — representative of OCP 4.18):*

```
NAME   VERSION   AVAILABLE   PROGRESSING   DEGRADED   SINCE
etcd   4.18.x    True        False         False      21d

NAME       STATUS   ROLES                  AGE   VERSION
master-0   Ready    control-plane,master   34d   v1.31.x
master-1   Ready    control-plane,master   34d   v1.31.x
master-2   Ready    control-plane,master   34d   v1.31.x
```

> **Narrate:** `AVAILABLE=True, DEGRADED=False` is the green light from the **etcd Operator** —
> snapshot a healthy quorum, not a degraded one. Three masters = 3-member etcd (Module 11).

---

## Step 2 — Open a root shell on a master and take the snapshot

```bash
# open a privileged debug pod on a master, then step onto the host filesystem
oc debug node/<master-0>
# --- inside the debug pod ---
chroot /host
# run the backup script; it writes into the directory you name
sudo /usr/local/bin/cluster-backup.sh /home/core/etcd-backup
```

**Expected output** *(requires a cluster + admin — representative):*

```
Certificate /etc/kubernetes/static-pod-resources/.../etcd-serving.crt is missing. Checking in different directory
found latest kube-apiserver-pod: ...
found latest etcd-pod: ...
{"level":"info","msg":"created temporary db file","path":"/home/core/etcd-backup/snapshot_2026-07-08_020000.db.part"}
{"level":"info","msg":"fetching snapshot","endpoint":"https://10.0.0.10:2379"}
{"level":"info","msg":"saved","path":"/home/core/etcd-backup/snapshot_2026-07-08_020000.db"}
snapshot db and kube resources are successfully saved to /home/core/etcd-backup
```

> **Narrate:** `cluster-backup.sh` calls `etcdctl snapshot save` for a **consistent** point-in-time
> copy, *and* tars the static-pod resources needed to restore. Notice it runs from the **host**
> (`chroot /host`) — the same `oc debug node` entry point you'll use for node-level
> troubleshooting.

---

## Step 3 — Look at what the backup produced

```bash
# still on the host:
ls -lh /home/core/etcd-backup
```

**Expected output** *(requires a cluster + admin — representative):*

```
total 148M
-rw-------. 1 root root 148M Jul  8 02:00 snapshot_2026-07-08_020000.db
-rw-------. 1 root root  74K Jul  8 02:00 static_kuberesources_2026-07-08_020000.tar.gz
```

> **Narrate:** Two artifacts: the **`snapshot_*.db`** (the crown jewels — the entire cluster's
> object state) and **`static_kuberesources_*.tar.gz`** (the manifests/certs `cluster-restore.sh`
> needs). One consistent snapshot restores the **whole** cluster — you don't back up each master.

---

## Step 4 — Copy the snapshot OFF the cluster

```bash
# leave the host + debug pod
exit          # exits chroot
exit          # exits the debug pod

# copy the backup somewhere it survives losing this node
# (example: to your workstation via the debug pod, or push to object storage / another host)
oc debug node/<master-0> -- chroot /host tar czf - /home/core/etcd-backup > mobily-etcd-backup-$(date +%F).tgz
ls -lh mobily-etcd-backup-*.tgz
```

**Expected output** *(requires a cluster + admin — representative):*

```
Starting pod/master-0-debug ...
-rw-r--r--  1 you  staff   148M Jul  8 02:03 mobily-etcd-backup-2026-07-08.tgz
```

> **Narrate:** This is the step teams skip and regret. A snapshot sitting only on `master-0` is
> worthless if you lose `master-0`. Ship it off — object storage, another host, wherever your DR
> plan says. **Now** you have a real backup.

---

## Step 5 — The restore plan (talk it through — do NOT run in the demo)

```bash
# On the chosen recovery master, ONLY when quorum is permanently lost:
#   sudo /usr/local/bin/cluster-restore.sh /home/core/etcd-backup
# then, cluster-wide: approve pending CSRs and revalidate operators
oc get csr | grep -i pending          # after a restore you'll typically have some
# oc adm certificate approve <csr>...
```

> **Narrate — the single most important decision in this module:**
> - Lost **one** master (quorum 2/3 holds)? → **replace the etcd member**, do *not* restore.
> - Lost **quorum** (2+ masters, unrecoverable)? → **restore** on one master from this snapshot;
>   it **rewinds the whole cluster** to 02:00, then the others rejoin.
> - After a restore, expect **pending CSRs** to approve and an apiserver rollout to wait on —
>   exactly the stale-control-plane symptom from Module 11. Never *practise* restore for the first
>   time during a real outage.

---

## Step 6 — Cleanup

```bash
# The demo only created snapshot files + one local tarball. Remove the on-node copy if this was
# a drill (keep real backups!):
oc debug node/<master-0> -- chroot /host rm -rf /home/core/etcd-backup   # drill cleanup only
rm -f mobily-etcd-backup-*.tgz                                            # local drill tarball
oc whoami                                                                 # back in your own shell
```

---

## Wrap-up questions to pose

1. Why must etcd be **healthy** before you snapshot it — what's wrong with a snapshot of a
   degraded member?
2. You lose **one** master of three. Restore or replace? What if you lose **two**?
3. What does an etcd snapshot **not** contain that your `subscriber-db` absolutely needs?
4. Your last snapshot was 6 hours ago and disaster strikes now. What have you lost, and what's
   the name for that gap?

---

> **◐ Partially verified:** `oc`/`cluster-backup.sh`/`oc debug node` **syntax** follows the OCP
> 4.18 / oc 4.22 references, but every step **requires a live OpenShift cluster with
> cluster-admin** and a control-plane host shell, and was not run at authoring (cluster
> asleep/unreachable). Output — operator table, backup-script log, file listing, sizes — is
> **representative of OpenShift 4.18 / etcd 3.5**; real values vary per cluster. Validate live as
> admin when the cluster is up. **Restore (`cluster-restore.sh`) is break-glass — practise it in a
> throwaway cluster, never first in production.**
