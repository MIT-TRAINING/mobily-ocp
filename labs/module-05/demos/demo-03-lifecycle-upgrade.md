# Demo 3 — Cluster Lifecycle & Upgrade (report/dry-run)

> **Scenario:** A CVE advisory lands and Mobily must move to **4.18.21**. We walk the
> full upgrade lifecycle — confirm health, choose the right **channel**, read the
> recommended targets, and explain exactly what happens when the **CVO** drives the
> upgrade — **without actually upgrading the shared class cluster** (we use the
> report-only forms).

| | |
|---|---|
| **Concepts reinforced** | update channels (candidate/fast/stable/eus) · `oc adm upgrade` · CVO walk · MCO drained reboots · pre/post health |
| **Maps to** | Guide §6 · Visualization 04 (upgrade) · Exercise 3 |
| **Time** | ~25 minutes |
| **Cluster** | Shared OCP 4.18 — **report-only**; a real upgrade needs cluster-admin |

---

> **⎈ Kubernetes equivalent:** none — self-upgrade is an OpenShift capability. Vanilla
> Kubernetes upgrades are a manual, component-by-component affair (`kubeadm upgrade`,
> separate node and addon steps).

> ⚠️ **Do NOT trigger a real upgrade on the class cluster.** Every command here is
> *report-only* (`oc adm upgrade` with no `--to`, channel reads). The actual
> `--to=` step is shown for reference but **not executed** in class.

## Talking points to open with

- An OpenShift upgrade is **one supervised command** — because the CVO moves OS +
  runtime + Kubernetes + platform services together as one tested unit.
- **You** still own the decisions: health-green first, the right channel, the right
  target, and verify after.
- Worker reboots are **drained**, so multi-replica apps stay up.

---

## Step 1 — Pre-flight: is the cluster green?

```bash
oc get clusterversion
oc get clusteroperators | grep -E 'DEGRADED|True .* True' || echo "no degraded operators"
oc get nodes | grep -v ' Ready ' || echo "all nodes Ready"
```

**Expected output** *(requires a cluster — representative):*

```
NAME      VERSION   AVAILABLE   PROGRESSING   SINCE   STATUS
version   4.18.20   True        False         12d     Cluster version is 4.18.20
no degraded operators
all nodes Ready
```

> **Narrate:** Same three-command check as Demo 1 — the **gate** before any upgrade.
> Green here, or we stop and fix first.

---

## Step 2 — See the channel and recommended targets

```bash
oc adm upgrade
```

**Expected output** *(requires a cluster — representative):*

```
Cluster version is 4.18.20

Upstream is unset, so the cluster will use an appropriate default.
Channel: stable-4.18 (available channels: candidate-4.18, eus-4.18, fast-4.18, stable-4.18)

Recommended updates:
  VERSION   IMAGE
  4.18.21   quay.io/openshift-release-dev/ocp-release@sha256:...
  4.18.22   quay.io/openshift-release-dev/ocp-release@sha256:...
```

> **Narrate:** `oc adm upgrade` with no flags is **report-only**. We're on
> **stable-4.18** — the right channel for production. **4.18.21** is recommended; the
> SHA-pinned **release image** is the single payload the CVO will roll out.

---

## Step 3 — Choosing / confirming the channel

```bash
oc adm upgrade channel stable-4.18      # confirm production channel (no version change)
```

**Expected output** *(requires admin — representative):*

```
(no output; channel set/confirmed)  — verify with: oc get clusterversion -o jsonpath='{.spec.channel}{"\n"}'  -> stable-4.18
```

> **Narrate:** Channels are the risk dial — **candidate** (test), **fast** (early),
> **stable** (production), **eus** (fewest upgrades). We keep Mobily prod on **stable**.

---

## Step 4 — What the real upgrade would do (reference — NOT run in class)

```bash
# NOT executed on the class cluster:
oc adm upgrade --to=4.18.21
watch oc get clusterversion          # PROGRESSING=True until complete
oc get clusteroperators              # each operator moves to 4.18.21 in dependency order
oc get mcp                           # worker pool UPDATING as the MCO reboots nodes
```

**Expected output** *(representative of a real upgrade):*

```
Requested update to 4.18.21
# clusterversion: PROGRESSING=True, "Working towards 4.18.21: N% complete"
# clusteroperators: kube-apiserver -> etcd -> ... each to 4.18.21
# mcp worker: UPDATED=False/UPDATING=True, nodes drain+reboot one at a time
```

> **Narrate:** The **CVO** sets the new release image and walks every Cluster Operator
> in dependency order; the **MCO** rolls RHCOS node-by-node with drains. Control plane
> first, then workers. Hours, not a maintenance weekend — and the subscriber-api stays
> up throughout.

---

## Step 5 — Post-upgrade verification

```bash
oc get clusterversion        # VERSION 4.18.21, AVAILABLE=True, PROGRESSING=False
oc get clusteroperators      # all at 4.18.21, none DEGRADED
oc get nodes                 # all Ready, kubelet version bumped
```

**Expected output** *(representative):*

```
NAME      VERSION   AVAILABLE   PROGRESSING   SINCE   STATUS
version   4.18.21   True        False         20m     Cluster version is 4.18.21
```

> **Narrate:** Verification is the **same health check** as the pre-flight — you're not
> done when the command returns, you're done when it's **green again** at the new
> version.

---

## Cleanup

Report/dry-run demo — nothing created, nothing to clean up (we did **not** run the
real `--to=` upgrade on the class cluster).

---

## Wrap-up questions to pose

1. Which channel for production, and how do the four channels differ?
2. What single command starts an upgrade, and what does the CVO then do?
3. Why do multi-replica apps stay up during worker reboots?
4. What's the *gate* before an upgrade and the *check* after — and why are they the
   same three commands?

---

> **◐ Partially verified:** all commands **require a live OpenShift cluster** and Step 4
> would change the cluster (deliberately **not run**). Output is **representative of
> OpenShift 4.18**; run the report-only forms (`oc adm upgrade`, channel reads) on the
> shared cluster for real values. Nothing is presented as independently verified.

> **Gating validated (2026-07-05, as learner25):** the cluster-scope actions in this demo
> returned `Error from server (Forbidden)` for the normal user **learner25** — confirming
> it is correctly **cluster-admin / instructor-led**, as marked. Reproduce the live output
> with an admin/cluster-reader login.
