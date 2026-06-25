# Demo 1 — Explore the Cluster Architecture

> **Scenario:** Before the operator's team deploys a single subscriber service,
> they need to understand the machine they're deploying *onto*. We'll take a guided
> tour of a live Kubernetes cluster — the control plane (brain), the worker
> node(s) (muscle), and the one rule that governs everything: **all roads go
> through the API server**.

| | |
|---|---|
| **Concepts reinforced** | Control plane vs worker nodes · the API-server front door · etcd as source of truth · the object model (`kubectl explain`, `api-resources`) |
| **Maps to** | Visualization 01 (Cluster Architecture) · Guide §4–6 |
| **Time** | ~25 minutes |
| **Cluster** | minikube, single node is fine (`minikube start`) |

---

> **⎈ Same on OpenShift:** every `kubectl` command here works verbatim as `oc` in
> Module 3+. The only OpenShift extras are `oc whoami` (Kubernetes uses
> `kubectl config current-context` / `kubectl auth whoami`) and the control-plane
> living in `openshift-*` namespaces instead of `kube-system`.

## Talking points to open with

- A cluster is **two kinds of role**: a **control plane** that decides and stores
  state, and **worker nodes** that actually run pods. (On minikube one node plays
  both — and is schedulable.)
- Every component — you, the scheduler, controllers, each kubelet — talks **only**
  through the **kube-apiserver**. No back channels.
- **etcd** is the single source of truth; everything else is effectively stateless.

---

## Step 1 — What am I talking to?

```bash
kubectl config current-context     # which cluster context (-> minikube)
kubectl cluster-info               # the API SERVER + CoreDNS URLs — your front door
kubectl auth whoami                # your identity (used for authn/authz on every call)
```

**Expected output** (abridged):

```
minikube
Kubernetes control plane is running at https://192.168.49.2:8443
CoreDNS is running at https://192.168.49.2:8443/api/v1/namespaces/kube-system/services/kube-dns:dns/proxy
```

> **Narrate:** Notice `kubectl cluster-info` is itself *served by the API server* —
> even "where is the control plane?" is answered through the one front door. That
> URL (minikube uses port **8443**; vanilla clusters use **6443**) is the only
> entry point; every later command flows through it.

---

## Step 2 — The cluster is made of API objects (the object model)

You don't manage the cluster with ad-hoc commands; you manage **objects**. List
the object *types* the API server knows about:

```bash
kubectl api-resources | head -20      # the kinds of objects (Pod, Service, Node…)
kubectl api-resources | wc -l         # how many resource types this cluster exposes
```

Then inspect the **shape** of an object without touching the cluster — the
`apiVersion/kind/metadata/spec/status` model from the guide:

```bash
kubectl explain pod                   # top-level fields
kubectl explain pod.spec --recursive | head -30   # drill into desired state
kubectl explain deployment.spec.replicas          # one field, documented
```

> **Narrate:** `kubectl explain` reads the **schema the API server validates
> against** — the same schema that rejects a malformed manifest at admission time.
> Every object has the same four-field shape: you own `spec` (desired), Kubernetes
> owns `status` (actual). Hold that thought — Demo 2 is built on it.

---

## Step 3 — The node(s): where pods will run

```bash
kubectl get nodes -o wide
kubectl get nodes -L node-role.kubernetes.io/control-plane
```

```
NAME       STATUS   ROLES           AGE   VERSION   INTERNAL-IP    OS-IMAGE   ...
minikube   Ready    control-plane   12m   v1.31.x   192.168.49.2   ...        CONTAINER-RUNTIME: cri-o / containerd
```

> **Narrate:** On minikube this single node is **both** control plane and worker,
> and it's **schedulable**, so our subscriber pods will land right here. In
> production you'd see **3** control-plane nodes (the etcd-quorum story — an odd
> number so a majority survives a failure) plus separate workers. Look closer:

```bash
kubectl describe node minikube | sed -n '/Capacity:/,/System Info/p'
kubectl top nodes        # live CPU/memory (the scheduler's raw material; needs metrics-server)
```

> **Multi-node option:** `minikube start --nodes 3` gives `minikube`,
> `minikube-m02`, `minikube-m03` — handy for Demos 2 (§5) and 3 where pods move
> between machines. `kubectl get nodes` then lists all three.

> **Tip:** if `kubectl top` errors, enable the add-on once:
> `minikube addons enable metrics-server` (wait ~30s).

---

## Step 4 — Meet the control-plane components (they run as pods)

On Kubernetes the control plane runs as pods in the **`kube-system`** namespace.
Look at the actual processes behind the architecture diagram:

```bash
kubectl get pods -n kube-system -o wide
kubectl get pods -n kube-system | grep -E 'apiserver|etcd|scheduler|controller-manager|coredns|kube-proxy'
```

```
NAME                               READY   STATUS    AGE
kube-apiserver-minikube            1/1     Running   12m
etcd-minikube                      1/1     Running   12m
kube-scheduler-minikube            1/1     Running   12m
kube-controller-manager-minikube   1/1     Running   12m
coredns-7db6d8ff4d-abcde           1/1     Running   12m
kube-proxy-xyz12                   1/1     Running   12m
```

> **Narrate:** There's our **front door** (`kube-apiserver`), the **scheduler**,
> the **controller-manager** (every reconciliation loop lives in there), **etcd**,
> **CoreDNS** (service discovery), and **kube-proxy** (service networking). On
> OpenShift these same components live in `openshift-*` namespaces and are managed
> by cluster Operators — but the architecture is identical.

Prove the **golden rule** that everything is API-driven — turn on request logging:

```bash
# kubectl ≥1.31 logs the call as: ... "Response" verb="GET" url="https://..."
kubectl get pods -A -v=6 2>&1 | grep -m1 'verb="GET"'   # see the literal API call kubectl makes
# (older kubectl printed it as `GET https://... 200 OK` — then use: grep -m1 "GET https")
```

```
I0625 ... round_trippers.go:632] "Response" verb="GET" url="https://127.0.0.1:6443/api/v1/pods?limit=500" status="200 OK" milliseconds=12
```

> **Narrate:** Even a plain `kubectl get` is just an authenticated **HTTPS GET to
> the API server**. There is no other way to read or change cluster state — not for
> us, not for the scheduler, not for any kubelet.

---

## Step 5 — Watch the API server's watch mechanism

Open the event stream that every controller relies on:

```bash
kubectl get events -A --watch &      # leave running ~10s, then: kill %1
```

> **Narrate:** Components don't poll etcd; they **watch** the API server and react
> to changes. That event-driven, decoupled design is what we'll see drive a pod's
> entire birth in Demo 4.

---

## Step 6 — Cleanup

Nothing was created in this demo (read-only tour). Just stop any backgrounded
watch:

```bash
kill %1 2>/dev/null   # stop the 'kubectl get events --watch' if still running
```

---

## Wrap-up questions to pose

1. Name the path a `kubectl get pods` request travels. Which component authorizes it?
2. Production clusters run 3 control-plane nodes — why an odd number, and what
   breaks if 2 fail? (How does minikube differ, and why is that OK for learning?)
3. If the scheduler crashes, can existing pods keep running? Why or why not?
4. Where does the cluster's entire state physically live, and what's the one
   component allowed to write there?

---

> **✅ Verified:** kubectl 1.34 against Kubernetes 1.33. Commands verified on an
> equivalent plain-Kubernetes cluster (3-node kind). Output values that are
> minikube-specific (node name `minikube`, API URL on port **8443**, IP
> `192.168.49.2`) are shown for the minikube lab environment; on kind/other
> clusters the node names and URL differ but the commands and behaviour are identical.
