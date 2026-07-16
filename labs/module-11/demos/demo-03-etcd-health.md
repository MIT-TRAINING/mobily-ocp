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

**Verified output** *(live, `oc 4.22.0` against OCP 4.18.45):*

```
NAME                                               READY   STATUS    RESTARTS   AGE   IP            NODE
etcd-ip-10-0-23-236.ap-south-1.compute.internal   5/5     Running   45         10d   10.0.23.236   ip-10-0-23-236.ap-south-1.compute.internal
etcd-ip-10-0-61-153.ap-south-1.compute.internal   5/5     Running   45         10d   10.0.61.153   ip-10-0-61-153.ap-south-1.compute.internal
etcd-ip-10-0-93-108.ap-south-1.compute.internal   5/5     Running   45         10d   10.0.93.108   ip-10-0-93-108.ap-south-1.compute.internal
3 members are available
```

> **Narrate:** Three etcd pods, one per master — that's the 3-member quorum group. The **etcd
> Operator** reports `EtcdMembersAvailable`. Odd count on purpose: 3 tolerates 1 failure at
> lower cost than 4 would.
>
> Pod names here are the real AWS instance hostnames (`etcd-ip-10-0-...`), not the tidy
> `etcd-master-0/1/2` you might expect — that naming is cluster-specific (IPI on AWS derives
> node names from the instance), so expect different literal names on a different cluster; the
> shape (3 pods, one per master, `READY` counting containers in the static pod) is what
> transfers. `READY` is `5/5` here (etcd + etcdctl + etcd-metrics + etcd-readyz + setup
> containers on this build), not the `4/4` an older etcd Operator version reports — check the
> container count on your own cluster rather than assuming a fixed number.

---

## Step 2 — Check endpoint health (quorum view)

```bash
# exec straight into the etcdctl container of one etcd pod — it's preconfigured with the
# client certs, so no manual --cert/--key/--cacert flags are needed:
oc -n openshift-etcd exec etcd-ip-10-0-23-236.ap-south-1.compute.internal -c etcdctl -- \
  etcdctl endpoint health --cluster -w table
```

**Verified output** *(live, `oc 4.22.0` against OCP 4.18.45):*

```
+--------------------------+--------+-------------+-------+
|         ENDPOINT         | HEALTH |    TOOK     | ERROR |
+--------------------------+--------+-------------+-------+
| https://10.0.23.236:2379 |   true | 16.598781ms |       |
| https://10.0.61.153:2379 |   true | 21.567276ms |       |
| https://10.0.93.108:2379 |   true | 24.425999ms |       |
+--------------------------+--------+-------------+-------+
```

