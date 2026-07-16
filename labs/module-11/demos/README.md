# Module 11 — Demos (Instructor-Led)

These are **narrated, instructor-driven** walkthroughs of OpenShift's day-2 observability:
**monitoring & alerting**, **logging**, and **etcd health**. Each demo is a scenario with
copy-paste `oc` commands, expected output, and talking points that connect what's on screen
to the concepts in the [guide](../../../guides/module-11-monitoring-logging-etcd.md).

Module 11 — **"Monitoring, Logging and etcd Administration"** — covers the built-in
**monitoring** stack (Prometheus, Alertmanager, dashboards), the **logging** pipeline (Vector
→ LokiStack → LogQL), and **etcd** architecture, health, and performance.

## Demos in this module

| # | Demo | Concepts | Telecom scenario | Time |
|---|------|----------|------------------|------|
| 1 | [Dashboards & a custom alert](demo-01-monitoring-alert.md) | Observe views · ServiceMonitor · PrometheusRule · Alertmanager | alert on **subscriber-api** 5xx rate | ~30 min |
| 2 | [Query & filter platform logs](demo-02-logging-query.md) | LokiStack · LogQL selector + filters · `oc logs` · log types | trace a **self-care** topup failure | ~25 min |
| 3 | [Verify etcd health & performance](demo-03-etcd-health.md) | etcdctl endpoint health/status · quorum · fsync/leader metrics | confirm the **control-plane brain** is sound | ~25 min |

## Conventions

- **`oc`-first** (this is OpenShift). `kubectl` equivalents are noted where they reinforce
  Kubernetes fundamentals; monitoring/logging/etcd objects are OpenShift/Operator CRDs.
- **Monitoring is built-in** (Cluster Monitoring Operator) — nothing to install to *read* it.
  **Logging is an add-on Operator** (admin-installed). **etcd** already runs on the control
  plane; you *inspect* it (backup/restore is **Module 12**).
- **What needs cluster-admin:** enabling user workload monitoring, installing the Logging/Loki
  Operators, and `oc rsh` into the `openshift-etcd` namespace. Reading dashboards, writing a
  **ServiceMonitor/PrometheusRule in your own namespace**, and querying your logs are
  project-user actions once the platform is set up.
- **Secrets are placeholders** (`<cluster-domain>`, `$OCP_PASSWORD`) — never commit real
  tokens or kubeconfig.
- **Cleanup** is included at the end of every demo.

## Pre-flight check

```bash
oc whoami                                   # confirm you're logged in
oc get clusteroperator monitoring           # built-in monitoring present (admin view)
oc get csv -A | grep -Ei 'logging|loki'     # Logging/Loki Operators (if installed)
oc -n openshift-monitoring get pods | head  # prometheus-k8s-*, alertmanager-main-*, thanos-*
```

Companion material: the interactive [visualizations](../index.html), the hands-on
[exercises](../exercises/README.md), and the
[concept guide](../../../guides/module-11-monitoring-logging-etcd.md).

---

> **Verification status (see each demo's footer for detail).** Re-validated against the live
> `mobily-ocp-training` cluster (OCP 4.18.45, `oc 4.22.0`, as `kube:admin`):
>
> - **Demo 3 (etcd) — ✅ fully verified live.** Every step (pod listing, `etcdctl endpoint
>   health/status` via `oc exec`, PromQL via the `thanos-querier` route, `clusteroperator
>   etcd`) was run for real; all output in the file is genuine.
> - **Demo 1 (monitoring) — ◐ partially verified.** Steps 1–2 (Observe pod list, enabling
>   user workload monitoring) were run live — UWM is now durably enabled on this cluster, and
>   a stale field name (`enableUserWorkloadMonitoring` → correct is `enableUserWorkload`) was
>   caught and fixed in the process. Steps 3–4 (ServiceMonitor/PrometheusRule renders) were
>   verified offline via `--dry-run=client`. Step 5 (watching the alert fire) is
>   representative **by design** — it needs a real app under real 5xx load for the full
>   `for: 10m` window, which is Exercise 1's job.
> - **Demo 2 (logging) — ◐ syntax-checked, not live.** The Logging + Loki Operators are
>   confirmed **not installed** on this cluster (live check, not just "cluster unreachable").
>   LogQL/`ClusterLogForwarder` syntax was checked against the Logging 6.2 API source rather
>   than run, since installing the stack needs backing object storage and is a real,
>   costed, cluster-admin prerequisite — **install before delivering this demo.**
