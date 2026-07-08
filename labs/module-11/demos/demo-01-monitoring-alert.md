# Demo 1 — Dashboards & a Custom Alert

> **Scenario:** Mobily's platform team wants to be paged when **subscriber-api**'s 5xx error
> rate stays high. We tour the built-in **Observe** dashboards, then wire up *our own* app
> monitoring: enable user workload monitoring (admin), point Prometheus at the app with a
> **ServiceMonitor**, author a **PrometheusRule**, and watch it move to **Firing** and route
> through **Alertmanager**.

| | |
|---|---|
| **Concepts reinforced** | Observe → Metrics/Dashboards/Alerting · user workload monitoring · ServiceMonitor · PrometheusRule (`expr` + `for:`) · Alertmanager routing |
| **Maps to** | Guide §3–§7 · Visualization 01 · Exercise 1 |
| **Time** | ~30 minutes |
| **Cluster** | Shared OCP 4.18 — monitoring is **built-in**; enabling **UWM** needs admin |

---

> **⎈ Kubernetes note:** `ServiceMonitor` and `PrometheusRule` are CRDs from the
> **prometheus-operator** (`monitoring.coreos.com`), the same project upstream Kubernetes
> uses via kube-prometheus. OpenShift ships and manages them for you.

> ⚠️ **Enabling user workload monitoring is cluster-admin.** Once on, creating a
> ServiceMonitor/PrometheusRule *in your own namespace* is a project-user action.

## Talking points to open with

- OpenShift **ships** Prometheus + Alertmanager (Cluster Monitoring Operator) — you *use* it.
- Platform monitoring watches **OpenShift**; your apps need **user workload monitoring** +
  a **ServiceMonitor** to be scraped.
- An alert = **PromQL expression + `for:`**. Prometheus fires; **Alertmanager** routes.

---

## Step 1 — Tour the built-in Observe views (no setup)

```bash
# Console path: Observe → Dashboards (curated) / Metrics (ad-hoc PromQL) / Alerting (live)
# From the CLI, confirm the platform stack is running:
oc -n openshift-monitoring get pods | grep -E 'prometheus-k8s|alertmanager-main|thanos-querier'
```

**Expected output** *(requires a cluster — representative of OCP 4.18):*

```
alertmanager-main-0                            6/6     Running
alertmanager-main-1                            6/6     Running
prometheus-k8s-0                               6/6     Running
prometheus-k8s-1                               6/6     Running
thanos-querier-7d9c...-abcde                   6/6     Running
```

> **Narrate:** In the console, **Observe → Metrics** runs ad-hoc PromQL; try
> `sum(rate(apiserver_request_total[5m]))`. **Observe → Dashboards** has curated views
> (etcd, API server, compute). **Observe → Alerting** lists what's currently Pending/Firing.
> All of this exists with **zero setup** — it's the platform watching itself via **Thanos
> Querier**.

---

## Step 2 — Enable user workload monitoring (admin, once)

```bash
oc -n openshift-monitoring get configmap cluster-monitoring-config -o yaml 2>/dev/null || \
oc apply -f - <<'EOF'
apiVersion: v1
kind: ConfigMap
metadata:
  name: cluster-monitoring-config
  namespace: openshift-monitoring
data:
  config.yaml: |
    enableUserWorkloadMonitoring: true
EOF
oc -n openshift-user-workload-monitoring get pods
```

**Expected output** *(requires a cluster + admin — representative):*

```
configmap/cluster-monitoring-config created
NAME                                   READY   STATUS
prometheus-user-workload-0             6/6     Running
prometheus-user-workload-1             6/6     Running
prometheus-operator-...                2/2     Running
```

> **Narrate:** Flipping one flag spins up a **second Prometheus** in
> `openshift-user-workload-monitoring` dedicated to *your* apps — kept isolated from the
> platform one so your queries and alerts can't destabilise cluster monitoring.

---

## Step 3 — Point Prometheus at the app (ServiceMonitor)

The app exposes `/metrics` on a Service labelled `app: subscriber-api`. A **ServiceMonitor**
tells the user-workload Prometheus to scrape it. Render it offline to inspect it first:

```bash
oc create -f - --dry-run=client -o yaml <<'EOF'
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: subscriber-api
  namespace: mobily-apps
  labels: { app: subscriber-api }
spec:
  selector:
    matchLabels: { app: subscriber-api }
  endpoints:
    - port: web
      path: /metrics
      interval: 30s
EOF
```

