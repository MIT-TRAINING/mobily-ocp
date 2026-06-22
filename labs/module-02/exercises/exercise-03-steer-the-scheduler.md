# Exercise 3 — Steer the Scheduler

> **Scenario:** The **CDR processor** is resource-hungry and (in production) must
> land on specific nodes. You'll give it resource requests and a `nodeSelector`,
> then deliberately make a pod **un-schedulable** and diagnose *why* from the events
> — the #1 real-world scheduling skill.

| | |
|---|---|
| **Practice** | resource `requests`, `nodeSelector`, reading `Pending` / `FailedScheduling`, the filter phase |
| **Maps to** | Visualization 03 (The Scheduler) · Demo 3 |
| **Difficulty** | ⭐⭐ Intermediate · ~25 min |
| **Cluster** | Tasks 1–4 work on **single-node**; the real-placement stretch needs **multi-node** (`minikube start --nodes 3`) |

---

## Tasks

> Tasks 1–4 teach scheduling by making a pod Pending and reading the reason, which
> works on any cluster — even single-node minikube.

1. Create a pod **`cdr-fits`** (image `ubi9/ubi`, command `sleep infinity`) with a
   modest request: `cpu: 100m`, `memory: 64Mi`. Confirm it reaches **Running** and
   note the node it was bound to (`-o wide`).
2. Create a pod **`cdr-greedy`** with an **impossible** request (`cpu: 999`,
   `memory: 9000Gi`). Confirm it stays **Pending**.
3. Read `cdr-greedy`'s **events** and quote the line that explains *why* it can't be
   scheduled. Then fix it (recreate with a sane request) and confirm Running.
4. Create a pod **`cdr-picky`** with a `nodeSelector` of `disktype=ssd`. On a
   cluster with no such labelled node it will stay **Pending** — confirm, and read
   the event. (This is the selector *filtering out every node*.)
5. From the scheduler's perspective, summarize the difference between *why*
   `cdr-greedy` and `cdr-picky` are both Pending.

> **Hint:** `kubectl describe pod <name>` → the `Events:` section; look for
> `FailedScheduling` and the node-by-node reason (`Insufficient cpu`,
> `node(s) didn't match Pod's node affinity/selector`).

---

## Validation

```bash
# Task 1 — Running, with a node assigned
kubectl get pod cdr-fits -o wide

# Task 2 & 4 — Pending
kubectl get pod cdr-greedy cdr-picky

# Task 3 — the smoking gun
kubectl describe pod cdr-greedy | grep -A3 Events
# ... FailedScheduling ... Insufficient cpu, Insufficient memory ...
```

---

## Stretch goals

- **Multi-node:** label a worker `kubectl label node <node> disktype=ssd`, then
  recreate `cdr-picky`. It should now schedule onto exactly that node — prove it
  with `-o wide`. Clean up: `kubectl label node <node> disktype-`.
- **Multi-node:** taint a node `kubectl taint nodes <node> tenant=billing:NoSchedule`,
  deploy a pod *without* a toleration (won't land there), then add the matching
  toleration and watch it become eligible. Remove the taint with the trailing `-`.
- Add `cpu`/`memory` **limits** as well as requests and inspect the pod's QoS class:
  `kubectl get pod cdr-fits -o jsonpath='{.status.qosClass}{"\n"}'`.

---

## Reflection

- Is `Pending` an *error*? What is the scheduler actually telling you?
- What are the scheduler's two phases, and which one rejected `cdr-greedy` vs
  `cdr-picky`?
- Once the scheduler "binds" a pod to a node, which component actually starts the
  container?

---

<details>
<summary><strong>✅ Solution</strong> (try the tasks first)</summary>

```bash
# 1. A pod that fits
cat <<'EOF' | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata: { name: cdr-fits, labels: { app: cdr } }
spec:
  containers:
    - name: proc
      image: registry.access.redhat.com/ubi9/ubi:latest
      command: ["sleep","infinity"]
      resources: { requests: { cpu: "100m", memory: "64Mi" } }
EOF
kubectl get pod cdr-fits -o wide      # Running, NODE shows the chosen node

# 2. A pod that fits nowhere
cat <<'EOF' | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata: { name: cdr-greedy }
spec:
  containers:
    - name: proc
      image: registry.access.redhat.com/ubi9/ubi:latest
      command: ["sleep","infinity"]
      resources: { requests: { cpu: "999", memory: "9000Gi" } }
EOF
kubectl get pod cdr-greedy            # Pending

# 3. Diagnose, then fix
kubectl describe pod cdr-greedy | sed -n '/Events:/,$p'
#   FailedScheduling ... 0/N nodes are available: N Insufficient cpu, N Insufficient memory
kubectl delete pod cdr-greedy
# (recreate cdr-greedy with requests cpu:100m memory:64Mi → Running)

# 4. A selector that matches no node
cat <<'EOF' | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata: { name: cdr-picky }
spec:
  nodeSelector: { disktype: ssd }
  containers:
    - name: proc
      image: registry.access.redhat.com/ubi9/ubi:latest
      command: ["sleep","infinity"]
EOF
kubectl get pod cdr-picky             # Pending
kubectl describe pod cdr-picky | sed -n '/Events:/,$p'
#   FailedScheduling ... node(s) didn't match Pod's node affinity/selector

# Cleanup
kubectl delete pod cdr-fits cdr-greedy cdr-picky --ignore-not-found
```

**Key point:** both pods are Pending after the **filter** phase eliminated every
node — but for different reasons: `cdr-greedy` because no node has the *capacity*
(`Insufficient cpu/memory`), `cdr-picky` because no node carries the required
*label* (`didn't match selector`). The event always names the cause. The scheduler
only *chooses*; the node's kubelet starts the container once a binding exists.
</details>
