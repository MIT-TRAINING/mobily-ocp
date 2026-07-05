# Exercise 4 — Machine API & Console Capstone

> **Scenario:** Capacity planning for the **CDR-worker** fleet. You'll inspect the
> **Machine API** (the infrastructure behind your nodes), correlate **Machines →
> Nodes**, tour the same facts in the **web console**, and finish by writing a
> one-paragraph **architecture brief** that ties together everything in Module 4.

| | |
|---|---|
| **Practice** | `oc get machines/machinesets`, Machine↔Node correlation, console Admin tour, synthesis |
| **Maps to** | Guide §4, §10, §11 · Visualizations 01–04 · Demo 4 |
| **Difficulty** | ⭐⭐⭐ Advanced (capstone) · ~30–35 min · **needs a real cluster** |

> ⚠️ **Read-mostly.** On the **shared cluster** you likely have **read-only** access to
> Machines/MachineSets (scaling is admin/instructor-only). The **scale** step (Task 4)
> is marked *instructor/admin-only* — read it, predict the outcome, watch it demoed. On
> the **Sandbox**, Machines aren't visible at all; use the console capstone (Tasks 5–6).

---

## Tasks

1. List the **MachineSets** (`oc get machinesets -n openshift-machine-api`) and the
   **Machines** (`oc get machines -n openshift-machine-api`). Note each MachineSet's
   **desired/current/ready** counts.
2. **Correlate** a Machine to the **Node** it became — same name, and the Machine's
   `status.nodeRef` points at the node.
3. Identify which MachineSet backs the **worker** nodes and read its instance
   **type/region** (provider spec) — this is the template each new VM is stamped from.
4. **(Instructor/admin-only)** Scale a worker MachineSet up by one and watch a new
   **Machine → RHCOS boot → Node Ready** appear; then scale back. *Predict first:* what
   reconcile loop is at work?
5. **Console tour (Administrator perspective):** open **Compute → Nodes**,
   **Compute → MachineSets/Machines**, **Administration → Cluster Settings** (the
   version + update channel), and **Home → Overview**. Find the *same* facts you read
   on the CLI.
6. **Capstone write-up:** in 5–6 sentences, explain to a new teammate **how OpenShift
   extends Kubernetes** — referencing RHCOS, CRI-O, the Operator pattern (Cluster
   Operators + CVO), and the Machine API. (A model answer is in the solution.)

> **Hint (Task 2):** `oc get machine <m> -n openshift-machine-api -o jsonpath='{.status.nodeRef.name}{"\n"}'`
> gives the node a Machine became.

> **Hint (Task 4):** `oc scale machineset <name> -n openshift-machine-api --replicas=N`
> — the *same verb* you used to scale a Deployment in Module 3, one layer down.

---

## Validation

```bash
# Task 1 — MachineSets with their counts, and the Machines
oc get machinesets -n openshift-machine-api
oc get machines    -n openshift-machine-api

# Task 2 — a Machine and the Node it became (should match)
M=$(oc get machines -n openshift-machine-api -o jsonpath='{.items[0].metadata.name}')
oc get machine "$M" -n openshift-machine-api -o jsonpath='machine={.metadata.name} node={.status.nodeRef.name}{"\n"}'

# Task 4 (admin) — after scaling, ready count rises then returns
oc get machinesets -n openshift-machine-api
```

---

## Reflection

- `Machine`/`MachineSet` are to nodes what `Pod`/`ReplicaSet` are to containers. Use
  that analogy to explain **worker-node self-healing** (delete a Machine → ?).
- You scaled a MachineSet with the **same `oc scale`** verb as a Deployment. What does
  that tell you about OpenShift's design philosophy?
- Tie it together: when you `oc adm upgrade`, **three subsystems** from this module all
  move — name them and who drives each (CVO, Cluster Operators, MCO + Machine API).

---

<details>
<summary><strong>✅ Solution</strong> (try the tasks first)</summary>