**Verified output** *(oc 4.22 `--dry-run=client`, run offline — no cluster):*

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  labels:
    app: subscriber-api
  name: subscriber-api
  namespace: mobily-apps
spec:
  endpoints:
  - interval: 30s
    path: /metrics
    port: web
  selector:
    matchLabels:
      app: subscriber-api
```

> **Narrate:** The **selector** matches the Service's labels; `endpoints` says *where*
> (`port: web`, `path: /metrics`) and *how often* (`interval: 30s`). Apply it (drop
> `--dry-run`) and within a scrape interval `up{job="subscriber-api"}` appears in
> **Observe → Metrics** — proof the app is being scraped.

---

## Step 4 — Author the alert (PrometheusRule)

```bash
oc create -f - --dry-run=client -o yaml <<'EOF'
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: subscriber-api-alerts
  namespace: mobily-monitoring
spec:
  groups:
    - name: subscriber-api.rules
      rules:
        - alert: SubscriberAPIHighErrorRate
          expr: sum(rate(http_requests_total{job="subscriber-api",code=~"5.."}[5m])) / sum(rate(http_requests_total{job="subscriber-api"}[5m])) > 0.05
          for: 10m
          labels: { severity: warning }
          annotations: { summary: "subscriber-api 5xx error rate above 5% for 10m" }
EOF
```

**Verified output** *(oc 4.22 `--dry-run=client`, run offline — no cluster):*

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: subscriber-api-alerts
  namespace: mobily-monitoring
spec:
  groups:
  - name: subscriber-api.rules
    rules:
    - alert: SubscriberAPIHighErrorRate
      annotations:
        summary: subscriber-api 5xx error rate above 5% for 10m
      expr: sum(rate(http_requests_total{job="subscriber-api",code=~"5.."}[5m])) /
        sum(rate(http_requests_total{job="subscriber-api"}[5m])) > 0.05
      for: 10m
      labels:
        severity: warning
```

> **Narrate:** Read the `expr` aloud: 5xx request rate over total request rate — the **error
> ratio** — greater than **5%**. `for: 10m` means it must hold ten minutes before firing
> (blip filter). The `severity: warning` **label** is what Alertmanager routes on.

---

## Step 5 — Watch it fire and route

```bash
# apply for real, then generate errors against subscriber-api (see exercise), and watch:
oc apply -f prometheusrule.yaml -n mobily-monitoring
oc -n mobily-monitoring get prometheusrule subscriber-api-alerts
# Observe → Alerting shows: Inactive → Pending (during 'for') → Firing
```

**Expected output** *(requires a cluster — representative):*

```
prometheusrule.monitoring.coreos.com/subscriber-api-alerts created
NAME                       AGE
subscriber-api-alerts      12s
# In Observe → Alerting: SubscriberAPIHighErrorRate  ⏳ Pending → 🔔 Firing (after 10m)
```

> **Narrate:** In **Observe → Alerting** the alert sits **Pending** while the `for:` window
> elapses, then flips to **Firing** and reaches **Alertmanager**, which groups it and routes
> `severity=warning` to its configured receiver (e.g. Slack). A critical-severity alert would
> go to PagerDuty instead — same alert engine, different route.

---

## Step 6 — Cleanup

```bash
oc delete prometheusrule subscriber-api-alerts -n mobily-monitoring
oc delete servicemonitor subscriber-api -n mobily-apps
# (leave user workload monitoring enabled — it's cluster config, not per-demo)
```

**Expected output** *(representative):*

```
prometheusrule.monitoring.coreos.com "subscriber-api-alerts" deleted
servicemonitor.monitoring.coreos.com "subscriber-api" deleted
```

---

## Wrap-up questions to pose

1. Platform monitoring is running — why didn't it already alert on `subscriber-api`?
2. What does the `for: 10m` clause change about *when* the alert fires?
3. Which component evaluates the expression, and which one routes the notification?
4. How would you send `severity: critical` alerts somewhere different from `warning`?

---

> **◐ Partially verified — Steps 3 & 4 VERIFIED offline; cluster steps representative.**
> The **ServiceMonitor** and **PrometheusRule** renders (`oc create --dry-run=client -o yaml`,
> Steps 3–4) were **run live offline with oc 4.22** — real output. Steps needing a **live
> cluster** (pod listings, UWM pods, Observe → Alerting state) are **representative of
> OpenShift 4.18**; enabling UWM is admin, the ServiceMonitor/PrometheusRule are project-user
> actions. Validate when the cluster is up.
