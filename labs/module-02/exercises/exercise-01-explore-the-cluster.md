# Exercise 1 — Explore the Cluster

> **Scenario:** You've just been given access to a Kubernetes cluster. Before
> deploying the **Number Portability (MNP)** service, do your recon: confirm what
> you're talking to, what objects the cluster knows about, and how it describes
> them.

| | |
|---|---|
| **Practice** | `config current-context`, `cluster-info`, `api-resources`, `explain`, `get -o jsonpath`, events |
| **Maps to** | Visualization 01 (Cluster Architecture) · Demo 1 |
| **Difficulty** | ⭐ Beginner · ~20 min · single-node minikube OK |

---

## Tasks

1. Print the **current context** and the **API server URL** you're connected to
   (your single front door).
2. Print how many **API resource types** this cluster exposes.
3. Without creating anything, show the **top-level fields** of a `Service` object,
   then drill into the documentation for `service.spec.selector`.
4. List the **objects in your current namespace** (there should be few or none yet).
5. Using `-o jsonpath`, print **just the server version** of the cluster.
6. List the **control-plane components** running as pods in the `kube-system`
   namespace, and identify the API server, etcd, scheduler, and controller-manager.
7. Stream **events** in your namespace for ~10 seconds (then stop). Note: it's quiet
   because nothing is happening — you'll fill it with activity in later exercises.

> **Hint (Task 3):** `kubectl explain <kind>` reads the same schema the API server
> validates against — `kubectl explain service` then
> `kubectl explain service.spec.selector`.

---

## Validation

```bash
# Task 1
kubectl config current-context && kubectl cluster-info | head -1

# Task 2 — a number (varies by cluster, typically 50+)
kubectl api-resources --no-headers | wc -l

# Task 5 — a version string like v1.31.x
kubectl version -o json | grep -m1 gitVersion

# Task 6 — the four core control-plane pods appear
kubectl get pods -n kube-system | grep -E 'apiserver|etcd|scheduler|controller-manager'
```

---

## Stretch goals

- Find the **kind** behind the short name `svc` (and `deploy`, `cm`):
  `kubectl api-resources | grep -E 'services|deployments|configmaps'`.
- Show which API resources are **namespaced** vs **cluster-scoped**:
  `kubectl api-resources --namespaced=true | wc -l` vs `--namespaced=false`.
- List the nodes and their roles: `kubectl get nodes -o wide`. On single-node
  minikube, what role does the one node play? In production, why an odd number of
  control-plane nodes?

---

## Reflection

- Every `kubectl get` you ran was secretly what kind of network call, to which
  component?
- If etcd were wiped (no backup), what exactly would be lost?
- Why is `kubectl explain` useful *before* you ever write a manifest?

---

<details>
<summary><strong>✅ Solution</strong> (try the tasks first)</summary>

```bash
# 1. Context + front door
kubectl config current-context        # minikube
kubectl cluster-info                  # API server + CoreDNS, all served BY the apiserver

# 2. How many object types
kubectl api-resources --no-headers | wc -l

# 3. Object shape (no cluster mutation)
kubectl explain service
kubectl explain service.spec.selector

# 4. What's in my namespace
kubectl get all                       # or: kubectl get pods,svc,deploy

# 5. Just the server version
kubectl version -o jsonpath='{.serverVersion.gitVersion}{"\n"}'

# 6. Control-plane components as pods
kubectl get pods -n kube-system
#   kube-apiserver-minikube / etcd-minikube / kube-scheduler-minikube /
#   kube-controller-manager-minikube / coredns-* / kube-proxy-*

# 7. Watch events (quiet for now)
kubectl get events -w        # Ctrl-C after ~10s
```

**Key point:** the cluster is managed as **API objects** through **one front door**
(the API server — minikube on :8443, vanilla on :6443). `kubectl explain` documents
the `apiVersion/kind/metadata/spec/status` shape every object shares — read it
before writing manifests. Every command you ran was an authenticated HTTPS call to
that one front door; the control plane itself runs as pods in `kube-system`.
</details>
