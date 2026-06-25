# Exercise 1 — Deploy & Scale a Workload

> **Scenario:** You're bringing the **subscriber-api** online for the first time. It
> must run as a managed workload that survives pod death and scales for peak hours.
> You'll declare it, trace the Deployment → ReplicaSet → Pod chain, scale it, and
> prove it heals itself.

| | |
|---|---|
| **Practice** | `create deployment`, the ownership chain, `scale`, `delete pod`, `spec` vs `status` |
| **Maps to** | Guide §3 · Demo 1 |
| **Difficulty** | ⭐ Beginner · ~20 min · single-node OK |

---

## Tasks

1. Create a Deployment named **`subscriber-api`** from
   `registry.access.redhat.com/ubi9/httpd-24:latest` with **3 replicas**.
2. Show the **ownership chain** — that the Deployment owns a ReplicaSet, which owns
   3 Pods — in a single command.
3. Display the Deployment's **desired** replica count and its **available** count
   side by side (they should match).
4. In a second terminal **watch** the pods, then **delete one** and confirm a
   replacement appears and the count returns to **3/3**. Note the new pod's name and
   age.
5. **Scale up** to 6 for an evening peak, confirm 6 pods, then **scale back** to 3.
6. Confirm a Pod's `ownerReferences` points at a **ReplicaSet**, not the Deployment.

> **Hint (Task 2):** one `kubectl get` can list multiple resource kinds at once,
> filtered by a label — `kubectl get deploy,rs,pods -l app=subscriber-api`.

> **Hint (Task 4):** `kubectl get pods -l app=subscriber-api -w` in the second
> terminal; grab a pod name with `-o jsonpath='{.items[0].metadata.name}'`.

---

## Validation

```bash
# Task 1 & 3 — both numbers should read 3
kubectl get deployment subscriber-api -o jsonpath='spec={.spec.replicas} avail={.status.availableReplicas}{"\n"}'

# Task 4 — after deleting a pod you still end with 3 Running
kubectl get pods -l app=subscriber-api        # 3 pods, all Running

# Task 6 — the pod is owned by a ReplicaSet
kubectl get pod -l app=subscriber-api -o jsonpath='{.items[0].metadata.ownerReferences[0].kind}{"\n"}'
# Expected: ReplicaSet
```

---

## Reflection

- Which two fields did the controller compare to decide a pod was missing, and who
  owns each?
- Why can't you permanently shrink the Deployment by deleting pods?
- After self-healing, why does the replacement pod have a *different name* but the
  same labels?

---

<details>
<summary><strong>✅ Solution</strong> (try the tasks first)</summary>

```bash
# 1. Declare desired state
kubectl create deployment subscriber-api \
  --image=registry.access.redhat.com/ubi9/httpd-24:latest --replicas=3

# 2. Ownership chain
kubectl get deploy,rs,pods -l app=subscriber-api
# deployment/subscriber-api -> replicaset/subscriber-api-59bdf46cb4 -> 3 pods

# 3. spec vs status
kubectl get deployment subscriber-api \
  -o jsonpath='spec={.spec.replicas} avail={.status.availableReplicas}{"\n"}'
# spec=3 avail=3

# 4. Self-healing (second terminal: kubectl get pods -l app=subscriber-api -w)
POD=$(kubectl get pods -l app=subscriber-api -o jsonpath='{.items[0].metadata.name}')
kubectl delete pod "$POD"
kubectl get pods -l app=subscriber-api    # new pod (younger age) replaces it; back to 3/3

# 5. Scale up then down
kubectl scale deployment subscriber-api --replicas=6
kubectl get pods -l app=subscriber-api --no-headers | wc -l   # 6
kubectl scale deployment subscriber-api --replicas=3
kubectl get pods -l app=subscriber-api --no-headers | wc -l   # 3

# 6. Ownership
kubectl get pod -l app=subscriber-api \
  -o jsonpath='{.items[0].metadata.ownerReferences[0].kind}{"\n"}'   # ReplicaSet

# Cleanup
kubectl delete deployment subscriber-api
```

**Verified output (key lines):**

```
spec=3 avail=3
subscriber-api-59bdf46cb4-bxzqx   1/1   Running   0   9s     <- replacement, younger
ReplicaSet
```

**Key point:** you own `spec` (desired); Kubernetes owns `status` (actual). The
ReplicaSet controller's whole job is closing that gap — for pod death *and* scaling.
</details>

---

> **✅ Verified:** kubectl 1.34 · Kubernetes 1.33 (3-node kind, equivalent plain
> Kubernetes) · image `ubi9/httpd-24`. Declare, ownership chain, `spec`/`status`,
> pod self-heal, scale up/down, and the ownerReference check were all run live (the
> identical flow as Demo 1).
