# Demo 1 — Verify Cluster Health (and Read the Topology)

> **Scenario:** Mobily ships a tariff-catalog release tonight and change-management
> wants a **green light** on the platform first. We run the administrator's
> **three-command health check**, read the cluster **topology** while we're there, and
> rehearse the triage path for a `DEGRADED` operator or a `NotReady` node — the muscle
> memory you'll use before every change.

| | |
|---|---|
| **Concepts reinforced** | `clusterversion` · `clusteroperators` · `nodes`/topology · `describe` triage · `events` · `adm top` · `must-gather` |
| **Maps to** | Guide §3, §4, §10 · Visualization 02 · Exercise 1 |
| **Time** | ~25 minutes |
| **Cluster** | Shared OCP 4.18 — reads need **cluster-reader/admin** (not Sandbox) |

---

> **⎈ Kubernetes equivalent:** `get nodes`, `describe node`, `get events` are pure
> `kubectl`. `clusterversion`/`clusteroperators` are **OpenShift-only** (vanilla
> Kubernetes doesn't manage itself), and `oc adm top`/`must-gather` are OpenShift admin
> verbs.

## Talking points to open with

- "Is the cluster healthy?" is answered in **three commands**, every time.
- Never start a change on a cluster that isn't green: a `Progressing` version or a
  `Degraded` operator means *fix first*.
- The same `oc get nodes` that checks health also shows your **topology** (control /
  worker / infra).

---

## Step 1 — Cluster version: healthy and not mid-upgrade?

```bash
oc get clusterversion
```

**Expected output** *(requires a cluster — representative of healthy OCP 4.18):*

```
NAME      VERSION   AVAILABLE   PROGRESSING   SINCE   STATUS
version   4.18.20   True        False         12d     Cluster version is 4.18.20
```

> **Narrate:** **AVAILABLE=True**, **PROGRESSING=False** — healthy and *not* upgrading.
> If PROGRESSING were True we'd stop here: never layer a change on an in-flight upgrade.

---

## Step 2 — Cluster Operators: anyone degraded?

```bash
oc get clusteroperators
oc get co -o jsonpath='{range .items[?(@.status.conditions[?(@.type=="Degraded")].status=="True")]}{.metadata.name}{"\n"}{end}'
```

**Expected output** *(requires a cluster — representative):*

```
NAME             VERSION   AVAILABLE   PROGRESSING   DEGRADED   SINCE
authentication   4.18.20   True        False         False      12d
etcd             4.18.20   True        False         False      40d
ingress          4.18.20   True        False         False      12d
image-registry   4.18.20   True        False         False      40d
monitoring       4.18.20   True        False         False      12d
...
                                  <-- (second command: no output = nobody Degraded)
```

> **Narrate:** ~30 operators, all **AVAILABLE=True / DEGRADED=False**. The jsonpath
> filter prints only *degraded* operators — empty is exactly what we want. A name here
> would be our first lead.

---

## Step 3 — Nodes: all Ready? (and read the topology)

```bash
oc get nodes
echo "control-plane: $(oc get nodes -l node-role.kubernetes.io/master --no-headers | wc -l)"
echo "workers:       $(oc get nodes -l node-role.kubernetes.io/worker --no-headers | wc -l)"
```

**Expected output** *(requires a cluster — representative):*

```
NAME            STATUS   ROLES                  AGE   VERSION
ocp4-master-0   Ready    control-plane,master   40d   v1.31.7
ocp4-master-1   Ready    control-plane,master   40d   v1.31.7
ocp4-master-2   Ready    control-plane,master   40d   v1.31.7
ocp4-worker-0   Ready    worker                 40d   v1.31.7
ocp4-worker-1   Ready    worker                 40d   v1.31.7
control-plane: 3
workers:       2
```

> **Narrate:** Every node **Ready**, topology is **3 control plane + 2 workers** (add
> `infra` if labelled). Three commands, full health picture — this is the green light.

---

## Step 4 — Rehearse triage (what red looks like)

```bash
# If an operator were Degraded:
oc describe co ingress | sed -n '/Conditions:/,/Extension/p'
# Recent cluster-wide activity (failures bubble up here):
oc get events -A --sort-by=.lastTimestamp | tail -15
# Live pressure:
oc adm top nodes
```

**Expected output** *(requires a cluster — representative):*

```
Conditions:
  Type           Status   Reason             Message
  Available      True     IngressAvailable   The ingress controller is available
  Progressing    False    AsExpected
  Degraded       False    AsExpected

NAME            CPU(cores)   CPU%   MEMORY(bytes)   MEMORY%
ocp4-worker-0   289m         7%     3998Mi          26%
ocp4-master-0   612m         17%    5123Mi          34%
```

> **Narrate:** When DEGRADED flips True, the **Conditions message** names the cause.
> `oc get events` surfaces recent failures; `oc adm top` finds a hot node. For a NotReady
> node you'd add `oc describe node <n>` and `oc adm node-logs <n>`.

---

## Step 5 — Bundle diagnostics for support (don't fully run in class)

```bash
oc adm must-gather --dest-dir=/tmp/mg     # collects logs/state into a bundle
```

**Expected output** *(requires a cluster — representative, abbreviated):*

```
[must-gather] OUT Using must-gather plug-in image: quay.io/.../must-gather
[must-gather] OUT namespace/openshift-must-gather-xxxx created
[must-gather] OUT gather logs ...
Reprinting Cluster State:
...
```

> **Narrate:** `must-gather` spins up a short-lived pod that scrapes a full diagnostic
> bundle — the **first artifact** a Red Hat support case asks for. We'll cut it short in
> class; it can take several minutes.

---

## Cleanup

Read-only demo — nothing to clean up (delete the `must-gather` output dir if you ran
Step 5: `rm -rf /tmp/mg`).

---

## Wrap-up questions to pose

1. What are the **three commands**, and what does each tell you?
2. `clusterversion` shows PROGRESSING=True — do you proceed with tonight's release?
3. An operator is DEGRADED — what's your next command, and what are you reading?
4. Where does the same `oc get nodes` tell you the cluster **topology**?

---

> **◐ Partially verified:** every command **requires a live OpenShift cluster** and was
> **not** runnable in the authoring environment (no cluster connection). Output is
> **representative of a healthy OpenShift 4.18** cluster; run the commands live to
> capture your real version, operator board, and node list. Syntax follows the
> `oc`/`kubectl` 4.x reference; nothing is presented as independently verified.
</content>
