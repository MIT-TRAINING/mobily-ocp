# Demo 2 — Desired State & Self-Healing

> **Scenario:** The **subscriber-api** must stay up 24/7. We declare "always keep 3
> replicas," then deliberately break things — kill pods, drain a node — and watch
> Kubernetes heal back to our declared intent **without anyone paging an engineer**.
> This is the single most important behaviour in the whole platform.

| | |
|---|---|
| **Concepts reinforced** | `spec` (desired) vs `status` (actual) · ReplicaSet controller · the reconciliation loop · node drain & reschedule |
| **Maps to** | Visualization 02 (Desired State & Self-Healing) · Guide §5.4, §7 |
| **Time** | ~30 minutes |
| **Cluster** | minikube; §1–4 single node OK, **§5 needs multi-node** (`minikube start --nodes 3`) |

---

> **⎈ Same on OpenShift:** `kubectl create deployment / scale / get / delete /
> describe` and `kubectl cordon/drain` all work verbatim as `oc ...` later. Pure
> Kubernetes.

## Talking points to open with

- You never say "start a pod here." You **declare** "I want N replicas" and walk away.
- A **controller** watches the gap between `spec` and `status` and closes it —
  forever, on a loop.
- "Self-healing" isn't magic; it's this loop noticing `actual ≠ desired` and acting.

---

## Step 1 — Declare desired state

```bash
kubectl create deployment subscriber-api \
  --image=registry.access.redhat.com/ubi9/httpd-24:latest --replicas=3
kubectl get deployment subscriber-api
```

```
NAME             READY   UP-TO-DATE   AVAILABLE   AGE
subscriber-api   3/3     3            3           25s
```

> **Narrate:** We described an **end state** (3 replicas of this image). We did not
> script "create pod, create pod, create pod." The Deployment created a ReplicaSet,
> which created 3 Pods. Look at the chain:

```bash
kubectl get deploy,rs,pods -l app=subscriber-api
```

> **Narrate:** Deployment → ReplicaSet → 3 Pods. Each pod got scheduled to a node
> and started. That whole cascade is Demo 4; here we focus on keeping it true.

---

## Step 2 — See `spec` vs `status` with your own eyes

```bash
kubectl get deployment subscriber-api -o jsonpath='{.spec.replicas}{"\n"}'    # what YOU want
kubectl get deployment subscriber-api -o jsonpath='{.status.availableReplicas}{"\n"}'  # what IS
```

```
3
3
```

> **Narrate:** Two numbers, two owners. **You** own the top one (`spec`);
> **Kubernetes** owns the bottom one (`status`). The controller's entire job is to
> make the bottom equal the top. Right now they match — so let's break that.

---

## Step 3 — Kill a pod and watch it heal

In a **second terminal**, start watching:

```bash
kubectl get pods -l app=subscriber-api -w
```

Back in the first terminal, delete one pod:

```bash
POD=$(kubectl get pods -l app=subscriber-api -o jsonpath='{.items[0].metadata.name}')
kubectl delete pod "$POD"
```

In the watch terminal you'll see the gap open and close in seconds:

```
subscriber-api-7d9...-abcde   1/1   Terminating         ...
subscriber-api-7d9...-fghij   0/1   ContainerCreating   ...   <- replacement appears
subscriber-api-7d9...-fghij   1/1   Running             ...
```

> **Narrate:** The instant the pod died, `status` dropped to 2 while `spec` stayed
> 3. The **ReplicaSet controller** saw `actual(2) ≠ desired(3)` and created a
> replacement — **new pod name, new IP**, same everything else. Nobody intervened.
> *This* is self-healing.

Confirm the count never really left 3:

```bash
kubectl get deployment subscriber-api      # READY back to 3/3
```

---

## Step 4 — Scale by changing desired state

Evening usage peak — scale up. You don't "add pods," you **raise the desired number**:

```bash
kubectl scale deployment subscriber-api --replicas=6
kubectl get pods -l app=subscriber-api      # 6 now
kubectl scale deployment subscriber-api --replicas=2
kubectl get pods -l app=subscriber-api      # back down to 2 — extras terminated
```

> **Narrate:** Scaling up and scaling down are the *same* operation — edit `spec`,
> let the controller reconcile. Down-scaling, the controller picks pods to delete
> to hit the target. Declarative all the way.

Try to "win" against the controller (you can't):

```bash
kubectl scale deployment subscriber-api --replicas=3
POD=$(kubectl get pods -l app=subscriber-api -o jsonpath='{.items[0].metadata.name}')
kubectl delete pod "$POD"; kubectl get pods -l app=subscriber-api   # a new one is already coming back
```

> **Narrate:** As long as the Deployment says 3, you cannot keep it at 2 by deleting
> pods — the loop just recreates them. To actually reduce pods you must change the
> **declaration**. The desired state always wins.

---

## Step 5 — Drain a node: healing across machines (multi-node)

> **Needs ≥2 nodes.** If you started single-node, recreate the cluster with
> `minikube delete && minikube start --nodes 3`, then redeploy
> `subscriber-api` (Step 1) before continuing.

Pod-level healing is one ReplicaSet. **Node-level** healing is the node controller
rescheduling work off a dead/maintenance machine. Find where a pod lives, then
drain that node:

```bash
kubectl get pods -l app=subscriber-api -o wide      # note the NODE column
NODE=$(kubectl get pods -l app=subscriber-api -o jsonpath='{.items[0].spec.nodeName}')

kubectl cordon "$NODE"                                # mark unschedulable (no NEW pods land here)
kubectl drain "$NODE" --ignore-daemonsets --delete-emptydir-data --force
```

Watch the affected pod get **evicted and rescheduled onto a different node**:

```bash
kubectl get pods -l app=subscriber-api -o wide -w     # NODE column changes for the moved pod
```

> **Narrate:** Cordon stops new placements; drain evicts the existing pods. The
> ReplicaSet controller recreates them and the scheduler places them on **healthy**
> nodes — exactly what happens automatically when a node crashes at 3 a.m. The app
> stayed available throughout.

Put the node back in service:

```bash
kubectl uncordon "$NODE"
kubectl get nodes      # node back to schedulable
```

> **Single-node note:** with only the `minikube` node there's nowhere to move pods
> to, so a drain would just leave them Pending. Re-run Step 3 instead and emphasize
> that the *same loop* handles both cases — the only difference is which controller
> (ReplicaSet vs node) noticed the gap.

---

## Step 6 — Cleanup

```bash
kubectl delete deployment subscriber-api
kubectl get pods -l app=subscriber-api      # all gone
```

---

## Wrap-up questions to pose

1. After `kubectl delete pod`, what made a replacement appear — and how did it
   "know" to?
2. Why can't you permanently reduce a Deployment's pods by deleting them?
3. Which two numbers must a controller reconcile, and who owns each?
4. When a node fails, which controller acts, and where do its pods end up?