```bash
# 1. MachineSets and Machines
oc get machinesets -n openshift-machine-api
oc get machines    -n openshift-machine-api -o wide

# 2. Machine -> Node correlation
for M in $(oc get machines -n openshift-machine-api -o jsonpath='{.items[*].metadata.name}'); do
  oc get machine "$M" -n openshift-machine-api \
    -o jsonpath='machine='"$M"' node={.status.nodeRef.name} phase={.status.phase}{"\n"}'
done

# 3. Which MachineSet backs workers + its provider template
oc get machineset -n openshift-machine-api \
  -o custom-columns=NAME:.metadata.name,DESIRED:.spec.replicas,READY:.status.readyReplicas

# 4. (admin-only) Scale up by one, watch a Node appear, scale back
MS=$(oc get machineset -n openshift-machine-api -o jsonpath='{.items[0].metadata.name}')
oc scale machineset "$MS" -n openshift-machine-api --replicas=3   # +1
watch oc get machines -n openshift-machine-api                    # Provisioning -> Provisioned -> Running
oc scale machineset "$MS" -n openshift-machine-api --replicas=2   # back

# 5. Console: Compute → MachineSets/Machines/Nodes; Administration → Cluster Settings; Home → Overview
```

**Representative output** *(requires a cluster — typical IPI cluster on a cloud):*

```
$ oc get machinesets -n openshift-machine-api
NAME                       DESIRED   CURRENT   READY   AVAILABLE   AGE
ocp4-abcde-worker-us-1a    2         2         2       2           40d
ocp4-abcde-worker-us-1b    1         1         1       1           40d

$ oc get machines -n openshift-machine-api
NAME                             PHASE     TYPE        REGION     ZONE        AGE
ocp4-abcde-master-0              Running   m5.xlarge   us-east-1  us-east-1a  40d
ocp4-abcde-worker-us-1a-7h2xq    Running   m5.large    us-east-1  us-east-1a  40d
ocp4-abcde-worker-us-1b-k9p4w    Running   m5.large    us-east-1  us-east-1b  40d

$ oc get machine ocp4-abcde-worker-us-1a-7h2xq -n openshift-machine-api \
    -o jsonpath='machine={.metadata.name} node={.status.nodeRef.name}{"\n"}'
machine=ocp4-abcde-worker-us-1a-7h2xq node=ocp4-abcde-worker-us-1a-7h2xq
```

**Model answer (Task 6):**
> OpenShift *is* certified Kubernetes, so every Pod, Deployment, and Service we learned
> still works — but it's delivered as a finished, self-managing product. The nodes run
> **RHCOS**, an immutable OS we configure declaratively (MachineConfig + MCO), not by
> SSH; the container runtime is **CRI-O**, a lean Kubernetes-only runtime versioned with
> the cluster. The platform runs *itself* through the **Operator pattern**: ~30 **Cluster
> Operators** each own a slice (ingress, registry, auth, monitoring…) and the **Cluster
> Version Operator** drives them all to one signed release. The **Machine API** applies
> the same reconcile loop to infrastructure — `MachineSet`/`Machine` are the
> `ReplicaSet`/`Pod` of cloud VMs — so nodes self-heal and autoscale. That's why an
> upgrade is one command: the CVO, the Cluster Operators, and the MCO + Machine API move
> the OS, runtime, Kubernetes, and platform services together as one tested unit.

**Key point:** the *same reconcile loop* recurs at every layer — Pods (RS),
applications (Operators), the platform (Cluster Operators + CVO), and infrastructure
(Machine API). Internalise that and OpenShift stops being 40 components and becomes
*one idea applied consistently*.
</details>

---

> **◐ Partially verified:** All `oc get machines/machinesets`/`oc scale machineset`
> commands **require a live OpenShift cluster** (with Machine API / IPI) and could not be
> run in the authoring sandbox. Output shown is **representative of an OpenShift 4.18 IPI
> cluster**; run the commands on the shared cluster (scaling is admin-only) for your real
> values. Command syntax follows the `oc` 4.x reference; no output is presented as
> independently verified.
