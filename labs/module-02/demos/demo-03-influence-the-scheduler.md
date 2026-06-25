# Demo 3 — Influence the Scheduler

> **Scenario:** The **CDR processor** is I/O-heavy and must run only on fast-SSD
> nodes; meanwhile some nodes are reserved for a different tenant. We'll give the
> scheduler resource requests, a node selector, and meet taints/tolerations —
> watching it **filter** feasible nodes and **score** the best one, and watching a
> pod sit **Pending** when nothing fits.

| | |
|---|---|
| **Concepts reinforced** | Resource requests · nodeSelector / labels · taints & tolerations · filter (predicates) + score (priorities) · `Pending` & events |
| **Maps to** | Visualization 03 (The Scheduler) · Guide §5.3 |
| **Time** | ~30 minutes |
| **Cluster** | **Multi-node minikube** (`minikube start --nodes 3`) so placement is visible |

---

> **⎈ Same on OpenShift:** `kubectl label/taint/get/describe/create` all work
> verbatim as `oc ...`. (`oc adm taint` is the OpenShift spelling of
> `kubectl taint`.) Pure Kubernetes scheduling.

## Talking points to open with

- A new pod has **no node**. The scheduler's only job is to *choose* one — it never
  runs anything.
- It decides in **two phases**: **filter** (which nodes *can* run it?) then **score**
  (which feasible node is *best*?).
- Its raw materials are your pod's **requests**, **nodeSelector/affinity**, and the
  nodes' **taints**.

---

## Step 1 — Label a node to model "fast SSD" capacity

```bash
kubectl get nodes
NODE=$(kubectl get nodes -o jsonpath='{.items[1].metadata.name}')   # a worker, e.g. minikube-m02
kubectl label node "$NODE" disktype=ssd --overwrite
kubectl get nodes -L disktype       # confirm exactly one node is labelled ssd
```

> **Narrate:** Labels are how we describe a node's *capabilities*. The scheduler
> will match a pod's `nodeSelector` against these.

---

## Step 2 — Deploy with a resource request + nodeSelector

Create the CDR processor that *demands* an SSD node and reserves CPU/memory:

```bash
cat <<'EOF' | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cdr-processor
spec:
  replicas: 2
  selector: { matchLabels: { app: cdr-processor } }
  template:
    metadata: { labels: { app: cdr-processor } }
    spec:
      nodeSelector:
        disktype: ssd                 # FILTER: only nodes labelled disktype=ssd
      containers:
        - name: proc
          image: registry.access.redhat.com/ubi9/ubi:latest
          command: ["sleep", "infinity"]
          resources:
            requests:                 # FILTER: node must have this much free
              cpu: "250m"
              memory: "128Mi"
EOF

kubectl get pods -l app=cdr-processor -o wide
```

```
NAME                              READY   STATUS    NODE           ...
cdr-processor-...-aaa             1/1     Running   minikube-m02   (the ssd node)
cdr-processor-...-bbb             1/1     Running   minikube-m02
```

> **Narrate:** Both pods landed on the **one SSD node** — the `nodeSelector`
> *filtered out* every other node. The `requests` told the scheduler how much
> capacity to reserve. This is the **filter** phase in action.

---

## Step 3 — Watch the scheduler's decision in the events

```bash
POD=$(kubectl get pods -l app=cdr-processor -o jsonpath='{.items[0].metadata.name}')
kubectl describe pod "$POD" | sed -n '/Events:/,$p'
```

```
Events:
  Type    Reason     From               Message
  ----    ------     ----               -------
  Normal  Scheduled  default-scheduler  Successfully assigned .../cdr-processor-...-aaa to minikube-m02
  Normal  Pulled     kubelet            Container image already present on machine
  Normal  Started    kubelet            Started container proc
```

> **Narrate:** Read the actors: **default-scheduler** said *Scheduled → minikube-m02*
> (it chose), then the node's **kubelet** pulled and started it (it ran). Two
> different components, two different jobs — exactly the separation from the guide.

