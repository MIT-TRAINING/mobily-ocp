# Assignment 2 — Kubernetes Architecture & Your First Pod

> **Module 2 · Kubernetes Foundations and Architecture**
> **Telecom scenario:** Mobily is moving the `selfcare-api` you containerized in
> Assignment 1 onto Kubernetes. Before trusting it to a Deployment, the platform
> team wants you to **understand the machinery**: which control-plane component
> does what, how a Pod actually gets scheduled onto a node, and how declarative
> YAML drives the whole thing. You'll run the API as a **single Pod** and narrate
> its journey from `kubectl apply` to `Running`.

| | |
|---|---|
| **Maps to** | Control plane & worker nodes · API server · etcd · scheduler · kubelet · Pods · declarative YAML |
| **Tools** | `minikube` + `kubectl` *(plain Kubernetes — not `oc`, by design for Modules 2–3)* |
| **Provided** | the `selfcare-api:1.0.0` image you built in Assignment 1 |
| **Difficulty** | ⭐⭐ Intermediate · ~60 min |
| **Weight** | 15 % of the Modules 1–3 assessment |

> **Why kubectl/minikube here?** Modules 2–3 teach *Kubernetes fundamentals* on a
> vanilla cluster so the concepts are crisp before OpenShift (`oc`) adds its layer
> in Module 4. Every `kubectl` verb you use has an identical `oc` equivalent.

---

## Learning objectives

By the end you can:

1. Name the **control-plane** components (API server, etcd, scheduler, controller
   manager) and **node** components (kubelet, container runtime, kube-proxy), and
   say what each contributed to your Pod starting.
2. Distinguish **imperative** (`kubectl run`) from **declarative** (`kubectl apply
   -f`) workflows and explain why production uses declarative YAML.
3. Use **namespaces** to isolate workloads.
4. Read a Pod's **events** and **conditions** to trace scheduling and startup.
5. Reach a Pod via `port-forward` and `exec`.

## Prerequisites

```bash
minikube start                  # single-node cluster
kubectl get nodes               # Ready?
kubectl version                 # client + server

# Make YOUR locally-built image available to the cluster (it isn't on a registry):
minikube image load selfcare-api:1.0.0
minikube image ls | grep selfcare-api
```

> If you pushed the image to a registry in Assignment 1, you may instead reference
> `docker.io/<your-registry-user>/selfcare-api:1.0.0` and skip `image load`.

---

## Tasks

### Part A — Map the cluster (5 pts)
1. List the **nodes** and describe the one node: how many CPUs / how much memory,
   what container runtime, what kubelet version?
2. List everything running in the **`kube-system`** namespace. Identify, by Pod
   name, the **API server**, **etcd**, **scheduler**, and **controller manager**.
   (On minikube these run as static Pods.)
3. In one or two sentences each, state what **etcd** and the **scheduler** do.

### Part B — Namespace + declarative Pod (6 pts)
4. Create a namespace `selfcare` **declaratively** (YAML + `kubectl apply`), not
   with `kubectl create namespace`.
5. Write a **Pod** manifest `pod-selfcare.yaml` for image `selfcare-api:1.0.0` in
   namespace `selfcare`, that:
   - names the Pod `selfcare`, labels it `app=selfcare-api`,
   - exposes `containerPort: 8080`,
   - sets `SELFCARE_REGION=minikube-dev` via `env`,
   - declares a **readiness** and **liveness** probe on `GET /healthz`,
   - uses `imagePullPolicy: IfNotPresent` (so it uses your loaded image).
6. `apply` it. Watch it go `Pending → ContainerCreating → Running`.

### Part C — Trace the Pod's birth (5 pts)
7. `kubectl describe pod` and read the **Events**. Identify the line where the
   **scheduler** assigned the Pod to a node (`Scheduled`), and the lines where the
   **kubelet** pulled the image and started the container.
8. Show the Pod's **node assignment** and its **Pod IP**
   (`kubectl get pod selfcare -n selfcare -o wide`).
9. Confirm the `/version` endpoint reports `"region":"minikube-dev"` and a `"pod"`
   equal to the Pod name — proving your `env` and the downward `HOSTNAME` flowed in.
   Use `kubectl port-forward`.
10. `kubectl exec` into the Pod and `curl` `localhost:8080/healthz` **from inside**
    the container. Why does this work without any Service?

