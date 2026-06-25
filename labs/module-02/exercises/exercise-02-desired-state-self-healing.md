# Exercise 2 — Desired State & Self-Healing

> **Scenario:** The **SMS Gateway** must always have 4 workers handling message
> queues. You'll declare that desired state, then prove the cluster keeps it true
> when pods die and when you try to fight it.

| | |
|---|---|
| **Practice** | `create deployment`, `scale`, `delete pod`, `spec` vs `status`, the reconciliation loop |
| **Maps to** | Visualization 02 (Desired State & Self-Healing) · Demo 2 |
| **Difficulty** | ⭐⭐ Intermediate · ~25 min · single-node OK (drain stretch needs multi-node) |

---

## Tasks

1. Create a Deployment named **`sms-gateway`** from
   `registry.access.redhat.com/ubi9/httpd-24:latest` with **4 replicas**.
2. Show the Deployment's **desired** replica count and its **available** count
   side by side (they should match).
3. In a second terminal, **watch** the pods. Then **delete one pod** and observe a
   replacement appear. Confirm the count returns to **4/4**.
4. **Scale up** to 7 for an evening peak, confirm 7 pods, then **scale back** to 4.
5. Try to "beat" the controller: with desired=4, delete a pod and immediately
   re-list. Explain why you can't hold it at 3.
6. Inspect the **ownership chain**: show that the Deployment owns a ReplicaSet,
   which owns the Pods.

> **Hint (Task 6):** `kubectl get deploy,rs,pods -l app=sms-gateway`, then
> `kubectl get pod <name> -o jsonpath='{.metadata.ownerReferences[0].kind}'`.

---

## Validation

```bash
# Task 2 & 3 — both should read 4
kubectl get deployment sms-gateway -o jsonpath='spec={.spec.replicas} avail={.status.availableReplicas}{"\n"}'

# Task 3 — after deleting a pod, you still end with 4 Running
kubectl get pods -l app=sms-gateway        # 4 pods, all Running

# Task 6 — pod is owned by a ReplicaSet
kubectl get pod -l app=sms-gateway -o jsonpath='{.items[0].metadata.ownerReferences[0].kind}{"\n"}'
# Expected: ReplicaSet
```

---

## Stretch goals

- Delete the **ReplicaSet** (not the Deployment) with
  `kubectl delete rs -l app=sms-gateway`. What recreates it, and why?
- Set `--replicas=0`. Are the pods gone? Is the Deployment gone? What's the
  difference between scaling to 0 and deleting?
- **Multi-node** (`minikube start --nodes 3`): find a node running 2 of your pods,
  `kubectl drain <node> --ignore-daemonsets --delete-emptydir-data`, and watch the
  pods reschedule onto other nodes. `kubectl uncordon <node>` to restore.

---

## Reflection

- Which two fields did the controller compare, and who owns each?
- Why is deleting pods a *useless* way to permanently shrink a Deployment?
- A node hosting 2 of your pods dies. Without you doing anything, what happens and
  which controller drives it?

---

<details>
<summary><strong>✅ Solution</strong> (try the tasks first)</summary>

```bash
# 1. Declare desired state
kubectl create deployment sms-gateway \
  --image=registry.access.redhat.com/ubi9/httpd-24:latest --replicas=4

# 2. spec vs status
kubectl get deployment sms-gateway \
  -o jsonpath='spec={.spec.replicas} avail={.status.availableReplicas}{"\n"}'

# 3. Self-healing (second terminal: kubectl get pods -l app=sms-gateway -w)
POD=$(kubectl get pods -l app=sms-gateway -o jsonpath='{.items[0].metadata.name}')
kubectl delete pod "$POD"
kubectl get pods -l app=sms-gateway     # a new pod replaces it; back to 4/4

# 4. Scale up then down
kubectl scale deployment sms-gateway --replicas=7
kubectl get pods -l app=sms-gateway     # 7
kubectl scale deployment sms-gateway --replicas=4
kubectl get pods -l app=sms-gateway     # 4 (extras terminated)

# 5. You can't beat the loop
POD=$(kubectl get pods -l app=sms-gateway -o jsonpath='{.items[0].metadata.name}')
kubectl delete pod "$POD"; kubectl get pods -l app=sms-gateway   # replacement already creating
# Desired stays 4, so the ReplicaSet controller keeps actual at 4. To reduce pods,
# change the DECLARATION (scale), not reality.

# 6. Ownership chain
kubectl get deploy,rs,pods -l app=sms-gateway
kubectl get pod -l app=sms-gateway -o jsonpath='{.items[0].metadata.ownerReferences[0].kind}{"\n"}'  # ReplicaSet

# Cleanup
kubectl delete deployment sms-gateway
```

**Key point:** you own `spec` (desired); Kubernetes owns `status` (actual). The
ReplicaSet controller's whole life is closing that gap. Self-healing = the loop
noticing `actual ≠ desired` and acting — for pod death *and* node death.
</details>

---

> **✅ Verified:** kubectl 1.34 · Kubernetes 1.33 (3-node kind, equivalent plain
> Kubernetes) · image `ubi9/httpd-24`. Declare/scale, pod self-heal, and the
> multi-node `cordon`+`drain` reschedule were run live (via Demo 2's identical flow).
