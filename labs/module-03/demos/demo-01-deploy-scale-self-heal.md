# Demo 1 — Deploy, Scale & Self-Heal a Workload

> **Scenario:** The **subscriber-api** is the read path for every self-care login
> and IVR lookup — it must stay up 24/7. We deploy it as a managed workload, watch
> Kubernetes build the **Deployment → ReplicaSet → Pods** chain, scale it for an
> evening peak, then kill a pod and watch the cluster heal it back **without anyone
> paging an engineer**. This is the foundation every other workload type builds on.

| | |
|---|---|
| **Concepts reinforced** | Deployment vs ReplicaSet vs Pod · labels/selectors · `spec` vs `status` · scaling · self-healing |
| **Maps to** | Guide §3 (Pods, ReplicaSets & Deployments) · Exercise 1 |
| **Time** | ~25 minutes |
| **Cluster** | minikube; single node is fine |

---

> **⎈ Same on OpenShift:** `kubectl create deployment / scale / get / delete` all
> work verbatim as `oc ...`. OpenShift has a legacy `DeploymentConfig` too, but
> modern OpenShift uses these standard Kubernetes Deployments. Pure Kubernetes.

## Talking points to open with

- You never say "start a pod here." You **declare** "keep N replicas of this image."
- A Deployment doesn't manage Pods directly — it manages a **ReplicaSet**, which
  manages the Pods. Three layers, one job each.
- "Self-healing" isn't magic; it's the ReplicaSet controller noticing
  `actual ≠ desired` and acting — forever, on a loop.

---

## Step 1 — Declare desired state

```bash
kubectl create deployment subscriber-api \
  --image=registry.access.redhat.com/ubi9/httpd-24:latest --replicas=3
kubectl get deployment subscriber-api
```

**Expected output:**

```
deployment.apps/subscriber-api created
NAME             READY   UP-TO-DATE   AVAILABLE   AGE
subscriber-api   3/3     3            3           18s
```

> **Narrate:** We described an **end state** — 3 replicas of this image — not a
> script of "create pod, create pod, create pod." `READY 3/3` means all three
> desired pods are up. We never named a node or an IP; the platform placed them.

---

## Step 2 — See the ownership chain

```bash
kubectl get deploy,rs,pods -l app=subscriber-api
```

**Expected output:**

```
NAME                             READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/subscriber-api   3/3     3            3           18s

NAME                                        DESIRED   CURRENT   READY   AGE
replicaset.apps/subscriber-api-59bdf46cb4   3         3         3       18s

NAME                                  READY   STATUS    RESTARTS   AGE
pod/subscriber-api-59bdf46cb4-29b8t   1/1     Running   0          18s
pod/subscriber-api-59bdf46cb4-khhhp   1/1     Running   0          18s
pod/subscriber-api-59bdf46cb4-mmtwr   1/1     Running   0          18s
```

> **Narrate:** Read the chain top-down. The **Deployment** created a **ReplicaSet**
> (the `59bdf46cb4` hash is the pod-template fingerprint), which created **3 Pods**.
> The pod names encode all three layers. The `-l app=subscriber-api` selector is the
> *same mechanism* the controllers use internally — labels, not names, are the glue.

---

## Step 3 — `spec` (desired) vs `status` (actual)

```bash
kubectl get deployment subscriber-api -o jsonpath='spec={.spec.replicas} avail={.status.availableReplicas}{"\n"}'
```

**Expected output:**

```
spec=3 avail=3
```

> **Narrate:** Two numbers, two owners. **You** own `spec.replicas` (what you want);
> **Kubernetes** owns `status.availableReplicas` (what is). The controller's whole
> life is making the second equal the first. Right now they match — so let's break
> it.

---

## Step 4 — Kill a pod and watch it heal

In a **second terminal**, start watching:

```bash
kubectl get pods -l app=subscriber-api -w
```

Back in the first terminal, delete one pod:

```bash
POD=$(kubectl get pods -l app=subscriber-api -o jsonpath='{.items[0].metadata.name}')
kubectl delete pod "$POD"
kubectl get pods -l app=subscriber-api
```

**Expected output:**

```
pod "subscriber-api-59bdf46cb4-29b8t" deleted from mod3-verify namespace
NAME                              READY   STATUS    RESTARTS   AGE
subscriber-api-59bdf46cb4-bxzqx   1/1     Running   0          9s
subscriber-api-59bdf46cb4-khhhp   1/1     Running   0          28s
subscriber-api-59bdf46cb4-mmtwr   1/1     Running   0          28s
```

> **Narrate:** The instant the pod died, `status` dropped to 2 while `spec` stayed
> 3. The **ReplicaSet controller** saw the gap and created a replacement — note the
> **new pod name** (`...-bxzqx`) and its **9s age** next to the survivors' 28s.
> New pod, new IP, same everything else. Nobody intervened. *This* is self-healing.

---

## Step 5 — Scale by changing desired state

Evening usage peak — you don't "add pods," you **raise the desired number**:

```bash
kubectl scale deployment subscriber-api --replicas=6
kubectl get pods -l app=subscriber-api --no-headers | wc -l
kubectl scale deployment subscriber-api --replicas=3
kubectl get pods -l app=subscriber-api --no-headers | wc -l
```

**Expected output:**

```
deployment.apps/subscriber-api scaled
       6
deployment.apps/subscriber-api scaled
       3
```

> **Narrate:** Scaling up and down are the *same* operation — edit `spec`, let the
> controller reconcile. Down-scaling, the controller picks pods to terminate to hit
> the target. You can't "win" by deleting pods: as long as desired is 3, deleting
> one just triggers a replacement. To actually reduce pods, change the
> **declaration**.

---

## Step 6 — Confirm who owns the pods

```bash
kubectl get pod -l app=subscriber-api -o jsonpath='{.items[0].metadata.ownerReferences[0].kind}{"\n"}'
```

**Expected output:**

```
ReplicaSet
```

> **Narrate:** Each pod's `ownerReferences` points at the **ReplicaSet**, not the
> Deployment. That's the chain made explicit: delete the ReplicaSet and the
> Deployment recreates it; delete a Pod and the ReplicaSet recreates it. Ownership
> *is* the reconciliation graph.

---

## Step 7 — Cleanup

```bash
kubectl delete deployment subscriber-api
kubectl get pods -l app=subscriber-api      # all gone
```

**Expected output:**

```
deployment.apps/subscriber-api deleted
No resources found in mod3-demos namespace.
```

> **Narrate:** Deleting the Deployment cascades down the chain — ReplicaSet gone,
> Pods gone. The owner-reference graph drives cleanup just like it drives creation.

---

## Wrap-up questions to pose

1. After `kubectl delete pod`, what made a replacement appear — and how did it
   "know" to?
2. Why can't you permanently reduce a Deployment's pods by deleting them?
3. Which two numbers must the controller reconcile, and who owns each?
4. What does a Pod's `ownerReferences` point at, and why does that matter for
   cascading deletes?

---

> **✅ Verified:** kubectl 1.34 · Kubernetes 1.33 (3-node kind, equivalent plain
> Kubernetes) · image `ubi9/httpd-24`. Create, ownership chain, `spec` vs `status`,
> pod self-heal (new pod name + younger age), scale up/down, and the ownerReference
> check were all run live and the output above is from that run.
