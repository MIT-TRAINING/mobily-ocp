# Exercise 3 — Cluster Operators & the Cluster Version

> **Scenario:** Mobily's change-management board wants a **platform health check**
> before tonight's tariff-catalog release. You'll read the cluster's **single version
> of truth**, scan all **Cluster Operators** for trouble, learn the **triage pattern**
> (Available / Progressing / Degraded), and find where **OperatorHub** lives.

| | |
|---|---|
| **Practice** | `oc get clusterversion`, `oc get clusteroperators`, reading A/P/D conditions, `oc describe co`, OperatorHub |
| **Maps to** | Guide §8, §9 · Visualization 03 · Demo 3 |
| **Difficulty** | ⭐⭐ Intermediate · ~25 min · **needs a real cluster** for `co`/`clusterversion` |

> ⚠️ **Cluster-scope reads.** `clusterversion` and `clusteroperators` are cluster-level.
> On the **Developer Sandbox** you can't read them — browse **OperatorHub** in the
> console instead (Task 5), and follow the instructor's cluster for Tasks 1–4.

---

## Tasks

1. Print the cluster's **version** and update channel (`oc get clusterversion`). Is it
   **healthy** (`Available=True`), or mid-**Progressing**?
2. List **all Cluster Operators** (`oc get clusteroperators`, alias `co`). How many are
   there, and are they all **AVAILABLE** with **DEGRADED=False**?
3. Find the **one column that matters most for triage** and confirm none of the
   operators are **Degraded**.
4. Pick one operator you recognise from the guide (e.g. `ingress`, `authentication`,
   `image-registry`, `monitoring`) and `oc describe co <name>` — read its **Conditions**
   and the **message** lines.
5. In the **web console** (Administrator perspective), open **Operators → OperatorHub**
   and find the catalog of installable Operators. Note one you'd use for Mobily (e.g. a
   PostgreSQL/Crunchy Operator for the CDR store).
6. *(Concept)* Explain, from the output, **how an upgrade would flow**: who reads the
   release image, and what each Cluster Operator does.

> **Hint (Task 1):** add `-o jsonpath` to pull just the version:
> `oc get clusterversion version -o jsonpath='{.status.desired.version}{"\n"}'`.

> **Hint (Task 3):** the **DEGRADED** column is your first stop. Filter quickly with
> `oc get co | awk '$5=="True"'` (column 5 is DEGRADED) — empty output = healthy.

---

## Validation

```bash
# Task 1 — version + top-level health
oc get clusterversion

# Task 2 — the operator board (A / P / D columns)
oc get clusteroperators

# Task 3 — anyone Degraded? (no rows = healthy)
oc get co -o jsonpath='{range .items[?(@.status.conditions[?(@.type=="Degraded")].status=="True")]}{.metadata.name}{"\n"}{end}'

# Task 4 — conditions for one operator
oc describe co ingress | sed -n '/Conditions:/,/Extension:/p'
```

---

## Reflection

- Why does the cluster have **one** `clusterversion` but ~30 `clusteroperators`? What
  is the relationship (recall the **CVO**)?
- The console reports "down". From §9, what are your **first two commands**, and why do
  they beat starting with `oc get pods`?
- An OpenShift upgrade is *one command* (`oc adm upgrade --to=…`). Using the A/P/D
  conditions, describe what you'd **see happen** to the operators during the upgrade.

---

<details>
<summary><strong>✅ Solution</strong> (try the tasks first)</summary>

```bash
# 1. Cluster version (single source of truth) + channel
oc get clusterversion
oc get clusterversion version -o jsonpath='{.status.desired.version}{"  channel="}{.spec.channel}{"\n"}'

# 2. All Cluster Operators
oc get clusteroperators            # alias: oc get co
oc get co --no-headers | wc -l     # ~30+

# 3. Triage: list any Degraded operators (empty = healthy)
oc get co -o jsonpath='{range .items[?(@.status.conditions[?(@.type=="Degraded")].status=="True")]}{.metadata.name}{"\n"}{end}'

# 4. Deep-dive one operator's conditions
oc describe co ingress | sed -n '/Conditions:/,/Extension:/p'

# 5. OperatorHub: web console → Operators → OperatorHub (browse the catalog)
#    CLI peek at what's available via OLM:
oc get packagemanifests -n openshift-marketplace | head

# 6. Upgrade flow (concept): CVO reads the release image → drives each Cluster Operator
#    to the new version in dependency order → MCO rolls RHCOS on every node.
oc adm upgrade            # shows current version + available updates (does NOT upgrade)
```

**Representative output** *(requires a cluster — typical of a healthy OpenShift 4.18):*

```
$ oc get clusterversion
NAME      VERSION   AVAILABLE   PROGRESSING   SINCE   STATUS
version   4.18.20   True        False         12d     Cluster version is 4.18.20

$ oc get clusteroperators
NAME                                       VERSION   AVAILABLE   PROGRESSING   DEGRADED   SINCE
authentication                             4.18.20   True        False         False      12d
console                                    4.18.20   True        False         False      12d
dns                                        4.18.20   True        False         False      40d
etcd                                       4.18.20   True        False         False      40d
image-registry                             4.18.20   True        False         False      40d
ingress                                    4.18.20   True        False         False      12d
kube-apiserver                             4.18.20   True        False         False      40d
machine-api                                4.18.20   True        False         False      40d
monitoring                                 4.18.20   True        False         False      12d
network                                    4.18.20   True        False         False      40d
... (~30 operators total) ...

$ oc get co -o jsonpath='...Degraded==True...'      # healthy cluster: (no output)
```

**Key point:** the cluster has **one version** (the `clusterversion`, owned by the
**CVO**) and ~30 **Cluster Operators** the CVO drives to that version. Health triage is
three booleans — **AVAILABLE** (up?), **PROGRESSING** (rolling out?), **DEGRADED**
(broken?). When something's wrong, `oc get clusterversion` + `oc get co` (scan the
DEGRADED column) point at the failing subsystem *before* you ever look at a pod.
</details>

---

> **◐ Partially verified:** `oc get clusterversion` / `oc get clusteroperators` /
> `oc describe co` / `oc adm upgrade` all **require a live OpenShift cluster** and could
> not be executed in the authoring sandbox. Output shown is **representative of a
> healthy OpenShift 4.18** cluster; run the commands on the shared cluster to capture
> your real operator board. Command syntax follows the `oc` 4.x reference; no output is
> presented as independently verified.
</content>
