# Exercise 3 — Incident Triage (Capstone)

> **Scenario:** At 02:40, Alertmanager pages: **SubscriberAPIHighErrorRate** is Firing.
> Mobily customers can't look up balances. You have three tools — **metrics**, **logs**, and
> **etcd health** — and one job: find the root cause fast, and prove it wasn't the platform.
> This capstone runs the full Module-11 loop end to end: **alert → metrics → logs → rule out
> etcd**.

| | |
|---|---|
| **Practice** | read a firing alert · confirm/quantify with PromQL · pivot to logs (LogQL) · rule etcd in/out (`etcdctl` + metrics) · write the incident summary |
| **Maps to** | Guide §5, §9, §11, §12 · Visualizations 01–03 · Demos 1–3 |
| **Difficulty** | ⭐⭐⭐ Advanced (capstone) · ~35 min · needs monitoring + logging; etcd checks need admin |

> ⚠️ Reading alerts/metrics/your logs is a project-user action; inspecting **etcd**
> (`oc rsh` into `openshift-etcd`) is **cluster-admin** — pair with your instructor for Task 4.

---

## Tasks

1. **Alert.** In **Observe → Alerting**, open the firing `SubscriberAPIHighErrorRate`. Record
   its `severity`, when it started, and the exact `expr`.
2. **Metrics.** In **Observe → Metrics**, quantify it: what is the current 5xx **ratio**, and
   what is the raw 5xx **rate**? Graph it — when did it start climbing?
3. **Logs.** Pivot to logs. Find `subscriber-api`'s errors, read the message, then follow it
   **downstream** to whatever it's failing to reach. Identify the actually-broken component.
4. **Rule out etcd.** Prove the platform's brain is healthy so you can say "this is an app
   problem, not a cluster problem": check members/quorum and the fsync signal.
5. **Summarise.** Write a 3-line incident note: **symptom → root cause → fix**, naming every
   layer the diagnosis passed through.

> **Hint (Task 3):** the `subscriber-api` error line names a host and port — search that
> component's own logs next.

> **Hint (Task 4):** all endpoints `healthy` + p99 fsync in the green = etcd is not your
> problem.

---

## Validation

```bash
# 2. metrics (Observe → Metrics):
#   sum(rate(http_requests_total{job="subscriber-api",code=~"5.."}[5m])) / sum(rate(http_requests_total{job="subscriber-api"}[5m]))
# 3. logs (Observe → Logs):
#   { kubernetes_namespace_name="mobily-apps", kubernetes_container_name="subscriber-api" } |= "ERROR"
#   { kubernetes_namespace_name="mobily-apps", kubernetes_container_name="subscriber-db" }
# 4. etcd (admin):
oc get clusteroperator etcd
oc -n openshift-etcd rsh etcd-master-0 etcdctl endpoint health --cluster
```

Expected: 5xx ratio well above 0.05; `subscriber-api` logs show `connection refused:
subscriber-db`; `subscriber-db` logs show `OOMKilled`; etcd all healthy → **not** the platform.

---

## Reflection

- Metrics told you *that* and *roughly where*; logs told you *why*. Point to the exact command
  that gave each.
- Why bother ruling out etcd at all — what would have been different in the signals if etcd
  *had* been the cause?
- The alert's `for: 10m` meant you were paged 10 minutes after it started. Trade-off: what
  breaks if you set it to `0m`? What breaks if you set it to `1h`?

---

<details>
<summary><strong>✅ Solution</strong> (try the tasks first — Task 4 needs admin)</summary>

```bash
# 1. Alert (Observe → Alerting): SubscriberAPIHighErrorRate, severity=warning,
#    expr = 5xx ratio > 0.05, for 10m. Started ~02:30.

# 2. Quantify with PromQL (Observe → Metrics):
#    sum(rate(http_requests_total{job="subscriber-api",code=~"5.."}[5m]))
#      / sum(rate(http_requests_total{job="subscriber-api"}[5m]))
#    → ~0.12 (12%) — well over the 5% threshold; graph shows onset ~02:30.

# 3. Pivot to logs (Observe → Logs):
#    { kubernetes_namespace_name="mobily-apps", kubernetes_container_name="subscriber-api" } |= "ERROR"
#      → GET /subscribers/... 500 connection refused: subscriber-db:5432
#    follow it downstream:
#    { kubernetes_namespace_name="mobily-apps", kubernetes_container_name="subscriber-db" }
#      → FATAL: out of memory — OOMKilled, restarting
oc get pods -n mobily-apps -l app=subscriber-db      # RESTARTS climbing, last state OOMKilled
oc describe pod -n mobily-apps -l app=subscriber-db | grep -A3 'Last State'

# 4. Rule out etcd (admin):
oc get clusteroperator etcd                          # AVAILABLE=True DEGRADED=False
oc -n openshift-etcd rsh etcd-master-0 etcdctl endpoint health --cluster   # all healthy
#    (and Observe → Metrics: etcd p99 fsync < ~10ms, 0 leader changes)

# 5. Fix: raise subscriber-db's memory limit (or fix the leak); the DB stops
#    OOMKilling, subscriber-api's calls succeed, the alert resolves.
oc set resources deploy/subscriber-db -n mobily-apps --limits=memory=512Mi
```

**Representative output** *(requires a cluster — OCP 4.18):*

```
# metrics: 0.12
# subscriber-api log:  500 connection refused: subscriber-db:5432
# subscriber-db log:   FATAL: out of memory — OOMKilled, restarting
etcd   4.18.x   True   False   False   21d
+------------------------+--------+---------+-------+
| ...:2379               |  true  | 4.8ms   |       |   (x3, all healthy)
```

**Incident note (Task 5):**
> **Symptom:** subscriber-api 5xx ratio 12% (alert fired 02:40, onset 02:30).
> **Root cause:** subscriber-db OOMKilled repeatedly → connections refused → api 5xx.
> **Fix:** raised subscriber-db memory limit; ruled out etcd (all members healthy, fsync
> green) — this was an **application** fault, not a platform fault.

**Why this is the whole module:** you **alerted on a metric**, **quantified it in Metrics**,
**diagnosed the *why* in logs** by following the dependency chain, and **ruled etcd in/out** so
you could confidently say "app, not platform." Metrics find *that/where*; logs find *why*; etcd
health tells you whether the brain is the problem.
</details>

---

> **◐ Partially verified:** PromQL/LogQL/`etcdctl`/`oc` **syntax** follows the OCP 4.18 / oc
> 4.22 references; every step **requires a live cluster** (Task 4 needs cluster-admin) and was
> not run at authoring (cluster asleep/unreachable). Output — ratios, log lines, etcd tables —
> is **representative of OpenShift 4.18**; real values vary per cluster. Validate live when the
> cluster is up (alerts/metrics/logs as a project user; etcd inspection as admin).
