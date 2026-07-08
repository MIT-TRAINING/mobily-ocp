# Exercise 2 — Query & Filter Platform Logs

> **Scenario:** A **self-care** customer reports their top-up silently failed. No metric
> captures a single customer's action, so you go to the **logs**. Using **LogQL**, narrow from
> every log stream in the cluster to the one line that explains it — then prove you can do the
> same for the **subscriber-api** it depends on.

| | |
|---|---|
| **Practice** | LogQL stream selector `{}` · line filters `|=` `!=` `|~` · log types · `oc logs` fallback |
| **Maps to** | Guide §8–§9 · Visualization 02 · Demo 2 |
| **Difficulty** | ⭐⭐ Intermediate · ~20 min · needs Logging + Loki Operators (admin-installed) |

> ⚠️ Installing Logging/Loki is admin. Querying logs for namespaces you can read is a
> project-user action (Observe → Logs is RBAC-scoped).

---

## Tasks

1. In **Observe → Logs**, write a LogQL query that selects **only** the `self-care`
   namespace's logs (stream selector, no line filter yet). Note roughly how many lines.
2. Add a **line filter** so you see only `ERROR` lines, and a second filter that **excludes**
   health-check noise (`/healthz`). You should be down to the failing line.
3. Write a query for `subscriber-api` in `mobily-apps` that finds any **timeout or refused
   connection** using a **regex** line filter.
4. Get the same "right now" view with **`oc logs`** for the `self-care` deployment, and explain
   what `oc logs` can't give you that LokiStack can.
5. Name which **log type** (application / infrastructure / audit) each of these lands in:
   your `self-care` pod's stdout; a `kube-apiserver` audit event; a node's kubelet log.

> **Hint (Task 2):** `|=` keeps matching lines, `!=` drops them — you can chain them.

> **Hint (Task 3):** regex line filter is `|~ "timeout|refused"`.

---

## Validation

```bash
# LogQL (Observe → Logs) — expected to narrow to ~1 line by task 2:
#   { kubernetes_namespace_name="self-care" }
#   { kubernetes_namespace_name="self-care" } |= "ERROR" != "/healthz"
#   { kubernetes_namespace_name="mobily-apps", kubernetes_container_name="subscriber-api" } |~ "timeout|refused"

# oc logs fallback:
oc logs deploy/self-care -n self-care --tail=20
```

Expected: the filtered LogQL returns the `topup failed: upstream timeout` line; the regex query
surfaces `subscriber-api`'s `connection refused: subscriber-db` line.

---

## Reflection

- Which part of `{namespace="self-care"} |= "ERROR"` uses Loki's **index**, and which greps
  raw text? Why does the order (select, then filter) matter for cost?
- Why keep **audit** logs as a separate type from **application** logs?
- You need "what did this pod log last Tuesday." Does `oc logs` help? What does?

---

<details>
<summary><strong>✅ Solution</strong> (try the tasks first)</summary>

**LogQL queries (Observe → Logs):**

```logql
# 1. stream selector only — all self-care logs
{ kubernetes_namespace_name="self-care" }

# 2. errors, minus health-check noise → the failing line
{ kubernetes_namespace_name="self-care" } |= "ERROR" != "/healthz"
#   → ERROR  self-care/self-care  topup failed: upstream timeout to billing

# 3. subscriber-api timeouts/refusals via regex
{ kubernetes_namespace_name="mobily-apps", kubernetes_container_name="subscriber-api" } |~ "timeout|refused"
#   → ERROR  ...  connection refused: subscriber-db:5432
```

**oc logs fallback (Task 4):**

```bash
oc logs deploy/self-care -n self-care --tail=20
oc logs deploy/self-care -n self-care -f     # live follow
```

**Log types (Task 5):**

| Source | Log type |
|--------|----------|
| your `self-care` pod's stdout | **application** |
| a `kube-apiserver` audit event | **audit** |
| a node's kubelet log | **infrastructure** |

**Why:** the `{ }` **stream selector** hits Loki's **label index** to pick streams cheaply
*before* any text grep; `|=` / `!=` / `|~` are **line filters** applied to that smaller set —
so you select first, then filter (kilobytes, not terabytes). `oc logs` reads a *running* pod's
current log with no store, so it can't answer "last Tuesday" — that's exactly what LokiStack's
retained, indexed history is for. Audit is separated so security/compliance can apply different
RBAC and retention than developer application logs.
</details>

---

> **◐ Partially verified:** LogQL/`oc logs` **syntax** follows the Logging 6.x / oc 4.22
> reference; every step **requires a live cluster with the Logging + Loki Operators** and was
> not run at authoring (cluster asleep/unreachable). Output is **representative of OpenShift
> 4.18**; the `kubernetes_namespace_name`/`kubernetes_container_name` labels match Logging 6.x.
> Validate when the cluster is up (Operator/LokiStack install as admin; queries as a project
> user).
