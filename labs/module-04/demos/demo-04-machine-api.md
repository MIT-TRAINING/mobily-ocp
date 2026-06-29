# Demo 4 — The Machine API: Infrastructure as Reconcile Loop

> **Scenario:** The CDR pipeline is growing and we need to plan **CDR-worker
> capacity**. We'll look behind the nodes at the **Machine API** — the subsystem that
> turns "I want N workers" into provisioned VMs running RHCOS — correlate each
> **Machine** to the **Node** it became, and (admin-only) scale a **MachineSet** to
> watch a node appear. The punchline: the *same reconcile loop* that manages pods
> manages your infrastructure.

| | |
|---|---|
| **Concepts reinforced** | `MachineSet` (ReplicaSet for nodes) · `Machine` · Machine→Node correlation · provider template · scaling · node self-healing · autoscaling |
| **Maps to** | Guide §4, §10 · Visualization 04 · Exercise 4 |
| **Time** | ~25 minutes |
| **Cluster** | Shared OCP 4.18 with Machine API (installer-provisioned infra) |

---

> **⎈ Kubernetes equivalent:** `Machine`/`MachineSet` are **OpenShift/Cluster-API**
> kinds — upstream Kubernetes has no built-in node-provisioning API. But the *shape*
> is deliberately familiar: a MachineSet is to Machines what a **ReplicaSet** is to
> Pods (Module 3). The verbs (`get`, `scale`, `describe`) are pure `kubectl`.

> ⚠️ **Availability & permissions:** the Machine API exists on **installer-provisioned
> (IPI)** clusters on supported clouds/bare-metal; a UPI/bare-metal cluster may not
> expose it — fall back to Visualization 04. Reads are cluster-scope; **scaling is
> admin-only** (Step 4 is an instructor demo).

## Talking points to open with

- Nodes are **cattle, not pets**. You don't click "launch instance" in the cloud
  console — you declare a desired count and the cluster provisions VMs that boot RHCOS
  and join automatically.
- `Machine` = one host that should exist. `MachineSet` = a template + a count. Same
  desired-state-and-reconcile idea, one layer below pods.
- All of this is driven by the **machine-api** Cluster Operator we saw green in Demo 3.

---

## Step 1 — The MachineSets (the "ReplicaSets for nodes")

```bash
oc get machinesets -n openshift-machine-api
```

**Expected output** *(requires an IPI cluster — representative, AWS):*

```
NAME                       DESIRED   CURRENT   READY   AVAILABLE   AGE
ocp4-abcde-worker-us-1a    2         2         2       2           40d
ocp4-abcde-worker-us-1b    1         1         1       1           40d
```

> **Narrate:** Read these columns exactly like a ReplicaSet — **DESIRED vs READY**.
> Each MachineSet is pinned to an availability zone; together they spread workers
> across failure domains. Change DESIRED and the cluster makes it real.

---

## Step 2 — The Machines (the hosts themselves)

```bash
oc get machines -n openshift-machine-api
```

**Expected output** *(requires a cluster — representative):*

```
NAME                             PHASE     TYPE        REGION      ZONE         AGE
ocp4-abcde-master-0              Running   m5.xlarge   us-east-1   us-east-1a   40d
ocp4-abcde-master-1              Running   m5.xlarge   us-east-1   us-east-1b   40d
ocp4-abcde-master-2              Running   m5.xlarge   us-east-1   us-east-1c   40d
ocp4-abcde-worker-us-1a-7h2xq    Running   m5.large    us-east-1   us-east-1a   40d
ocp4-abcde-worker-us-1b-k9p4w    Running   m5.large    us-east-1   us-east-1b   40d
```

> **Narrate:** Each **Machine** is the cluster's declarative claim on one VM —
> instance **type**, **region**, **zone**, and a **PHASE** (Provisioning →
> Provisioned → Running). The masters are Machines too. The random suffix
> (`-7h2xq`) is stamped per VM from the MachineSet template.

---

## Step 3 — Correlate a Machine to the Node it became