> **Narrate on the tool choice:** `oc exec -c etcdctl` runs the command directly instead of
> dropping into an interactive shell first — same result, easier to script/repeat. The pod has
> 5 containers (`etcdctl etcd etcd-metrics etcd-readyz etcd-rev`, matching the `5/5` from
> Step 1); a bare `oc rsh etcd-<node>` lands you in `etcd` (the pod's default container), so
> for interactive use you'd want `oc rsh -c etcdctl etcd-<node>` instead.

> **Narrate:** Every endpoint `true` and low `TOOK` = all members healthy and responsive. If
> one showed `false`, we'd still have **2 of 3 = quorum** and the cluster would keep serving;
> two `false` would mean **quorum lost** — a Module-12 disaster-recovery situation.

---

## Step 3 — Endpoint status (leader, DB size, raft term)

```bash
oc -n openshift-etcd exec etcd-ip-10-0-23-236.ap-south-1.compute.internal -c etcdctl -- \
  etcdctl endpoint status --cluster -w table
```

**Verified output** *(live, `oc 4.22.0` against OCP 4.18.45, etcd 3.5.18):*

```
+--------------------------+------------------+---------+---------+-----------+------------+-----------+------------+--------------------+--------+
|         ENDPOINT         |        ID        | VERSION | DB SIZE | IS LEADER | IS LEARNER | RAFT TERM | RAFT INDEX | RAFT APPLIED INDEX | ERRORS |
+--------------------------+------------------+---------+---------+-----------+------------+-----------+------------+--------------------+--------+
| https://10.0.93.108:2379 | 1b81f2b54b789f68 |  3.5.18 |  154 MB |     false |      false |        27 |    1285785 |            1285785 |        |
| https://10.0.23.236:2379 | 20cca90be2311bc6 |  3.5.18 |  154 MB |      true |      false |        27 |    1285786 |            1285786 |        |
| https://10.0.61.153:2379 | 4b1c94fe18d9a668 |  3.5.18 |  154 MB |     false |      false |        27 |    1285786 |            1285786 |        |
+--------------------------+------------------+---------+---------+-----------+------------+-----------+------------+--------------------+--------+
```

> **Narrate:** Exactly **one leader** (`IS LEADER true`) — the member that serializes all
> writes; the others are followers. All share the same **RAFT TERM** (no recent election
> churn) and near-identical **DB SIZE** (in sync). A leader flapping term-to-term is a red flag.
> Current etcd 3.5.x also reports **IS LEARNER** (a member still catching up, not yet a full
> voting member — relevant during member replacement) and the raft **INDEX**/**APPLIED INDEX**
> pair (equal here, meaning nothing is lagging behind the write log).

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

Run live via the `thanos-querier` route (the same backend the console's Observe → Metrics
uses) rather than pasting into the console, so the output below is scriptable:

```bash
TOKEN=$(oc whoami -t)
HOST=$(oc -n openshift-monitoring get route thanos-querier -o jsonpath='{.spec.host}')
curl -sk -H "Authorization: Bearer $TOKEN" \
  --data-urlencode 'query=histogram_quantile(0.99,rate(etcd_disk_wal_fsync_duration_seconds_bucket[5m]))' \
  "https://$HOST/api/v1/query"
```

**Verified result** *(live, queried via `thanos-querier` route against OCP 4.18.45; trimmed to
the `instance`/`value` fields):*

```
{instance="10.0.23.236:9979"}   0.004935   # ~4.9ms p99 fsync — healthy (< ~10ms)
{instance="10.0.61.153:9979"}   0.006058   # ~6.1ms
{instance="10.0.93.108:9979"}   0.004581   # ~4.6ms

increase(etcd_server_leader_changes_seen_total[1h])   0   # all 3 instances, no elections

etcd_mvcc_db_total_size_in_bytes:
  10.0.23.236:9979   155643904   # ~148 MiB
  10.0.61.153:9979   154001408   # ~147 MiB
  10.0.93.108:9979   155623424   # ~148 MiB, well under the 8 GiB default quota
```

> **Narrate:** `etcd_disk_wal_fsync_duration_seconds` p99 under ~**10 ms** is the green zone —
> etcd commits nothing until fsync returns, so **disk latency *is* etcd latency**. Zero leader
> changes = a stable leader. OpenShift ships **`etcdHighFsyncDurations`** and
> **`etcdMembersDown`** alerts on exactly these, so you're paged before it's fatal.
>
> Note the `instance` label here is `<node-ip>:9979` — the **etcd-metrics** sidecar's port,
> not the client port `2379` used in Steps 2–3. Same three members, different label because
> it's a different scrape target (metrics vs. client API).

---

## Step 5 — Built-in etcd dashboard

```bash
# Console: Observe → Dashboards → "etcd" — curated graphs of the metrics above.
# Confirm the etcd cluster operator is healthy from the CLI:
oc get clusteroperator etcd
```

**Verified output** *(live, `oc 4.22.0` against OCP 4.18.45):*

```
NAME   VERSION   AVAILABLE   PROGRESSING   DEGRADED   SINCE
etcd   4.18.45   True        False         False      11d
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

> **✅ Verified:** `oc 4.22.0` · OCP `4.18.45` / etcd `3.5.18` · cluster `mobily-ocp-training`
> · every command in Steps 1–5 was **run live as `kube:admin`** and the output above is real
> (endpoint tables, member IDs, latencies, DB sizes, PromQL results — nothing fabricated).
> Pod names, IPs, member IDs, latencies, and DB size are **this cluster's specific values** —
> expect the same shape (3 members, one leader, sub-10ms fsync) but different literal numbers
> on a different cluster. **Backup/restore is Module 12.**
