# Demo 4 — Trace a Pod's Birth

> **Scenario:** We deploy the **tariff-catalog** API and follow the single
> `kubectl apply` end-to-end — API server → etcd → controllers → scheduler →
> kubelet → container runtime — by reading the cluster's own event trail. The goal:
> prove that the sequence diagram in the guide is *literally* what happens, every
> time.

| | |
|---|---|
| **Concepts reinforced** | The pod-creation request flow · every actor reacts to a **watch** · events as the audit trail · `spec`→`status` completion |
| **Maps to** | Visualization 04 (Anatomy of kubectl apply) · Guide §8 |
| **Time** | ~25 minutes |
| **Cluster** | minikube; a multi-node cluster makes the "spread" in Step 4 visible |

---

> **⎈ Same on OpenShift:** `kubectl apply / get / get events / get -o wide` all
> work verbatim as `oc ...`. Fully portable.

## Talking points to open with

- One command, **seven steps**, **six actors** — and no actor talks to another
  directly. Everything goes through the API server.
- The fingerprint of the whole flow is in `kubectl get events`: each line is one
  actor reacting to a watch.
- "Created" means *recorded in etcd*, not *running*. Running is the end of a chain.

---

## Step 1 — Pre-stage two watchers (so the class sees it live)

Open **two extra terminals** and start streaming before you create anything:

```bash
# Terminal 2 — pod state transitions
kubectl get pods -l app=tariff-catalog -w

# Terminal 3 — the actor-by-actor event trail
kubectl get events -w --field-selector involvedObject.kind!=Node
```

> **Narrate:** Keep your eyes on Terminal 3 — that's where each component will
> announce itself in order as we submit one manifest.

---

## Step 2 — Submit desired state (Step 1 of the flow)

In Terminal 1:

```bash
cat <<'EOF' | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata: { name: tariff-catalog }
spec:
  replicas: 3
  selector: { matchLabels: { app: tariff-catalog } }
  template:
    metadata: { labels: { app: tariff-catalog } }
    spec:
      containers:
        - name: api
          image: registry.access.redhat.com/ubi9/httpd-24:latest
          ports: [{ containerPort: 8080 }]
EOF
```

```
deployment.apps/tariff-catalog created
```

> **Narrate:** "created" = the API server **authenticated** you, ran **RBAC** and
> **admission**, validated the object, and **persisted it to etcd**. That's all.
> Nothing is running yet. We just recorded intent. Watch the other terminals erupt.

---

## Step 3 — Read the chain in the event trail

In Terminal 3 (or capture it after the fact), you'll see the actors fire in order:

```bash
kubectl get events --sort-by=.lastTimestamp | tail -20
```

```
REASON              OBJECT                              MESSAGE
ScalingReplicaSet   deployment/tariff-catalog           Scaled up replica set tariff-catalog-6f8 to 3
SuccessfulCreate    replicaset/tariff-catalog-6f8       Created pod: tariff-catalog-6f8-aaaaa
SuccessfulCreate    replicaset/tariff-catalog-6f8       Created pod: tariff-catalog-6f8-bbbbb
SuccessfulCreate    replicaset/tariff-catalog-6f8       Created pod: tariff-catalog-6f8-ccccc
Scheduled           pod/tariff-catalog-6f8-aaaaa        Successfully assigned .../...-aaaaa to minikube-m02
Pulled              pod/tariff-catalog-6f8-aaaaa        Container image already present on machine
Created             pod/tariff-catalog-6f8-aaaaa        Created container api
Started             pod/tariff-catalog-6f8-aaaaa        Started container api
```

> **Narrate — map each line to the guide's diagram:**
> - `ScalingReplicaSet` → the **Deployment controller** created a **ReplicaSet** (step 3/4).
> - `SuccessfulCreate ... Created pod` → the **ReplicaSet controller** created 3 **Pod** objects, still nodeless (step 4).
> - `Scheduled ... assigned ... to <node>` → the **scheduler** bound each pod to a node (step 5).
> - `Pulled / Created / Started` → the node's **kubelet** drove the **container runtime** to pull and run the container (step 6).
>
> Six actors, each reacting to a **watch**, each via the API server. No shortcuts.

---

## Step 4 — Confirm the binding (who chose where)

```bash
kubectl get pods -l app=tariff-catalog -o wide
```

```
NAME                          READY   STATUS    NODE           IP            ...
tariff-catalog-6f8-aaaaa      1/1     Running   minikube-m02   10.244.1.41
tariff-catalog-6f8-bbbbb      1/1     Running   minikube       10.244.0.12
tariff-catalog-6f8-ccccc      1/1     Running   minikube-m02   10.244.1.42
```

> **Narrate:** The `NODE` column is the scheduler's binding; the `IP` column is what
> the kubelet+CNI assigned when the pod actually started. On a multi-node cluster
> notice the scheduler **spread** the pods across nodes — that's the *score* phase
> preferring resilience (Demo 3). On single-node minikube all three land on
> `minikube` (the only node), which is expected.

---

## Step 5 — `spec` → `status`: reconciliation complete

```bash
kubectl get deployment tariff-catalog -o jsonpath=\
'desired={.spec.replicas} available={.status.availableReplicas}{"\n"}'
```

```
desired=3 available=3
```

> **Narrate:** The kubelets reported `Running` back through the API server into
> etcd, so `status.availableReplicas` rose to match `spec.replicas`. The loop has
> closed — actual equals desired. That final report is step 7 of the flow.

Peek at one pod's own status timeline:

```bash
kubectl get pod -l app=tariff-catalog -o jsonpath='{.items[0].status.conditions[*].type}{"\n"}'
# e.g.: PodReadyToStartContainers Initialized Ready ContainersReady PodScheduled
# (the set/order vary by version — k8s ≥1.31 adds PodReadyToStartContainers; the
#  meaningful birth milestones are PodScheduled → Initialized → ContainersReady → Ready)
```

> **Narrate:** Even a single pod records the milestones of its own birth:
> *Scheduled → Initialized → ContainersReady → Ready*. The system is auditable end
> to end because every transition went through the one front door.

---

## Step 6 — Cleanup

```bash
kubectl delete deployment tariff-catalog
# in terminals 2 & 3: press Ctrl-C to stop the watchers
```

---

## Wrap-up questions to pose

1. Put these in order and name the actor for each: *Scheduled, SuccessfulCreate
   (pod), Started, ScalingReplicaSet*.
2. When `kubectl apply` returned "created," what was and wasn't true about the
   workload?
3. How did the scheduler and kubelet each "find out" there was work to do?
4. Why did the 3 pods land on different nodes (on a multi-node cluster)?

---

> **✅ Verified:** kubectl 1.34 · Kubernetes 1.33 (3-node kind, equivalent plain
> Kubernetes) · image `ubi9/httpd-24`. The event chain
> (`ScalingReplicaSet`→`SuccessfulCreate`→`Scheduled`→`Started`), multi-node spread,
> the line-continuation jsonpath (`desired=3 available=3`), and pod conditions were
> all run live. Node names shown are minikube's.