```bash
for M in $(oc get machines -n openshift-machine-api -o jsonpath='{.items[*].metadata.name}'); do
  oc get machine "$M" -n openshift-machine-api \
    -o jsonpath='machine='"$M"' -> node={.status.nodeRef.name} ('{.status.phase}')'{"\n"}
done
```

**Expected output** *(requires a cluster — representative):*

```
machine=ocp4-abcde-worker-us-1a-7h2xq -> node=ocp4-abcde-worker-us-1a-7h2xq (Running)
machine=ocp4-abcde-worker-us-1b-k9p4w -> node=ocp4-abcde-worker-us-1b-k9p4w (Running)
...
```

> **Narrate:** The Machine's `status.nodeRef` links it to the **Node** object from
> Demo 2 — same name. That's the join between *infrastructure* (the VM) and
> *Kubernetes* (the schedulable node). Provisioning flows left-to-right: Machine →
> RHCOS boots via Ignition → kubelet registers → Node Ready.

---

## Step 4 — (Admin-only) Scale a MachineSet and watch a node appear

```bash
MS=ocp4-abcde-worker-us-1a
oc scale machineset "$MS" -n openshift-machine-api --replicas=3   # +1
# second terminal: watch the new Machine progress and a Node join
oc get machines -n openshift-machine-api -w
oc get nodes -w
oc scale machineset "$MS" -n openshift-machine-api --replicas=2   # scale back
```

**Expected output** *(requires admin on an IPI cluster — representative):*

```
machineset.machine.openshift.io/ocp4-abcde-worker-us-1a scaled
# new machine: Provisioning -> Provisioned -> Running   (~3-6 min on a cloud)
# new node:    NotReady -> Ready
machineset.machine.openshift.io/ocp4-abcde-worker-us-1a scaled
```

> **Narrate:** *Predict first:* it's the **ReplicaSet reconcile loop**, one layer
> down. We changed DESIRED to 3; the machine-api Operator called AWS, a VM booted
> RHCOS, the kubelet registered, and a Node went Ready — **no console clicking**.
> Delete a Machine instead and the set provisions a replacement: that's **worker-node
> self-healing**. Add a **ClusterAutoscaler** and *pending pods* trigger this
> automatically (Visualization 04).

---

## Step 5 — Where this sits in the platform

```bash
oc get co machine-api
```

**Expected output** *(requires a cluster — representative):*

```
NAME          VERSION   AVAILABLE   PROGRESSING   DEGRADED   SINCE
machine-api   4.18.20   True        False         False      40d
```

> **Narrate:** Full circle to Demo 3 — the whole Machine API is itself run by a
> **Cluster Operator**. Infrastructure management is just another reconcile loop the
> CVO keeps healthy. *Pods (ReplicaSet) → apps (Operators) → platform (Cluster
> Operators) → infrastructure (Machine API)* — one idea, applied at every layer.

---

## Cleanup

Nothing to clean up if you scaled back in Step 4 (`--replicas=2`). Confirm:

```bash
oc get machinesets -n openshift-machine-api    # DESIRED back to original
```

---

## Wrap-up questions to pose

1. A MachineSet is the "ReplicaSet for nodes." Use that to explain what happens when
   you **delete a Machine**.
2. You scaled nodes with the **same `oc scale`** verb as a Deployment. What does that
   say about OpenShift's design?
3. Trace the lifecycle from `oc scale` to a schedulable Node — name each stage.
4. When you run `oc adm upgrade`, which **three** subsystems from this module move, and
   who drives each?

---

> **◐ Partially verified:** All `oc get machines/machinesets` and
> `oc scale machineset` commands **require a live OpenShift cluster with the Machine
> API** (installer-provisioned infra) and could not be run in the authoring
> environment. Output is **representative of an OpenShift 4.18 IPI cluster on AWS**;
> names, instance types, and zones vary by cluster/provider, and scaling is admin-only.
> Command syntax follows the `oc` 4.x reference; nothing is presented as independently
> verified.
</content>