### Part D — Declarative is the point (4 pts)
11. Delete the Pod with `kubectl delete pod selfcare -n selfcare`. Does it come
    back? Now delete it and immediately re-`apply` the manifest. Explain the
    difference between a bare **Pod** and a controller-managed Pod (foreshadowing
    Assignment 3's Deployment).
12. Export the live Pod as YAML (`-o yaml`) and identify **three fields Kubernetes
    added** that you did not write (e.g. `status`, `nodeName`, default
    `serviceAccount`).

---

## Deliverables

`submission-02.md` containing:

- Your `namespace.yaml` and `pod-selfcare.yaml`.
- Pasted output of `kubectl get nodes -o wide`, the `kube-system` Pod list with
  the four control-plane components circled/annotated, the **Events** section of
  `kubectl describe pod selfcare`, and the `/version` JSON.
- Written answers to Tasks 3, 10, 11, and 12.

---

## Validation (self-check)

```bash
kubectl get pod selfcare -n selfcare -o jsonpath='{.status.phase}'      # Running
kubectl get pod selfcare -n selfcare -o jsonpath='{.spec.nodeName}'     # a node name
kubectl -n selfcare port-forward pod/selfcare 8080:8080 &              # then:
curl -s localhost:8080/version | grep -q '"region": "minikube-dev"' && echo PASS
```

---

## Grading rubric (15 pts)

| Criteria | Pts |
|---|---|
| Cluster + control-plane components correctly identified and explained | 5 |
| Namespace + Pod created **declaratively**, probes present, Pod Running | 6 |
| Events read correctly (scheduler vs kubelet steps distinguished) | 2 |
| Correct explanation of bare-Pod vs controller + added status fields | 2 |
| **Total** | **15** |

> Deduction: using `kubectl run`/`create` instead of `apply -f` for Tasks 4–5 (−3) —
> the objective is the **declarative** workflow.

---

## Stretch goals (not graded)

- `kubectl get events -n selfcare --sort-by=.lastTimestamp` — build the timeline
  yourself.
- `kubectl run tmp --rm -it --image=registry.access.redhat.com/ubi9/ubi-minimal
  -- bash`, then `curl http://<pod-ip>:8080/healthz` from another Pod. Why is the
  Pod IP reachable cluster-wide but useless from your laptop?
- Compare your hand-written Pod to the `podman generate kube` output from
  Assignment 1's stretch goal. What did Kubernetes require that podman didn't?

---

<details>
<summary><strong>✅ Reference solution</strong> (attempt the tasks first)</summary>

**namespace.yaml**
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: selfcare
  labels: { team: self-care, course: mobily-ocp }
```

**pod-selfcare.yaml**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: selfcare
  namespace: selfcare
  labels: { app: selfcare-api }
spec:
  containers:
    - name: selfcare-api
      image: selfcare-api:1.0.0
      imagePullPolicy: IfNotPresent
      ports: [{ containerPort: 8080 }]
      env:
        - name: SELFCARE_REGION
          value: "minikube-dev"
      readinessProbe:
        httpGet: { path: /healthz, port: 8080 }
        initialDelaySeconds: 2
        periodSeconds: 5
      livenessProbe:
        httpGet: { path: /healthz, port: 8080 }
        initialDelaySeconds: 5
        periodSeconds: 10
```

```bash
# A — map the cluster
kubectl get nodes -o wide
kubectl describe node minikube | sed -n '/Capacity/,/System Info/p'
kubectl get pods -n kube-system          # kube-apiserver-*, etcd-*, kube-scheduler-*, kube-controller-manager-*
# etcd      = the cluster's source of truth (all object state, key-value, watchable)
# scheduler = picks a node for each unscheduled Pod based on requests/affinity/taints

# B — declarative namespace + Pod
kubectl apply -f namespace.yaml
kubectl apply -f pod-selfcare.yaml
kubectl get pod -n selfcare -w           # Pending -> ContainerCreating -> Running

# C — trace its birth
kubectl describe pod selfcare -n selfcare        # Events: Scheduled (scheduler) -> Pulled/Created/Started (kubelet)
kubectl get pod selfcare -n selfcare -o wide     # NODE + POD IP
kubectl -n selfcare port-forward pod/selfcare 8080:8080 &
curl -s localhost:8080/version                   # region=minikube-dev, pod=selfcare
kubectl exec -it selfcare -n selfcare -- curl -s localhost:8080/healthz
# Works with no Service because curl targets localhost INSIDE the Pod's own
# network namespace — the container talking to itself. A Service is only needed
# to reach the Pod from OTHER pods/clients (Assignment 3).

# D — declarative is the point
kubectl delete pod selfcare -n selfcare          # gone — nothing recreates a bare Pod
kubectl apply -f pod-selfcare.yaml               # you bring it back by re-declaring it
kubectl get pod selfcare -n selfcare -o yaml | grep -E 'nodeName|serviceAccount|phase|podIP'
# Kubernetes added status{}, spec.nodeName, spec.serviceAccountName=default, podIP, etc.
```

**Key point:** a bare Pod has **no controller** — delete it and it stays dead.
The API server only records desired state in etcd; the scheduler places the Pod;
the kubelet on the chosen node pulls the image and runs the container; you read
the whole story in `kubectl describe`'s Events. Assignment 3 adds a controller
(Deployment/ReplicaSet) that makes "always N healthy Pods" self-healing.
</details>

---

> **✅ Manifests validated:** `kubectl apply --dry-run=client` (client v1.34) on
> 2026-06-25 — every manifest in this assignment parses and is schema-valid. Run
> them on your minikube cluster for the live Events/IP output (cluster-specific).
> The image itself is the one verified in Assignment 1.
