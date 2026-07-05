# Demo 2 — Explore the Nodes: RHCOS & CRI-O

> **Scenario:** Mobily's **CDR pipeline** runs on this cluster and we owe the
> change-management board a one-page map of the platform: how many nodes, which
> **roles**, what **operating system** (we expect RHCOS), and which **container
> runtime** (CRI-O). We'll read every fact straight from the Kubernetes API — no SSH,
> because on RHCOS you *don't* SSH in to poke around.

| | |
|---|---|
| **Concepts reinforced** | node roles (control-plane/worker/infra) · roles = labels + taints · RHCOS OS image · CRI-O runtime · `describe node` · immutable OS |
| **Maps to** | Guide §4, §6, §7 · Visualizations 02 & 04 · Exercise 2 |
| **Time** | ~25 minutes |
| **Cluster** | Shared OCP 4.18 — **needs cluster-scope read** (not Sandbox) |

---

> **⎈ Kubernetes equivalent:** every command here is **pure `kubectl`** —
> `get nodes`, `describe node`, `-o jsonpath`. Nothing OpenShift-specific in the verbs;
> what's OpenShift-specific is *what you find*: RHCOS and CRI-O on every node.

> ⚠️ **Permissions:** reading nodes is cluster-scope. Instructor runs this as admin /
> cluster-reader. Sandbox participants watch the instructor's screen.

## Talking points to open with

- Every node — control-plane *and* worker — runs the **same stack**: RHCOS → CRI-O →
  kubelet → pods. Roles are just **labels + taints**, not different software.
- The OS is **immutable**. We're *reading* it; to *change* it you'd write a
  MachineConfig (Demo-adjacent concept), never `ssh node && vi`.
- The runtime is **CRI-O**, versioned with the cluster — not Docker.

---

## Step 1 — The cluster at a glance

```bash
oc get nodes -o wide
```

**Expected output** *(requires a cluster — representative of OCP 4.18):*

```
NAME            STATUS   ROLES                  AGE   VERSION   OS-IMAGE                                       KERNEL-VERSION            CONTAINER-RUNTIME
ocp4-master-0   Ready    control-plane,master   40d   v1.31.7   Red Hat Enterprise Linux CoreOS 418.94...      5.14.0-427.el9_4.x86_64   cri-o://1.31.7-...
ocp4-master-1   Ready    control-plane,master   40d   v1.31.7   Red Hat Enterprise Linux CoreOS 418.94...      5.14.0-427.el9_4.x86_64   cri-o://1.31.7-...
ocp4-master-2   Ready    control-plane,master   40d   v1.31.7   Red Hat Enterprise Linux CoreOS 418.94...      5.14.0-427.el9_4.x86_64   cri-o://1.31.7-...
ocp4-worker-0   Ready    worker                 40d   v1.31.7   Red Hat Enterprise Linux CoreOS 418.94...      5.14.0-427.el9_4.x86_64   cri-o://1.31.7-...
ocp4-worker-1   Ready    worker                 40d   v1.31.7   Red Hat Enterprise Linux CoreOS 418.94...      5.14.0-427.el9_4.x86_64   cri-o://1.31.7-...
```

> **Narrate:** Three big facts in one screen. **ROLES** — three control-plane, the
> rest workers. **OS-IMAGE** — *Red Hat Enterprise Linux CoreOS* on every line.
> **CONTAINER-RUNTIME** — `cri-o://`, not docker. The `VERSION` column is the embedded
> Kubernetes (1.31.7), matching the OCP 4.18 we saw in Demo 1.

---

## Step 2 — Pull OS + runtime precisely (nodeInfo)

```bash
oc get nodes -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.nodeInfo.osImage}{"\t"}{.status.nodeInfo.containerRuntimeVersion}{"\n"}{end}'
```

**Expected output** *(requires a cluster — representative):*

```
ocp4-master-0   Red Hat Enterprise Linux CoreOS 418.94.202506...   cri-o://1.31.7-6.rhaos4.18...
ocp4-worker-0   Red Hat Enterprise Linux CoreOS 418.94.202506...   cri-o://1.31.7-6.rhaos4.18...
...
```

> **Narrate:** `status.nodeInfo` is the authoritative record. Note the CRI-O version
> (`1.31.x`) tracks the cluster's Kubernetes minor — that lockstep is exactly why
> OpenShift chose CRI-O over "which Docker is compatible?" guesswork.

---

## Step 3 — Count nodes by role (roles are labels)

