# Demo 3 — Verify etcd Health & Performance

> **Scenario:** Before Mobily's platform team signs off on a maintenance window, they confirm
> the cluster's **brain** is sound: all etcd members healthy, **quorum** intact, and the
> **fsync/leader** performance signals in the green. We inspect etcd from the control plane
> with `etcdctl`, then read the same signals from Prometheus — the two views every operator
> should know.

| | |
|---|---|
| **Concepts reinforced** | etcd static pods · `etcdctl endpoint health/status` · quorum & leader · fsync/backend-commit latency · leader changes · DB size |
| **Maps to** | Guide §10–§11 · Visualization 03 · Exercise 3 |
| **Time** | ~25 minutes |
| **Cluster** | Shared OCP 4.18 — inspecting etcd (`oc rsh` into `openshift-etcd`) needs **admin** |

---

> **⎈ Kubernetes note:** etcd is the same key-value store behind *any* Kubernetes API server.
> OpenShift runs it as **static pods** on the masters and manages it with the **etcd
> Operator**; the `etcdctl` commands are standard etcd.

> ⚠️ **Inspecting etcd is cluster-admin.** The `openshift-etcd` namespace and the etcd client
> certs are admin-only. **Backup/restore is Module 12** — here we only *read* health.

## Talking points to open with

- etcd is the **single source of truth**; every `oc get` reads it. If etcd is sick, the whole
  API is sick.
- Health has **two** dimensions: **members/quorum** (are enough up?) and **performance** (is
  it fast enough?). A "healthy" etcd on a slow disk still degrades the API.
- **Quorum = majority.** 3 members tolerate 1 failure; lose 2 and the cluster freezes.

---

## Step 1 — See the etcd members (static pods on the masters)

```bash
oc -n openshift-etcd get pods -l app=etcd -o wide
oc get etcd cluster -o jsonpath='{.status.conditions[?(@.type=="EtcdMembersAvailable")].message}{"\n"}'
```

**Expected output** *(requires a cluster + admin — representative of OCP 4.18):*

```
NAME                   READY   STATUS    NODE
etcd-master-0          4/4     Running   master-0
etcd-master-1          4/4     Running   master-1
etcd-master-2          4/4     Running   master-2
3 members are available
```

> **Narrate:** Three etcd pods, one per master — that's the 3-member quorum group. The **etcd
> Operator** reports `EtcdMembersAvailable`. Odd count on purpose: 3 tolerates 1 failure at
> lower cost than 4 would.

---

## Step 2 — Check endpoint health (quorum view)

```bash
# exec into one etcd pod; etcdctl is preconfigured with the client certs inside:
oc -n openshift-etcd rsh etcd-master-0
# inside the pod:
etcdctl endpoint health --cluster -w table
```

**Expected output** *(requires a cluster + admin — representative):*

```
+------------------------------+--------+-------------+-------+
|           ENDPOINT           | HEALTH |    TOOK     | ERROR |
+------------------------------+--------+-------------+-------+
| https://10.0.0.10:2379       |  true  |  4.812ms    |       |
| https://10.0.0.11:2379       |  true  |  5.109ms    |       |
| https://10.0.0.12:2379       |  true  |  4.640ms    |       |
+------------------------------+--------+-------------+-------+
```

> **Narrate:** Every endpoint `true` and low `TOOK` = all members healthy and responsive. If
> one showed `false`, we'd still have **2 of 3 = quorum** and the cluster would keep serving;
> two `false` would mean **quorum lost** — a Module-12 disaster-recovery situation.

---

## Step 3 — Endpoint status (leader, DB size, raft term)

```bash
# still inside the etcd pod:
etcdctl endpoint status --cluster -w table
```

**Expected output** *(requires a cluster + admin — representative):*

