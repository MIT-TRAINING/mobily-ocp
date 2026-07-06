# Demo 3 — Package & Release with Helm

> **Scenario:** Package the Mobily **self-care** app as a reusable **Helm chart** so it can
> be deployed many ways from one template. We scaffold a chart, lint it, render it with
> default and overridden values, then walk the **install → upgrade → rollback** lifecycle.

| | |
|---|---|
| **Concepts reinforced** | `helm create` · chart anatomy · `helm lint` · `helm template` + `--set` override · install/upgrade/rollback/history |
| **Maps to** | Guide §5, §6, §7 · Visualization 03 · Exercise 3 |
| **Time** | ~30 minutes |
| **Cluster** | `helm create/lint/template` need **no cluster**; `helm install/upgrade` need a cluster (normal user in own project) |

---

> **⎈ Kubernetes equivalent:** Helm 3 is a client-side tool (no Tiller) — same on any
> Kubernetes. The OpenShift console's **Developer → Helm** view lists releases too.

## Talking points to open with

- A **chart** = templates + `values.yaml`; **values** parameterize it; installing = a named
  **release** with revision history.
- **`helm template`/`lint` run offline** — perfect for review and CI.
- **Override precedence:** `--set` > `-f file` > chart defaults.

---

## Step 1 — Scaffold a chart (VERIFIED)

```bash
helm create subscriber-api
find subscriber-api -maxdepth 2 -type f | sort
```

**Verified output** *(helm v3.16.3, run live — no cluster):*

```
Creating subscriber-api
subscriber-api/.helmignore
subscriber-api/Chart.yaml
subscriber-api/templates/NOTES.txt
subscriber-api/templates/_helpers.tpl
subscriber-api/templates/deployment.yaml
subscriber-api/templates/hpa.yaml
subscriber-api/templates/ingress.yaml
subscriber-api/templates/service.yaml
subscriber-api/templates/serviceaccount.yaml
subscriber-api/values.yaml
```

> **Narrate:** `helm create` scaffolds a working chart: **Chart.yaml** (metadata),
> **values.yaml** (defaults), and **templates/** (Go-templated manifests + `_helpers.tpl`
> and `NOTES.txt`). Edit these to make it *your* app.

---

## Step 2 — Lint it (VERIFIED)

```bash
helm lint subscriber-api
```

**Verified output** *(helm v3.16.3, run live):*

```
==> Linting subscriber-api
[INFO] Chart.yaml: icon is recommended

1 chart(s) linted, 0 chart(s) failed
```

> **Narrate:** `helm lint` checks the chart is well-formed. The `INFO` about `icon` is
> advisory; **0 failed** means it's valid. Run this in CI before shipping a chart.

---

## Step 3 — See defaults, then render (VERIFIED)

```bash
helm show values subscriber-api | sed -n '1,10p'
helm template subscriber-api subscriber-api | grep 'replicas:'
```

**Verified output** *(helm v3.16.3, run live):*

```
# Default values for subscriber-api.
...
replicaCount: 1
image:
  repository: nginx
...
  replicas: 1
```

> **Narrate:** The scaffold's defaults are `replicaCount: 1` and image `nginx`.
> `helm template` renders the chart to manifests **locally, no cluster** — what you'd
> review before applying.

---

## Step 4 — Override values (VERIFIED)

```bash
helm template subscriber-api subscriber-api \
  --set replicaCount=3 \
  --set image.repository=registry.access.redhat.com/ubi9/httpd-24 \
  --set image.tag=latest \
  | grep -E 'replicas:|image:'
```

**Verified output** *(helm v3.16.3, run live):*

```
  replicas: 3
          image: "registry.access.redhat.com/ubi9/httpd-24:latest"
```

> **Narrate:** Same chart, different config — `--set` overrode `replicaCount` (1 → **3**)
> and the image (nginx → **UBI httpd-24**). `--set` beats a `-f values.yaml` beats the
> chart defaults. One template, many environments.

---

## Step 5 — Release lifecycle: install → upgrade → rollback

```bash
helm install self-care ./subscriber-api --set replicaCount=2      # revision 1
helm list
helm upgrade self-care ./subscriber-api --set replicaCount=5      # revision 2
helm history self-care
helm rollback self-care 1                                          # revision 3 = copy of rev 1
helm history self-care
```

**Expected output** *(requires a cluster — representative of a real run):*

```
NAME: self-care
STATUS: deployed
REVISION: 1
NAME        REVISION   STATUS       CHART                 APP VERSION
self-care   1          deployed     subscriber-api-0.1.0  1.16.0
# after upgrade:
REVISION  UPDATED   STATUS       DESCRIPTION
1         ...       superseded   Install complete
2         ...       deployed     Upgrade complete
# after rollback:
3         ...       deployed     Rollback to 1
```

> **Narrate:** Install = rev 1; upgrade = rev 2; **rollback 1** creates **rev 3** (a copy
> of rev 1) — history is append-only, nothing lost. Add `--atomic` to auto-roll-back a
> failed upgrade. `helm uninstall self-care` removes it.

---

## Step 6 — Cleanup

```bash
helm uninstall self-care        # if installed to the cluster
rm -rf subscriber-api           # remove the scaffolded chart dir
```

**Expected output** *(representative):*

```
release "self-care" uninstalled
```

---

## Wrap-up questions to pose

1. What three things make up a chart, and what is a "release"?
2. Which two Helm commands run without a cluster, and why is that useful?
3. Override precedence: `--set` vs `-f file` vs `values.yaml` — which wins?
4. An upgrade broke prod. How do you revert, and what does the history show afterwards?

---

> **✅ Verified (chart authoring) / ◐ representative (cluster install).** Steps 1–4
> (`helm create`, `helm lint`, `helm show values`, `helm template` with `--set`) were **run
> live with helm v3.16.3** — that output is real, no cluster needed. Step 5's
> `helm install/upgrade/rollback` **require a live cluster** and are **representative of a
> real run**; a normal user can validate them in their own project when the cluster is up.
