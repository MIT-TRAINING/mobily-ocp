# Demo 2 — Query & Filter Platform Logs

> **Scenario:** A Mobily customer reports their **self-care** top-up failed. There's no metric
> for "this one customer's top-up," so we go to the **logs**. We confirm the logging stack,
> then narrow from *every log line in the cluster* to the single `topup failed: upstream
> timeout` that explains it — using a **LogQL** stream selector plus line filters, and the
> live `oc logs` fallback.

| | |
|---|---|
| **Concepts reinforced** | LokiStack · log types (application/infra/audit) · LogQL selector `{}` + line filters `|= != |~` · ClusterLogForwarder · `oc logs` |
| **Maps to** | Guide §8–§9 · Visualization 02 · Exercise 2 |
| **Time** | ~25 minutes |
| **Cluster** | Shared OCP 4.18 with **OpenShift Logging + Loki** Operators (admin-installed) |

---

> **⎈ Kubernetes note:** `oc logs` is `kubectl logs` — the raw, per-pod, unstored view.
> LokiStack/LogQL is OpenShift's aggregated **store** on top, so logs survive pod restarts.

> ⚠️ **Installing the Logging + Loki Operators and the LokiStack is cluster-admin.** Querying
> logs for namespaces you can read is a project-user action (RBAC-scoped in Observe → Logs).

> 🔧 **Prerequisite — not yet installed on this training cluster.** Checked live
> (`oc get csv -A | grep -Ei 'cluster-logging|loki'` → no results): `cluster-logging` and
> `loki-operator` are available in the catalog (`oc get packagemanifest -A` shows both under
> **Red Hat Operators**) but **no CSV is installed**, so `openshift-logging`/LokiStack don't
> exist yet here. Standing up the full stack (Operators + a LokiStack, which needs backing
> object storage — typically an S3 bucket) is real infra work with a real cost, so it's a
> **before-class setup task for the instructor**, not something this demo does live. Steps
> below show the intended flow with output representative of a correctly installed stack;
> the LogQL/CLF syntax has been checked against the current Logging 6.x API and is accurate.

## Talking points to open with

- **Metrics say *that* it broke; logs say *why*.** This is the "why" tool.
- Logging pipeline = **collect (Vector) → store (LokiStack) → visualize (LogQL/console)**.
- LogQL narrows in two moves: **stream selector** (labels, indexed) then **line filters**
  (grep). Select first, then filter.

---

## Step 1 — Confirm the logging stack

```bash
oc get csv -A | grep -Ei 'cluster-logging|loki'      # Operators Succeeded
oc -n openshift-logging get lokistack                  # the log store
oc -n openshift-logging get pods | grep -E 'vector|loki'
```

On **this** training cluster today, the first command comes back empty — real, live output:

```
$ oc get csv -A | grep -Ei 'cluster-logging|loki'
$                                              # no output: Operators not installed yet
```

**Expected output once the Operators + LokiStack are installed** *(representative of OCP
4.18 / Logging 6.x — the shape to expect after the instructor completes the prerequisite
install):*

```
cluster-logging.v6.x.y     Red Hat OpenShift Logging   6.x.y   Succeeded
loki-operator.v6.x.y       Loki Operator               6.x.y   Succeeded
NAME            STATUS
logging-loki    Ready
collector-abcde        1/1   Running    <- Vector, one per node (DaemonSet)
logging-loki-...        1/1   Running
```

> **Narrate:** **Vector** (the `collector-*` DaemonSet) reads each container's stdout/stderr
> on every node and forwards to **LokiStack** (`logging-loki`). That's collect → store; the
> console's **Observe → Logs** is the visualize step.

---

## Step 2 — See what routes where (ClusterLogForwarder)

```bash
oc -n openshift-logging get clusterlogforwarder instance -o yaml | oc neat 2>/dev/null || \
oc -n openshift-logging get clusterlogforwarder instance -o yaml
```

**Representative manifest** *(requires a cluster — schema per Logging 6.x):*

```yaml
apiVersion: observability.openshift.io/v1
kind: ClusterLogForwarder
metadata:
  name: instance
  namespace: openshift-logging
spec:
  outputs:
    - name: default-lokistack
      type: lokiStack
      lokiStack:
        target: { name: logging-loki, namespace: openshift-logging }
  pipelines:
    - name: all-to-loki
      inputRefs: [application, infrastructure, audit]   # the three log types
      outputRefs: [default-lokistack]
```