```
+--------------------------+------------------+---------+---------+-----------+------------+
|         ENDPOINT         |        ID        | VERSION | DB SIZE | IS LEADER | RAFT TERM  |
+--------------------------+------------------+---------+---------+-----------+------------+
| https://10.0.0.10:2379   | 8e9e05c52164694d | 3.5.x   | 148 MB  |   true    |     12     |
| https://10.0.0.11:2379   | 91bc3c398fb3c146 | 3.5.x   | 148 MB  |   false   |     12     |
| https://10.0.0.12:2379   | fd422379fda50e48 | 3.5.x   | 149 MB  |   false   |     12     |
+--------------------------+------------------+---------+---------+-----------+------------+
exit                                     # leave the etcd pod
```

> **Narrate:** Exactly **one leader** (`IS LEADER true`) — the member that serializes all
> writes; the others are followers. All share the same **RAFT TERM** (no recent election
> churn) and a similar **DB SIZE** (in sync). A leader flapping term-to-term is a red flag.

---

## Step 4 — The same signals from Prometheus (Observe → Metrics)

```promql
# p99 fsync latency — the #1 etcd health signal (disk latency == etcd latency):
histogram_quantile(0.99, rate(etcd_disk_wal_fsync_duration_seconds_bucket[5m]))

# leader elections over the last hour (should be ~0):
increase(etcd_server_leader_changes_seen_total[1h])

# etcd DB size on disk (watch vs the 8 GiB default quota):
etcd_mvcc_db_total_size_in_bytes
```

**Expected result** *(requires a cluster — representative):*

```
{instance="10.0.0.10:2379"}   0.0043     # ~4.3ms p99 fsync — healthy (< ~10ms)
{instance="10.0.0.11:2379"}   0.0051
increase(...leader_changes...) 0          # no elections in the last hour
etcd_mvcc_db_total_size_in_bytes 1.55e8   # ~148 MB, well under quota
```

> **Narrate:** `etcd_disk_wal_fsync_duration_seconds` p99 under ~**10 ms** is the green zone —
> etcd commits nothing until fsync returns, so **disk latency *is* etcd latency**. Zero leader
> changes = a stable leader. OpenShift ships **`etcdHighFsyncDurations`** and
> **`etcdMembersDown`** alerts on exactly these, so you're paged before it's fatal.

---

## Step 5 — Built-in etcd dashboard

```bash
# Console: Observe → Dashboards → "etcd" — curated graphs of the metrics above.
# Confirm the etcd cluster operator is healthy from the CLI:
oc get clusteroperator etcd
```

**Expected output** *(requires a cluster — representative):*

```
NAME   VERSION   AVAILABLE   PROGRESSING   DEGRADED   SINCE
etcd   4.18.x    True        False         False      21d
```

> **Narrate:** `AVAILABLE=True, DEGRADED=False` from the **etcd cluster operator** is the
> one-line "brain is fine" check. The **Observe → Dashboards → etcd** view graphs fsync,
> leader changes, and DB size over time — the trend view you'd screenshot for a maintenance
> sign-off.

---

## Step 6 — Cleanup

```bash
# Read-only demo — nothing created. Just make sure you exited the etcd pod:
oc whoami                                   # back in your own shell, not the etcd rsh
echo "read-only demo — no cleanup needed"
```

---

## Wrap-up questions to pose

1. A 3-member etcd loses one member — is the cluster still writable? What about two?
2. What does `IS LEADER` show, and why is exactly one leader the healthy state?
3. Every member is "up" but the API is slow — which metric do you check first, and why?
4. Which two OpenShift alerts warn you about etcd trouble, and what does each catch?

---

> **◐ Partially verified:** `etcdctl`/`oc`/PromQL **syntax** follows the etcd 3.5 / oc 4.22
> reference, but every step **requires a live OpenShift cluster with cluster-admin** (the
> `openshift-etcd` namespace and etcd client certs are admin-only) and was not run at
> authoring (cluster asleep/unreachable). Output — endpoint tables, member IDs, latencies,
> DB sizes — is **representative of OpenShift 4.18 / etcd 3.5**; real values vary per cluster.
> Validate live as admin when the cluster is up. **Backup/restore is Module 12.**