---

## Step 4 — Make a pod un-schedulable (Pending)

Ask for something no node can satisfy and watch it get **stuck** (not error — *wait*):

```bash
cat <<'EOF' | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata: { name: cdr-greedy, labels: { app: cdr-processor } }
spec:
  containers:
    - name: proc
      image: registry.access.redhat.com/ubi9/ubi:latest
      command: ["sleep","infinity"]
      resources:
        requests: { cpu: "999", memory: "9000Gi" }   # absurd — fits nowhere
EOF

kubectl get pod cdr-greedy             # STATUS: Pending
kubectl describe pod cdr-greedy | sed -n '/Events:/,$p'
```

```
STATUS: Pending
Events:
  Warning  FailedScheduling  default-scheduler  0/3 nodes are available:
           3 Insufficient cpu, 3 Insufficient memory. preemption: 0/3 ...
```

> **Narrate:** **Pending** is the scheduler saying "I filtered every node and none
> can run this." The pod object exists in etcd, but it has no home, so the kubelet
> never hears about it. This is the #1 real-world scheduling symptom — and the event
> tells you exactly why (`Insufficient cpu`). Fix = lower requests or add capacity.

```bash
kubectl delete pod cdr-greedy
```

---

## Step 5 — Taints & tolerations: reserve a node

A **taint** repels pods *unless* they explicitly **tolerate** it — the mechanism
control-plane nodes use to keep your workloads off them. Reserve a node for, say,
the messaging tenant:

```bash
kubectl taint nodes "$NODE" tenant=messaging:NoSchedule
```

Now the CDR pods (which don't tolerate it) can't use that node. Roll the
Deployment so it reschedules and watch it go Pending (the SSD node is now tainted):

```bash
kubectl rollout restart deployment/cdr-processor
kubectl get pods -l app=cdr-processor -o wide        # may be Pending: only ssd node exists & it's tainted
```

Add a **toleration** so CDR is allowed back on:

```bash
kubectl patch deployment cdr-processor --type=merge -p '{
  "spec": {"template": {"spec": {"tolerations":
    [{"key":"tenant","operator":"Equal","value":"messaging","effect":"NoSchedule"}]}}}}'
kubectl get pods -l app=cdr-processor -o wide        # Running on the ssd node again
```

> **Narrate:** Taint = the node says "go away." Toleration = the pod says "I'm
> allowed here anyway." Together with `nodeSelector` they're how you steer *which*
> workloads land *where* — the controls the scheduler weighs during **filtering**.

---

## Step 6 — Cleanup

```bash
kubectl delete deployment cdr-processor
kubectl delete pod cdr-greedy --ignore-not-found
# undo node changes:
kubectl taint nodes "$NODE" tenant=messaging:NoSchedule-     # trailing '-' removes
kubectl label node "$NODE" disktype-                          # trailing '-' removes
```

---

## Wrap-up questions to pose

1. What are the scheduler's two phases, and what does each decide?
2. A pod is `Pending` with `FailedScheduling`. Is that an error or expected? How do
   you find the cause?
3. What's the difference between a `nodeSelector` and a `toleration`?
4. The scheduler "bound" a pod to a node — did it start the container? Who did?

---

> **✅ Verified:** kubectl 1.34 · Kubernetes 1.33 (3-node kind, equivalent plain
> Kubernetes) · images `ubi9/ubi`, `ubi9/httpd-24`. `nodeSelector` placement, the
> `Pending`/`FailedScheduling` (Insufficient cpu/memory) path, and the
> taint→toleration round-trip were run live; node label/taint were reverted.
> **Note:** the exact `FailedScheduling` node counts vary by cluster (on a single
> schedulable-node-per-role kind cluster the control-plane node also shows an
> untolerated-taint line); the minikube output where all nodes are schedulable
> reads `0/3 nodes ... 3 Insufficient cpu`.