> **Narrate:** The **ClusterLogForwarder** wires **inputs** (the three log **types**) to
> **outputs**. Here all three go to the in-cluster LokiStack; we could add a second output to
> fan **audit** logs to a SIEM without touching a single app.

---

## Step 3 — Start broad, then select the stream (LogQL)

In **Observe → Logs**, or via the Loki API. Begin with just the **stream selector** (labels):

```logql
{ kubernetes_namespace_name="self-care" }
```

**Expected result** *(requires a cluster — representative):*

```
INFO   self-care/self-care   login ok user=cust_4821
INFO   self-care/self-care   GET /healthz 200
ERROR  self-care/self-care   topup failed: upstream timeout to billing
... (all self-care lines, newest first)
```

> **Narrate:** The `{ }` is the **stream selector** — it hits Loki's **label index** to pull
> only `self-care` streams, cheaply, before we grep anything. That's already a huge cut from
> "every log in the cluster." Now filter the text.

---

## Step 4 — Filter the lines (`|=`, `!=`, `|~`)

```logql
# only errors, minus health-check noise:
{ kubernetes_namespace_name="self-care" } |= "ERROR" != "/healthz"

# or hunt any timeout / refused connection with a regex:
{ kubernetes_namespace_name="self-care" } |~ "timeout|refused"
```

**Expected result** *(requires a cluster — representative):*

```
ERROR  self-care/self-care   topup failed: upstream timeout to billing
```

> **Narrate:** `|=` keeps lines containing a string, `!=` drops them, `|~` is a regex match.
> We've gone from the whole cluster to **one line**: the top-up timed out talking to billing.
> **Select by label, then grep** — you searched kilobytes, not terabytes.

---

## Step 5 — The live fallback: `oc logs`

```bash
# no store needed — read the running pod's current log straight from the node:
oc logs deploy/self-care -n self-care --tail=20
oc logs deploy/self-care -n self-care -f          # live follow
```

**Expected output** *(requires a cluster — representative):*

```
INFO   login ok user=cust_4821
ERROR  topup failed: upstream timeout to billing
```

> **Narrate:** `oc logs` is perfect for **"what's happening right now"** — but there's no
> store, so once the pod is replaced its history is gone. That's exactly the gap **LokiStack**
> fills: searchable history across restarts, across pods, over time.

---

## Step 6 — Cleanup

```bash
# Nothing to delete — this demo only *read* logs (no objects created).
# If you added an extra ClusterLogForwarder output for testing, revert it:
# oc -n openshift-logging edit clusterlogforwarder instance
echo "read-only demo — no cleanup needed"
```

---

## Wrap-up questions to pose

1. Why reach for logs here instead of a metric/alert?
2. In `{kubernetes_namespace_name="self-care"} |= "ERROR"`, which part uses Loki's index and
   which greps text?
3. What are the three log types, and why keep them as separate streams?
4. When is `oc logs` the right tool, and when does it let you down?

---

> **◐ Partially verified:** the cluster is live and reachable (`oc 4.22.0` against OCP
> 4.18.45, `kube:admin`), and **Step 1's "no Operators installed" state was confirmed live**
> (`oc get csv -A` for `cluster-logging`/`loki-operator` returns nothing; both are
> catalog-available per `oc get packagemanifest -A`, just not installed on this cluster).
> Everything downstream of that — LogQL selector/filter syntax (`|= != |~`,
> `kubernetes_namespace_name`, `kubernetes_container_name`), the `ClusterLogForwarder`
> `observability.openshift.io/v1` schema (`inputRefs: [application, infrastructure, audit]`,
> `type: lokiStack` with a `target: {name, namespace}`) — was **checked against the Logging
> 6.2 API source** (`openshift/cluster-logging-operator`, `release-6.2` branch), not run live,
> since installing the stack (Operators + a LokiStack needing backing object storage) is a
> real, costed, cluster-admin prerequisite outside this validation pass. Output blocks are
> representative of a correctly installed stack. **Install the Operators + LokiStack before
> delivering this demo**; log queries themselves are a project-user action once that's done.
