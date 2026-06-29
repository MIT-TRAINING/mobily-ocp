# Exercise 2 — Explore the Cluster Architecture

> **Scenario:** Mobily's CDR (Call Detail Record) pipeline runs on this cluster and
> you've been asked to **document the platform** it sits on: how many nodes, which
> **roles**, what **operating system** (you suspect RHCOS), and which **container
> runtime** (CRI-O). You'll read it all straight from the API.

| | |
|---|---|
| **Practice** | `oc get nodes -o wide`, node roles via labels, RHCOS image & CRI-O version, `oc describe node` |
| **Maps to** | Guide §4, §6, §7 · Visualizations 02 & 04 · Demo 2 |
| **Difficulty** | ⭐⭐ Intermediate · ~25 min · **needs a real cluster** (not Sandbox) |

> ⚠️ **Cluster-admin (or shared-cluster) only.** Reading nodes requires cluster-level
> permissions you **don't** have on the Developer Sandbox. On the Sandbox, follow your
> instructor's cluster output for this one — the goal is to *read* the architecture.

---

## Tasks

1. List all **nodes** with extra detail (`-o wide`) and note the **ROLES**,
   **OS-IMAGE**, **KERNEL-VERSION**, and **CONTAINER-RUNTIME** columns.
2. Confirm the **OS is RHCOS** and the **runtime is CRI-O** straight from the columns.
3. Count nodes **by role** — how many `control-plane`/`master`, how many `worker`?
4. Show that node roles are just **labels**: list the `node-role.kubernetes.io/*`
   labels on the nodes.
5. `oc describe node <a-worker>` and find: its **taints**, **capacity** (cpu/memory),
   and the **System Info** block (OS image, kernel, kubelet, container runtime).
6. Show that a **control-plane node carries a `NoSchedule` taint** (why your app pods
   normally avoid it).
7. *(Optional, needs metrics)* `oc adm top nodes` to see live CPU/memory per node.

> **Hint (Task 3):** `oc get nodes -l node-role.kubernetes.io/worker` filters by role
> label; pipe `--no-headers | wc -l` to count.

> **Hint (Task 5):** jump straight to the runtime with
> `oc get node <n> -o jsonpath='{.status.nodeInfo.containerRuntimeVersion}{"\n"}'`.

---

## Validation

```bash
# Tasks 1-2 — OS column says RHCOS, runtime column says cri-o
oc get nodes -o wide

# Task 2 (precise) — runtime + OS image straight from nodeInfo
oc get nodes -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.nodeInfo.osImage}{"\t"}{.status.nodeInfo.containerRuntimeVersion}{"\n"}{end}'

# Task 3 — count workers
oc get nodes -l node-role.kubernetes.io/worker --no-headers | wc -l

# Task 6 — control-plane taint
oc get nodes -l node-role.kubernetes.io/master \
  -o jsonpath='{.items[0].spec.taints}{"\n"}'
```

---

## Reflection

- The OS-IMAGE says *Red Hat Enterprise Linux CoreOS*. Given §6, **how** would you
  change a kernel argument on these nodes — and what would you **not** do?
- The runtime is `cri-o`, not `docker`. From §7, name two reasons OpenShift chose it.
- Roles are labels, not different binaries. What *practical* effect does the
  control-plane `NoSchedule` taint have on where the CDR pods land?

---

<details>
<summary><strong>✅ Solution</strong> (try the tasks first)</summary>

```bash
# 1-2. Wide listing — read ROLES / OS-IMAGE / CONTAINER-RUNTIME
oc get nodes -o wide

# 2. Precise: name, OS image, runtime
oc get nodes -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.nodeInfo.osImage}{"\t"}{.status.nodeInfo.containerRuntimeVersion}{"\n"}{end}'

# 3. Count by role
echo "control-plane: $(oc get nodes -l node-role.kubernetes.io/master --no-headers | wc -l)"
echo "workers:       $(oc get nodes -l node-role.kubernetes.io/worker --no-headers | wc -l)"

# 4. Role labels are how roles are expressed
oc get nodes --show-labels | tr ',' '\n' | grep node-role

# 5. Deep-dive one worker
WORKER=$(oc get nodes -l node-role.kubernetes.io/worker -o jsonpath='{.items[0].metadata.name}')
oc describe node "$WORKER" | sed -n '/Taints:/p; /Capacity:/,/Allocatable:/p; /System Info:/,/Container Runtime/p'

# 6. Control-plane taint
oc get nodes -l node-role.kubernetes.io/master -o jsonpath='{.items[0].spec.taints}{"\n"}'

# 7. Live usage (needs metrics)
oc adm top nodes
```

**Representative output** *(requires a cluster — values are typical of OpenShift 4.18):*

```
$ oc get nodes -o wide
NAME                          STATUS   ROLES                  AGE   VERSION   OS-IMAGE                                                       KERNEL-VERSION                 CONTAINER-RUNTIME
ocp4-master-0                 Ready    control-plane,master   40d   v1.31.7   Red Hat Enterprise Linux CoreOS 418.94.202506...               5.14.0-427.el9_4.x86_64        cri-o://1.31.7-...
ocp4-master-1                 Ready    control-plane,master   40d   v1.31.7   Red Hat Enterprise Linux CoreOS 418.94.202506...               5.14.0-427.el9_4.x86_64        cri-o://1.31.7-...
ocp4-master-2                 Ready    control-plane,master   40d   v1.31.7   Red Hat Enterprise Linux CoreOS 418.94.202506...               5.14.0-427.el9_4.x86_64        cri-o://1.31.7-...
ocp4-worker-0                 Ready    worker                 40d   v1.31.7   Red Hat Enterprise Linux CoreOS 418.94.202506...               5.14.0-427.el9_4.x86_64        cri-o://1.31.7-...
ocp4-worker-1                 Ready    worker                 40d   v1.31.7   Red Hat Enterprise Linux CoreOS 418.94.202506...               5.14.0-427.el9_4.x86_64        cri-o://1.31.7-...

$ oc get nodes -l node-role.kubernetes.io/master \
    -o jsonpath='{.items[0].spec.taints}{"\n"}'
[{"effect":"NoSchedule","key":"node-role.kubernetes.io/master"}]
```

**Key point:** the API tells you everything — three things to internalize: **OS =
RHCOS** (immutable, change it via MachineConfig — *never* SSH-and-edit), **runtime =
CRI-O** (Kubernetes-only, versioned with the cluster), and **roles = labels + taints**
on an otherwise identical stack. The control-plane `NoSchedule` taint keeps your CDR
pods on workers unless they explicitly tolerate it.
</details>

---

> **◐ Partially verified:** Every command **requires a live OpenShift cluster** and
> was **not** runnable in the authoring sandbox (no cluster connection). Output shown is
> **representative of OpenShift 4.18 / Kubernetes 1.31** — run the commands on the
> shared cluster to capture your own node names, RHCOS build, and CRI-O version. The
> command *syntax* follows the `oc`/`kubectl` 4.x reference; no output is presented as
> independently verified.
</content>
