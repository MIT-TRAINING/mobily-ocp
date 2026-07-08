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

> **◐ Partially verified (see each demo's footer).** Manifest-rendering steps
> (`oc create --dry-run=client -o yaml` for **PrometheusRule** and **ServiceMonitor**) were
> **run live offline with oc 4.22** — real output. Steps needing a **live cluster** (Observe
> dashboards, LogQL results, `etcdctl` output) are **representative of OpenShift 4.18** and
> should be validated when the cluster is up (dashboards/logs as a project user; UWM/Logging
> install and etcd `rsh` as admin).
