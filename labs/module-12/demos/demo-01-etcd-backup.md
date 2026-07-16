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

**Live output** *(captured 2026-07-15 on the shared OCP 4.18.45 training cluster):*

```
NAME   VERSION   AVAILABLE   PROGRESSING   DEGRADED   SINCE   MESSAGE
etcd   4.18.45   True        False         False      11d

NAME                                         STATUS   ROLES                  AGE   VERSION
ip-10-0-23-236.ap-south-1.compute.internal   Ready    control-plane,master   11d   v1.31.14
ip-10-0-61-153.ap-south-1.compute.internal   Ready    control-plane,master   11d   v1.31.14
ip-10-0-93-108.ap-south-1.compute.internal   Ready    control-plane,master   11d   v1.31.14
```

> **Narrate:** `AVAILABLE=True, DEGRADED=False` is the green light from the **etcd Operator** —
> snapshot a healthy quorum, not a degraded one. Three masters = 3-member etcd (Module 11).
>
> **Gotcha:** on this AWS IPI cluster, master node names are **not** `master-0/1/2` — they're the
> EC2-derived hostnames above (`ip-10-0-...`). Don't hardcode a name; capture one:
> ```bash
> MASTER=$(oc get nodes -l node-role.kubernetes.io/master -o jsonpath='{.items[0].metadata.name}')
> ```

---

## Step 2 — Open a root shell on a master and take the snapshot

```bash
# capture a master node name, then open a privileged debug pod on it
MASTER=$(oc get nodes -l node-role.kubernetes.io/master -o jsonpath='{.items[0].metadata.name}')
oc debug node/$MASTER
# --- inside the debug pod ---
chroot /host
# run the backup script; it writes into the directory you name
sudo /usr/local/bin/cluster-backup.sh /home/core/etcd-backup
```

**Live output** *(captured 2026-07-15, real run on the training cluster):*

```
Temporary namespace openshift-debug-bwssw is created for debugging node...
Starting pod/ip-10-0-23-236ap-south-1computeinternal-debug-wnpt2 ...
To use host binaries, run `chroot /host`.
Certificate /etc/kubernetes/static-pod-certs/configmaps/etcd-all-bundles/server-ca-bundle.crt is missing. Checking in different directory
Certificate /etc/kubernetes/static-pod-resources/etcd-certs/configmaps/etcd-all-bundles/server-ca-bundle.crt found!
found latest kube-apiserver: /etc/kubernetes/static-pod-resources/kube-apiserver-pod-7
found latest kube-controller-manager: /etc/kubernetes/static-pod-resources/kube-controller-manager-pod-6
found latest kube-scheduler: /etc/kubernetes/static-pod-resources/kube-scheduler-pod-6
found latest etcd: /etc/kubernetes/static-pod-resources/etcd-pod-8
etcdctl version: 3.5.18
API version: 3.5
{"level":"info","ts":"2026-07-15T17:55:32Z","msg":"created temporary db file","path":"/home/core/etcd-backup/snapshot_2026-07-15_175526.db.part"}
{"level":"info","ts":"2026-07-15T17:55:32Z","msg":"fetching snapshot","endpoint":"https://10.0.23.236:2379"}
{"level":"info","ts":"2026-07-15T17:55:33Z","msg":"fetched snapshot","endpoint":"https://10.0.23.236:2379","size":"157 MB","took":"1 second ago"}
Snapshot saved at /home/core/etcd-backup/snapshot_2026-07-15_175526.db
{"level":"info","ts":"2026-07-15T17:55:33Z","msg":"saved","path":"/home/core/etcd-backup/snapshot_2026-07-15_175526.db"}
{"hash":544302140,"revision":1134361,"totalKey":13476,"totalSize":157089792}
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

**Live output** *(captured 2026-07-15, real run on the training cluster):*

```
total 150M
-rw-------. 1 root root 150M Jul 15 17:55 snapshot_2026-07-15_175526.db
-rw-------. 1 root root  81K Jul 15 17:55 static_kuberesources_2026-07-15_175526.tar.gz
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
oc debug node/$MASTER -- chroot /host tar czf - /home/core/etcd-backup > mobily-etcd-backup-$(date +%F).tgz
ls -lh mobily-etcd-backup-*.tgz
```

**Live output** *(captured 2026-07-15, real run on the training cluster):*

```
Starting pod/ip-10-0-23-236ap-south-1computeinternal-debug ...
Removing debug pod ...
-rw-r--r--  1 you  staff    42M Jul 15 23:36 mobily-etcd-backup-2026-07-15.tgz
```

> **Narrate:** This is the step teams skip and regret. A snapshot sitting only on the master it was
> taken on is worthless if you lose that node. Ship it off — object storage, another host, wherever
> your DR plan says. **Now** you have a real backup. (Gzip shrinks the 150 MB snapshot to ~42 MB
> here — etcd's b-tree pages compress well.)

---

## Step 5 — The restore plan (talk it through — do NOT run in the demo)

```bash
# On the chosen recovery master, ONLY when quorum is permanently lost:
#   sudo /usr/local/bin/cluster-restore.sh /home/core/etcd-backup
# then, cluster-wide: approve pending CSRs and revalidate operators
oc get csr | grep -i pending          # after a restore you'll typically have some
# oc adm certificate approve <csr>...
```

**Live output** *(captured 2026-07-15 — cluster is healthy, so no pending CSRs right now; expect some after an actual restore):*

```
No resources found
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
oc debug node/$MASTER -- chroot /host rm -rf /home/core/etcd-backup      # drill cleanup only
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

> **● Fully live-verified — 2026-07-15**, cluster-admin, on the shared **OCP 4.18.45** training
> cluster (3 masters, real AWS IPI hostnames). Every command through Step 4 was **run for real**:
> `oc get co etcd` / `oc get nodes -l node-role.kubernetes.io/master`, a live `oc debug node` +
> `cluster-backup.sh` snapshot (real 150 MB `.db` + 81K `static_kuberesources` tarball, real
> `etcdctl 3.5.18` log lines), the file listing, and the off-cluster `tar czf` copy (real 42 MB
> `.tgz`). All on-node/local artifacts from the drill were cleaned up. **Step 5 (`cluster-restore.sh`)
> was intentionally NOT run** — it's break-glass, rewinds the whole cluster, and must never be
> practised for the first time in production or on a shared training cluster; that step's commands
> are shown for narration only. Fixed a stale placeholder: master node names on this cluster are
> **not** `master-0/1/2` (real names are AWS-derived, e.g. `ip-10-0-23-236...`) — the steps now
> capture the name into `$MASTER` instead of hardcoding it.
