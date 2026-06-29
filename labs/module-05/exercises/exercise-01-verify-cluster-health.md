# Exercise 1 — Verify Cluster Health

> **Scenario:** You're the on-call platform engineer and Mobily is about to ship a
> release. Produce a **health gate**: prove the cluster version is healthy, no Cluster
> Operator is degraded, every node is Ready, and document the **topology** — then show
> you know where to look if any of it were red.

| | |
|---|---|
| **Practice** | `oc get clusterversion`/`clusteroperators`/`nodes` · role counts · triage reads (`describe`, `events`, `adm top`) |
| **Maps to** | Guide §3, §4, §10 · Visualization 02 · Demo 1 |
| **Difficulty** | ⭐ Beginner · ~20 min · reads need cluster-reader/admin |

---

## Tasks

1. Show the **cluster version** and confirm `AVAILABLE=True` and `PROGRESSING=False`.
2. List the **Cluster Operators** and prove **none** are `DEGRADED`.
3. List **nodes** and confirm all are `Ready`.
4. Document the **topology**: count control-plane vs worker (and infra, if any) nodes.
5. Show the **triage reads** you'd run if something were red: an operator's
   `Conditions`, recent cluster `events`, and live node usage.
6. State your **go / no-go** verdict in one line, with the evidence.

> **Hint (Task 2):** filter to only degraded operators with a jsonpath on the
> `Degraded` condition — empty output means healthy.

> **Hint (Task 4):** `oc get nodes -l node-role.kubernetes.io/worker --no-headers | wc -l`.

---

## Validation

```bash
# Task 1
oc get clusterversion

# Task 2 — empty output = no degraded operators
oc get co -o jsonpath='{range .items[?(@.status.conditions[?(@.type=="Degraded")].status=="True")]}{.metadata.name}{"\n"}{end}'

# Task 3 — every node Ready (no lines printed = all Ready)
oc get nodes | grep -v ' Ready ' | grep -v '^NAME' || echo "all Ready"

# Task 4 — topology
echo "cp: $(oc get nodes -l node-role.kubernetes.io/master --no-headers | wc -l)  workers: $(oc get nodes -l node-role.kubernetes.io/worker --no-headers | wc -l)"
```

---

## Reflection

- Why must `PROGRESSING` be `False` before you proceed with a change?
- Which single column on `oc get co` is your first triage stop, and why?
- The same `oc get nodes` answers two different questions — which two?

---

<details>
<summary><strong>✅ Solution</strong> (try the tasks first)</summary>

```bash
# 1. Version healthy & not upgrading
oc get clusterversion

# 2. No operator degraded (empty list)
oc get clusteroperators
oc get co -o jsonpath='{range .items[?(@.status.conditions[?(@.type=="Degraded")].status=="True")]}{.metadata.name}{"\n"}{end}'

# 3. All nodes Ready
oc get nodes

# 4. Topology
echo "control-plane: $(oc get nodes -l node-role.kubernetes.io/master --no-headers | wc -l)"
echo "workers:       $(oc get nodes -l node-role.kubernetes.io/worker --no-headers | wc -l)"
echo "infra:         $(oc get nodes -l node-role.kubernetes.io/infra  --no-headers 2>/dev/null | wc -l)"

# 5. Triage reads (used when something is red)
oc describe co ingress | sed -n '/Conditions:/,/Extension/p'
oc get events -A --sort-by=.lastTimestamp | tail -15
oc adm top nodes

# 6. Verdict: "GO — version 4.18.20 Available/not-Progressing, 0 degraded operators, 5/5 nodes Ready."
```

**Representative output** *(requires a cluster — healthy OCP 4.18):*

```
NAME      VERSION   AVAILABLE   PROGRESSING   SINCE   STATUS
version   4.18.20   True        False         12d     Cluster version is 4.18.20

(no output)                       <- no degraded operators

control-plane: 3
workers:       2
infra:         0
```

**Key point:** the **three-command health check** is the gate before *every* change.
Green = go. Any `Progressing` version, `Degraded` operator, or `NotReady` node = stop and
diagnose with `describe`/`events`/`adm top` first.
</details>

---

> **◐ Partially verified:** every command **requires a live OpenShift cluster** and was
> not runnable in the authoring environment. Output is **representative of a healthy
> OpenShift 4.18** cluster; run live for your real values. Syntax follows the
> `oc`/`kubectl` 4.x reference; nothing is presented as independently verified.
</content>
