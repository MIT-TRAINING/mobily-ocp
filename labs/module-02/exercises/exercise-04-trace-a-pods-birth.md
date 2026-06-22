# Exercise 4 — Trace a Pod's Birth

> **Scenario:** You're rolling out the **Usage Metering** API. You'll deploy it and
> then reconstruct the *entire* request flow — controllers → scheduler → kubelet —
> purely from the cluster's own event trail, matching each line to an actor.

| | |
|---|---|
| **Practice** | `apply`, reading `kubectl get events`, mapping the flow, `-o wide`, pod conditions |
| **Maps to** | Visualization 04 (Anatomy of kubectl apply) · Demo 4 |
| **Difficulty** | ⭐⭐ Intermediate · ~25 min · single-node OK (multi-node shows the spread) |

---

## Tasks

1. In a second terminal, start `kubectl get events -w`. In the first, **apply** a
   Deployment named **`usage-metering`** (image `ubi9/httpd-24`, **3 replicas**,
   `containerPort: 8080`).
2. Immediately after apply returns "created," explain in one sentence what is — and
   isn't — true about the workload yet.
3. From `kubectl get events --sort-by=.lastTimestamp`, **find and label** the lines
   for: (a) the Deployment controller scaling a ReplicaSet, (b) the ReplicaSet
   creating pods, (c) the scheduler binding a pod, (d) the kubelet pulling/starting
   a container. Name the **actor** for each.
4. Show the pods with `-o wide`. On a multi-node cluster, did the scheduler put all
   3 on the **same** node or **spread** them? Why might it spread them?
5. Confirm reconciliation finished by showing `spec.replicas` equals
   `status.availableReplicas`.
6. Show one pod's **status conditions** and put them in birth order.

> **Hint (Task 3):** events have a `REASON` column —
> `ScalingReplicaSet`, `SuccessfulCreate`, `Scheduled`, `Pulled/Created/Started`.

---

## Validation

```bash
# Task 1 — 3 running pods
kubectl get pods -l app=usage-metering

# Task 4 — see the NODE column
kubectl get pods -l app=usage-metering -o wide

# Task 5 — desired == available
kubectl get deployment usage-metering -o jsonpath='spec={.spec.replicas} avail={.status.availableReplicas}{"\n"}'
# Expected: spec=3 avail=3

# Task 6 — condition types in order
kubectl get pod -l app=usage-metering -o jsonpath='{.items[0].status.conditions[*].type}{"\n"}'
# Expected: PodScheduled Initialized ContainersReady Ready
```

---

## Stretch goals

- Capture the ordered event trail to a file and annotate it:
  `kubectl get events --sort-by=.lastTimestamp | tail -20`.
- Delete one pod and watch the **same flow** replay for just the replacement —
  which steps repeat, which don't (no new ReplicaSet)?
- Add `-v=6` to your `kubectl apply` and find the literal
  `POST https://.../deployments` call — proof the request went through the API server.

---

## Reflection

- Order these and give each an actor: *Started, Scheduled, SuccessfulCreate (pod),
  ScalingReplicaSet*.
- "Created" came back instantly, but the pods took a few seconds to run. Why?
- How did the scheduler and each kubelet *learn* there was work to do — push or pull?

---

<details>
<summary><strong>✅ Solution</strong> (try the tasks first)</summary>

```bash
# 1. Watch (terminal 2): kubectl get events -w
#    Apply (terminal 1):
cat <<'EOF' | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata: { name: usage-metering }
spec:
  replicas: 3
  selector: { matchLabels: { app: usage-metering } }
  template:
    metadata: { labels: { app: usage-metering } }
    spec:
      containers:
        - name: api
          image: registry.access.redhat.com/ubi9/httpd-24:latest
          ports: [{ containerPort: 8080 }]
EOF

# 2. "created" = authn/authz/admission passed and the object is PERSISTED IN ETCD.
#    Nothing is running yet — only intent is recorded.

# 3. The chain, by actor:
kubectl get events --sort-by=.lastTimestamp | tail -20
#   ScalingReplicaSet   deployment/...   -> Deployment controller
#   SuccessfulCreate    replicaset/...   -> ReplicaSet controller (created the Pods)
#   Scheduled           pod/...          -> kube-scheduler (bound pod to node)
#   Pulled/Created/Started pod/...        -> kubelet (+ container runtime) on the chosen node

# 4. Placement
kubectl get pods -l app=usage-metering -o wide
#   Multi-node: typically SPREAD across nodes — the scheduler's score phase favors
#   resilience. Single-node minikube: all on the one node (expected).

# 5. Reconciliation complete
kubectl get deployment usage-metering \
  -o jsonpath='spec={.spec.replicas} avail={.status.availableReplicas}{"\n"}'   # spec=3 avail=3

# 6. One pod's birth milestones
kubectl get pod -l app=usage-metering \
  -o jsonpath='{.items[0].status.conditions[*].type}{"\n"}'   # PodScheduled Initialized ContainersReady Ready

# Cleanup
kubectl delete deployment usage-metering
```

**Key point:** one `apply`, six actors, all via the API server, each reacting to a
**watch** (pull, not push). "Created" means recorded in etcd; "Running" is the end
of the controllers→scheduler→kubelet chain. The event trail is the audit log of
that chain.
</details>
