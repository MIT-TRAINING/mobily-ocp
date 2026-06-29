# Demo 3 — Cluster Operators & the Cluster Version Operator

> **Scenario:** Tonight Mobily ships a tariff-catalog release, and change-management
> wants a **platform health check** first. We'll read the cluster's *single version of
> truth*, scan all ~30 **Cluster Operators** for trouble, learn the triage habit
> (**Available / Progressing / Degraded**), and see where new platform capabilities
> come from in **OperatorHub**. This demo is the payoff of the Operator pattern:
> **OpenShift runs itself.**

| | |
|---|---|
| **Concepts reinforced** | `clusterversion` · `clusteroperators` (`co`) · A/P/D conditions · the CVO · release image · OperatorHub/OLM · triage order |
| **Maps to** | Guide §8, §9 · Visualization 03 · Exercise 3 |
| **Time** | ~30 minutes |
| **Cluster** | Shared OCP 4.18 — **cluster-scope reads** (not Sandbox for steps 1–4) |

---

> **⎈ Kubernetes equivalent:** `clusterversion` and `clusteroperators` are
> **OpenShift-only** API kinds — vanilla Kubernetes has no equivalent because vanilla
> Kubernetes doesn't manage *itself*. The verbs (`get`, `describe`) are pure `kubectl`.

> ⚠️ **Permissions:** Sandbox participants can't read cluster-scope resources — follow
> the instructor for Steps 1–4 and explore **OperatorHub** in the console (Step 5).

## Talking points to open with

- Everything self-managing about OpenShift 4 is the **Operator pattern** (Viz 03):
  a controller reconciling desired → actual. The platform uses it on *itself*.
- There is **one** cluster version (owned by the **CVO**) and ~30 **Cluster
  Operators** the CVO drives to it. That's why an upgrade is one command.
- Triage order for a sick cluster: **`clusterversion` first, then the DEGRADED column
  of `co`** — *before* you ever look at a pod.

---

## Step 1 — The single version of truth

```bash
oc get clusterversion
```

**Expected output** *(requires a cluster — representative of a healthy OCP 4.18):*

```
NAME      VERSION   AVAILABLE   PROGRESSING   SINCE   STATUS
version   4.18.20   True        False         12d     Cluster version is 4.18.20
```

> **Narrate:** One object, `version`. **AVAILABLE=True** + **PROGRESSING=False** =
> healthy and *not* mid-upgrade. This is the CVO speaking: it owns the desired release
> and reports whether the whole cluster matches it. If PROGRESSING were True, an
> upgrade would be in flight.

---

## Step 2 — The operator board

```bash
oc get clusteroperators        # alias: oc get co
oc get co --no-headers | wc -l
```

**Expected output** *(requires a cluster — representative):*

```
NAME             VERSION   AVAILABLE   PROGRESSING   DEGRADED   SINCE
authentication   4.18.20   True        False         False      12d
console          4.18.20   True        False         False      12d
dns              4.18.20   True        False         False      40d
etcd             4.18.20   True        False         False      40d
image-registry   4.18.20   True        False         False      40d
ingress          4.18.20   True        False         False      12d
kube-apiserver   4.18.20   True        False         False      40d
machine-api      4.18.20   True        False         False      40d
monitoring       4.18.20   True        False         False      12d
network          4.18.20   True        False         False      40d
...
33
```

> **Narrate:** ~30 Operators, each owning one slice — `ingress` runs the Router,
> `image-registry` runs the registry, `authentication` runs the OAuth server we logged
> in through in Demo 1, `machine-api` runs Demo 4's machines. Three booleans each:
> **AVAILABLE** (up?), **PROGRESSING** (changing?), **DEGRADED** (broken?). Right now
> all green.

---

## Step 3 — The triage column: anyone DEGRADED?

```bash
oc get co -o jsonpath='{range .items[?(@.status.conditions[?(@.type=="Degraded")].status=="True")]}{.metadata.name}{"\n"}{end}'
```

**Expected output** *(requires a cluster — healthy cluster prints nothing):*

```
(no output)
```

> **Narrate:** Empty is good — nobody is Degraded. **This is the first query you run on
> a sick cluster.** A name here points straight at the failing subsystem. Imagine
> `ingress` appeared: that means Routes/external traffic are impacted, and you'd know
> *before* touching a single application pod.

---

## Step 4 — Read one operator's conditions

```bash
oc describe co ingress | sed -n '/Conditions:/,/Extension/p'
```

**Expected output** *(requires a cluster — representative):*

```
Conditions:
  Type           Status   Reason             Message
  Available      True     IngressAvailable   The ingress controller is available
  Progressing    False    AsExpected         desired and current number of ...
  Degraded       False    AsExpected
```

> **Narrate:** The condition **messages** are where the *why* lives. When DEGRADED
> flips True, this message names the cause (cert expiry, no ready endpoints, etc.).
> Reading conditions is the core of platform triage we go deep on in Modules 11–12.

---

## Step 5 — Where new capability comes from: OperatorHub

In the **web console → Operators → OperatorHub**, browse the catalog; then peek from
the CLI at what OLM offers:

```bash
oc get packagemanifests -n openshift-marketplace | head
```

**Expected output** *(requires a cluster — representative):*

```
NAME                          CATALOG               AGE
postgresql                    Community Operators   40d
cluster-logging               Red Hat Operators     40d
openshift-gitops-operator     Red Hat Operators     40d
amq-streams                   Red Hat Operators     40d
...
```

> **Narrate:** This is the same Operator pattern, now for *add-ons*. **OLM** (Operator
> Lifecycle Manager) installs, resolves dependencies, and auto-upgrades these via
> subscriptions/channels. For Mobily's CDR store you might install a PostgreSQL
> Operator from here — a level-5 Operator that backs up and fails over the DB for you.
> We do this hands-on in Module 9.

---

## Step 6 — How an upgrade would flow (concept, do not run)

```bash
oc adm upgrade        # shows current version + available updates — does NOT upgrade
```

**Expected output** *(requires a cluster — representative):*

```
Cluster version is 4.18.20
Upstream is unset, so the cluster will use an appropriate default.
Channel: stable-4.18 (available channels: candidate-4.18, eus-4.18, fast-4.18, stable-4.18)

Recommended updates:
  VERSION   IMAGE
  4.18.21   quay.io/openshift-release-dev/ocp-release@sha256:...
```

> **Narrate:** `oc adm upgrade` (no `--to`) only *reports*. When you do run
> `--to=4.18.21`, the **CVO** sets the new release image, walks every Cluster Operator
> to it **in dependency order**, and the MCO rolls RHCOS on each node. OS + runtime +
> Kubernetes + platform services move as **one tested unit** — exactly the CVO
> animation in Visualization 03.

---

## Cleanup

Nothing to clean up — this demo only **read** cluster state (we never ran an upgrade).

---

## Wrap-up questions to pose

1. Why does the cluster have one `clusterversion` but ~30 `clusteroperators`? Who ties
   them together?
2. The console is down. What are your **first two commands**, and why beat `oc get
   pods`?
3. What do AVAILABLE / PROGRESSING / DEGRADED each tell you?
4. Where do add-on Operators come from, and what installs/upgrades them?

---

> **◐ Partially verified:** `oc get clusterversion` / `clusteroperators` /
> `describe co` / `get packagemanifests` / `adm upgrade` all **require a live OpenShift
> cluster** and could not be executed in the authoring environment. Output is
> **representative of a healthy OpenShift 4.18** cluster; run the commands live to
> capture your real operator board and available updates. Command syntax follows the
> `oc` 4.x reference; nothing is presented as independently verified.
</content>
