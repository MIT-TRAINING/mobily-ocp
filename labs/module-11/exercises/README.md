# Module 11 — Exercises (Hands-On Practice)

These are **participant-driven** tasks. You drive **`oc`** plus PromQL/LogQL and the
monitoring/logging/etcd objects, then verify with the provided **validation** commands. Each
exercise has a fully worked **solution** — try the tasks first, then check.

Module 11 — **"Monitoring, Logging and etcd Administration"** — covers the built-in
**monitoring** stack (Prometheus/Alertmanager/dashboards), the **logging** pipeline (LokiStack
+ LogQL), and **etcd** health & performance. Monitoring is built-in; logging is an
admin-installed Operator; etcd inspection is admin-only.

## Where to run these

| Target | What you can do | Notes |
|--------|-----------------|-------|
| **Shared OpenShift 4.18 cluster** (preferred) | ServiceMonitor/PrometheusRule in your ns, LogQL queries, read etcd dashboard | UWM enable, Logging install, `etcd rsh` need **cluster-admin** |
| **[Developer Sandbox](https://developers.redhat.com/developer-sandbox)** | Explore Observe → Metrics/Logs (may vary) | No cluster-admin → can't enable UWM or inspect etcd |
| **Local (no cluster)** | `oc create --dry-run=client -o yaml` renders ServiceMonitor/PrometheusRule offline | Manifest authoring is fully offline |

> **CLIs:** `oc` (+ the console **Observe** views), PromQL (Metrics), LogQL (Logs). Manifest
> rendering with `oc create --dry-run=client -o yaml` needs **no cluster** — great for
> checking your ServiceMonitor/PrometheusRule before applying.

## Exercises in this module

| # | Exercise | What you'll practice | Telecom scenario | Difficulty |
|---|----------|----------------------|------------------|------------|
| 1 | [Create a custom alert rule](exercise-01-custom-alert.md) | ServiceMonitor, PrometheusRule (`expr`+`for:`), Observe → Alerting | alert on **subscriber-api** 5xx | ⭐ Beginner |
| 2 | [Query & filter platform logs](exercise-02-log-query.md) | LogQL selector + line filters, log types, `oc logs` | trace a **self-care** failure | ⭐⭐ Intermediate |
| 3 | [Incident triage (capstone)](exercise-03-capstone.md) | alert → metrics → logs → rule out etcd, end to end | full **subscriber-api** outage | ⭐⭐⭐ Advanced |

## Before you start

```bash
oc login https://api.<cluster-domain>:6443 -u <user> -p "$OCP_PASSWORD"   # or token
oc whoami
oc get clusteroperator monitoring etcd                # platform monitoring + etcd healthy?
oc get csv -A | grep -Ei 'logging|loki'               # logging Operators present?
oc new-project mobily-apps 2>/dev/null || oc project mobily-apps
```

- App image: **`ubi9/httpd-24`** (rootless, HTTP on **8080**) stands in for `subscriber-api`;
  a bare `GET /` → **403** proves connectivity. Instrument a real app for true `/metrics`.
- Replace placeholders (`<cluster-domain>`). **Never commit real tokens** — use `$OCP_PASSWORD`
  or a token file you supply.
- **Cluster-admin needed for:** enabling user workload monitoring, installing Logging/Loki,
  and `oc rsh` into `openshift-etcd`. ServiceMonitors/PrometheusRules in your namespace and
  reading logs/dashboards are project-user actions once the platform is ready.
- Cleanup: `oc delete project mobily-apps`; delete any ServiceMonitor/PrometheusRule you made.

## How to self-assess

Each exercise's **Validation** section gives commands whose output confirms success.
`oc create --dry-run=client -o yaml` lets you check manifests **without a cluster**. Stuck?
The **Solution** walks one correct approach.

Companion material: the guided [demos](../demos/README.md), the interactive
[visualizations](../index.html), and the
[concept guide](../../../guides/module-11-monitoring-logging-etcd.md).

---

> **Verification status (see each exercise's footer for detail).** Re-checked against the
> live `mobily-ocp-training` cluster (OCP 4.18.45, `oc 4.22.0`, as `kube:admin`):
>
> - **Exercise 1 (alert) — ◐ partially verified.** UWM is confirmed live (already enabled,
>   `prometheus-user-workload-*` pods up 8h+); the ServiceMonitor/PrometheusRule dry-run
>   renders are real. Applying the CRs for real and watching `up`/the alert fire needs *your*
>   `subscriber-api` deployed — that's the task, left for the participant.
> - **Exercise 2 (logs) — ◐ syntax-checked, not live.** Logging + Loki are confirmed **not
>   installed** on this cluster (live check). LogQL/CLF syntax checked against the Logging 6.2
>   API source — install the Operators before assigning this exercise.
> - **Exercise 3 (capstone) — ◐ partially verified.** Task 4 (rule out etcd) is **fully
>   verified live** — also fixed a bug where the original `etcd-master-0` pod name doesn't
>   exist on real clusters (names are node-hostname-derived; look the pod up, don't hardcode
>   it). Tasks 1–3 need a real triggered incident and stay representative by design.
