# Exercise 1 — Create a Custom Alert Rule

> **Scenario:** Mobily's platform team must be paged when **subscriber-api** starts returning
> errors. Platform monitoring won't do it (it watches OpenShift, not your app), so you'll wire
> up user workload monitoring: scrape the app with a **ServiceMonitor** and fire a
> **PrometheusRule** on its 5xx error ratio.

| | |
|---|---|
| **Practice** | ServiceMonitor · PrometheusRule (`expr` + `for:` + `severity`) · Observe → Metrics/Alerting · UWM boundary |
| **Maps to** | Guide §4–§7 · Visualization 01 · Demo 1 |
| **Difficulty** | ⭐ Beginner · ~20 min · needs user workload monitoring enabled (admin) |

> ⚠️ Enabling **user workload monitoring** is cluster-admin (once). Creating the
> ServiceMonitor/PrometheusRule in your own namespace is a project-user action.

---

## Tasks

1. Confirm user workload monitoring is on (ask your instructor/admin if not) — there should be
   `prometheus-user-workload-*` pods in `openshift-user-workload-monitoring`.
2. Author a **ServiceMonitor** in `mobily-apps` that scrapes a Service labelled
   `app: subscriber-api` on port `web`, path `/metrics`, every 30s. **Render it offline first**
   with `--dry-run=client -o yaml`, then apply.
3. Author a **PrometheusRule** `subscriber-api-alerts` with an alert
   `SubscriberAPIHighErrorRate`: fire when the 5xx **ratio** exceeds **5%** for **10m**, with
   `severity: warning`.
4. In **Observe → Metrics**, confirm your app is scraped (`up{job="subscriber-api"}` = 1).
5. In **Observe → Alerting**, find your alert and describe its state (Inactive/Pending/Firing).

> **Hint (Task 2):** the ServiceMonitor's `selector.matchLabels` must match the **Service's**
> labels, not the Deployment's.

> **Hint (Task 3):** the error ratio is `sum(rate(5xx[5m])) / sum(rate(all[5m]))`. Put the
> `> 0.05` inside `expr`; `for:` is a sibling of `expr`, not part of it.

---

## Validation

```bash
# manifests are valid (works offline):
oc create -f servicemonitor.yaml --dry-run=client -o yaml >/dev/null && echo "SM ok"
oc create -f prometheusrule.yaml --dry-run=client -o yaml >/dev/null && echo "PR ok"

# after applying:
oc -n mobily-apps get servicemonitor subscriber-api
oc -n mobily-apps get prometheusrule subscriber-api-alerts
# Observe → Metrics:  up{job="subscriber-api"}   → 1
# Observe → Alerting: SubscriberAPIHighErrorRate  → Inactive (until errors occur)
```

---

## Reflection

- Platform monitoring is already running — why doesn't it alert on your app without this?
- What would change about the alert's behaviour if you set `for: 0m`? Why is that risky?
- Which label makes Alertmanager route this to Slack vs PagerDuty?

---

<details>
<summary><strong>✅ Solution</strong> (try the tasks first)</summary>

```bash
oc project mobily-apps

# 2. ServiceMonitor — render offline, then apply
cat > servicemonitor.yaml <<'EOF'
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
oc create -f servicemonitor.yaml --dry-run=client -o yaml   # inspect
oc apply -f servicemonitor.yaml

# 3. PrometheusRule
cat > prometheusrule.yaml <<'EOF'
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: subscriber-api-alerts
  namespace: mobily-apps
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
oc apply -f prometheusrule.yaml

# 4-5. verify in the console (Observe → Metrics / Alerting), or:
oc -n mobily-apps get servicemonitor,prometheusrule
```

**Verified render** *(`oc create --dry-run=client -o yaml`, run offline — real):*

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

**Why:** platform monitoring only watches OpenShift; the **ServiceMonitor** opts your app into
the **user-workload** Prometheus, and the **PrometheusRule** turns its metrics into a paging
condition. `for: 0m` would fire on a single bad scrape (a blip) — noisy and untrustworthy. The
`severity` **label** is what Alertmanager routes on.
</details>

---

> **◐ Partially verified:** the **ServiceMonitor/PrometheusRule renders**
> (`oc create --dry-run=client -o yaml`) were **run live offline with oc 4.22** — real output.
> Steps needing a **live cluster** (UWM pods, `up` metric, Observe → Alerting state) are
> **representative of OpenShift 4.18**; enabling UWM is admin, the CRs are project-user
> actions. Validate when the cluster is up.