```bash
echo "control-plane: $(oc get nodes -l node-role.kubernetes.io/master --no-headers | wc -l)"
echo "workers:       $(oc get nodes -l node-role.kubernetes.io/worker --no-headers | wc -l)"
oc get nodes --show-labels | tr ',' '\n' | grep node-role | sort -u
```

**Expected output** *(requires a cluster — representative):*

```
control-plane: 3
workers:       2
node-role.kubernetes.io/master=
node-role.kubernetes.io/worker=
```

> **Narrate:** We filtered by **label**, not by a special "node type" field — because
> there isn't one. `node-role.kubernetes.io/master` and `/worker` are *just labels* on
> an identical RHCOS+CRI-O stack. That's the whole "roles are labels" idea made
> concrete. Infra nodes, when present, are workers with an extra `infra` label.

---

## Step 4 — Why your CDR pods avoid the control plane

```bash
oc get nodes -l node-role.kubernetes.io/master \
  -o jsonpath='{.items[0].spec.taints}{"\n"}'
```

**Expected output** *(requires a cluster — representative):*

```
[{"effect":"NoSchedule","key":"node-role.kubernetes.io/master"}]
```

> **Narrate:** The control-plane nodes carry a **`NoSchedule` taint**. The scheduler
> won't place ordinary pods there unless they explicitly *tolerate* it — so the CDR
> workload stays on worker nodes and never competes with etcd/the API server. Labels
> say "what I am"; taints say "who's allowed here."

---

## Step 5 — Deep-dive one worker

```bash
WORKER=$(oc get nodes -l node-role.kubernetes.io/worker -o jsonpath='{.items[0].metadata.name}')
oc describe node "$WORKER" | sed -n '/System Info:/,/Container Runtime Version/p'
```

**Expected output** *(requires a cluster — representative):*

```
System Info:
  Machine ID:                 ...
  Kernel Version:             5.14.0-427.el9_4.x86_64
  OS Image:                   Red Hat Enterprise Linux CoreOS 418.94.202506...
  Operating System:           linux
  Architecture:               amd64
  Container Runtime Version:  cri-o://1.31.7-6.rhaos4.18...
  Kubelet Version:            v1.31.7
```

> **Narrate:** `describe node` is the full datasheet — kernel, RHCOS image, **CRI-O**
> runtime, and the **kubelet** (the node agent that drives CRI-O over the CRI). This is
> the per-node stack from Visualization 02, printed by the API. Notice there's nothing
> here you'd `yum update`: the OS ships as a versioned image.

---

## Step 6 — (Optional) live resource usage

```bash
oc adm top nodes
```

**Expected output** *(requires a cluster + metrics — representative):*

```
NAME            CPU(cores)   CPU%   MEMORY(bytes)   MEMORY%
ocp4-master-0   612m         17%    5123Mi          34%
ocp4-worker-0   289m         7%     3998Mi          26%
...
```

> **Narrate:** `oc adm top` (an OpenShift admin verb, backed by the
> metrics Cluster Operator) gives live utilisation — the start of capacity planning for
> the CDR fleet, which we'll act on with the Machine API in Demo 4.

---

## Cleanup

Nothing to clean up — this demo only **read** cluster state.

---

## Wrap-up questions to pose

1. The OS-IMAGE says RHCOS. How would you change a kernel argument on every worker —
   and what must you *not* do?
2. Roles are labels, not binaries. What practical effect does the control-plane
   `NoSchedule` taint have on the CDR pods?
3. Why does the CRI-O version track the Kubernetes version so closely?
4. Which two pieces of node software did `describe node` show, and what does each do?

---

> **◐ Partially verified:** Every command **requires a live OpenShift cluster** and
> was **not** runnable in the authoring environment (no cluster connection). Output is
> **representative of OpenShift 4.18 / Kubernetes 1.31**; run the commands on the shared
> cluster to capture real node names, the RHCOS build, and the CRI-O version. Command
> *syntax* follows the `oc`/`kubectl` 4.x reference; nothing is presented as
> independently verified.

> **Gating validated (2026-07-05, as learner25):** every cluster-scope read in this demo
> (`oc get nodes` / `clusteroperators` / `clusterversion` / `machines`) returned
> `Error from server (Forbidden): ... at the cluster scope` for the normal user
> **learner25** — confirming this demo is correctly **cluster-admin / instructor-led**, as
> marked. The representative output above still requires an admin/cluster-reader login to
> reproduce live.
