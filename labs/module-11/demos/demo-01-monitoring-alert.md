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

**Verified output** *(live, `oc 4.22.0` against OCP 4.18.45):*

```
alertmanager-main-0                                      6/6     Running   6          11h
alertmanager-main-1                                      6/6     Running   6          11h
prometheus-k8s-0                                         6/6     Running   6          11h
prometheus-k8s-1                                         6/6     Running   6          11h
thanos-querier-754c6cfddd-6jxs5                          6/6     Running   6          11h
thanos-querier-754c6cfddd-7lvbz                          6/6     Running   6          11h
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
    enableUserWorkload: true
EOF
oc -n openshift-user-workload-monitoring get pods
```

**Verified output** *(live, `oc 4.22.0` against OCP 4.18.45, ~1 minute after apply):*

```
configmap/cluster-monitoring-config created
NAME                                   READY   STATUS    RESTARTS   AGE
prometheus-operator-655cbbf5d9-vc8hr   2/2     Running   0          56s
prometheus-user-workload-0             6/6     Running   0          53s
prometheus-user-workload-1             6/6     Running   0          53s
thanos-ruler-user-workload-0           4/4     Running   0          53s
thanos-ruler-user-workload-1           4/4     Running   0          53s
```

> **Narrate:** Flipping one flag spins up a **second Prometheus** (plus a **Thanos Ruler**, for
> alerting rules over long-term/aggregated data) in `openshift-user-workload-monitoring`
> dedicated to *your* apps — kept isolated from the platform one so your queries and alerts
> can't destabilise cluster monitoring. Pods take under a minute to come up from a cold start.
>
> **Field-name correction:** the config key is **`enableUserWorkload`**, not
> `enableUserWorkloadMonitoring` — an older/community name that some blog posts still use.
> Applying it with the wrong key is rejected outright by the cluster's validating admission
> webhook (`admission webhook "monitoringconfigmaps.openshift.io" denied the request: ...
> unknown field "enableUserWorkloadMonitoring"`), so the typo fails loudly rather than
> silently doing nothing — but it's worth getting right the first time in front of a class.

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

**Expected output** *(deliberately not run in this pass — see note below):*

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
>
> **Scope note:** this step assumes `subscriber-api` is already deployed and emitting
> `http_requests_total` in the `mobily-apps`/`mobily-monitoring` namespaces (neither exists
> yet on a fresh cluster — this demo doesn't create them). Watching the alert really move
> Pending → Firing needs the app deployed, real 5xx traffic, and waiting out the `for: 10m`
> window — that full loop is **Exercise 1**, not this demo. Steps 1–4 here establish the
> *mechanism* (stack is up, UWM is live, the objects render correctly); Exercise 1 is where
> it fires for real.

---

## Step 6 — Cleanup

```bash
oc delete prometheusrule subscriber-api-alerts -n mobily-monitoring
oc delete servicemonitor subscriber-api -n mobily-apps
# (leave user workload monitoring enabled — it's cluster config, not per-demo)
```

**Expected output** *(representative — cleans up the objects Steps 3–5 describe applying for
real; this validation pass only rendered them offline, so there was nothing to delete):*

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

> **◐ Partially verified:** Steps 1–2 were **run live** (`oc 4.22.0` against OCP 4.18.45,
> cluster `mobily-ocp-training`, as `kube:admin`) — the platform pod list and the UWM enable
> (with the corrected `enableUserWorkload` field) are real output, and UWM is now durably
> enabled on this shared cluster. Steps 3–4 (**ServiceMonitor**/**PrometheusRule** renders,
> `oc create --dry-run=client -o yaml`) were **run live offline** — also real output. Step 5
> (the alert actually firing) is **representative by design**, not a verification gap: it
> requires the `subscriber-api` app deployed and generating real 5xx traffic for the full
> `for: 10m` window, which is **Exercise 1**'s job, not this demo's. Step 6 is representative
> for the same reason (nothing was created for real in this pass to clean up).
