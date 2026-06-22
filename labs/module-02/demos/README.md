# Module 2 — Guided Demos (Instructor-Led)

These are **instructor-led, narrated walkthroughs**. The instructor runs each step
live against a real **Kubernetes** cluster while explaining *what* each component
is doing and *why* it matters. Participants watch and follow along, then practice
independently in the [`../exercises`](../exercises).

Module 2 is about **Kubernetes architecture**, so the labs use plain **`kubectl`**
against a **[minikube](../../setup/minikube-kubernetes.md)** cluster — *not*
OpenShift. (OpenShift and `oc` are introduced in Module 3.) Where Module 1 ran
containers on a single host with `podman`, Module 2 moves up a level: the same
workloads, now **orchestrated across a cluster**.

All scenarios use a **telecom domain** framing (subscriber API, CDR processor,
SMS gateway, self-care portal) so the architecture lands in a familiar context.
Data and services are fictional and illustrative.

## Demos in this module

| # | Demo | Concepts reinforced | Maps to | Time |
|---|------|---------------------|---------|------|
| 1 | [Explore the cluster architecture](demo-01-explore-cluster-architecture.md) | Control plane vs nodes · API server as the only front door · the object model | Viz 01 · Guide §4–6 | ~25 min |
| 2 | [Desired state & self-healing](demo-02-desired-state-self-healing.md) | `spec` vs `status` · ReplicaSet reconciliation · node drain & reschedule | Viz 02 · Guide §5.4, §7 | ~30 min |
| 3 | [Influence the scheduler](demo-03-influence-the-scheduler.md) | Requests · nodeSelector · taints/tolerations · filter + score | Viz 03 · Guide §5.3 | ~30 min |
| 4 | [Trace a pod's birth](demo-04-trace-a-pods-birth.md) | End-to-end request flow · watches · events | Viz 04 · Guide §8 | ~25 min |
| 5 | [Services, endpoints & DNS](demo-05-service-discovery-dns.md) | Labels/selectors · endpoints · ClusterIP · CoreDNS | Viz 05 · Guide §5.6, §6.3, §9 | ~30 min |

## Conventions

- Commands use **`kubectl`** — vanilla Kubernetes. On OpenShift (Module 3+) the
  *same* commands work as **`oc`** (`oc` is `kubectl` plus OpenShift verbs); each
  demo opens with an **⎈ Same on OpenShift** note pointing out the handful of
  OpenShift conveniences (`oc new-project`, `oc expose`, `oc debug`, `oc adm`).
- **Single-node vs multi-node.** Most demos run on a default single-node minikube.
  The scheduler and node-drain demos need **multiple nodes** — start those with
  `minikube start --nodes 3` (see the
  [minikube setup guide](../../setup/minikube-kubernetes.md)). Each affected step
  says so. On minikube you are **cluster-admin**, so every command — including node
  and `kube-system` inspection — just works.
- Replace placeholders like `<node>` / `<pod>` with your own values. Nothing here
  needs credentials; minikube wires up your kubeconfig automatically.
- Each demo ends with a **Cleanup** section — run it so the next demo starts clean.
- Companion material: the [interactive visualizations](../index.html), the
  [concept guide](../../../guides/module-02-kubernetes-architecture.md), and the
  [cheat sheets](../cheetsheets/README.md).

## Pre-flight check (run once before Demo 1)

```bash
# Install/start minikube first — see ../../setup/minikube-kubernetes.md
minikube start --driver=docker        # single node is enough for Demos 1, 4, 5
kubectl version                        # client + server
kubectl config current-context         # -> minikube
kubectl get nodes                      # node Ready
kubectl create namespace mod2-demos 2>/dev/null; \
  kubectl config set-context --current --namespace=mod2-demos
```

> **Instructor tip:** pre-pull the demo images into the cluster before class
> (`minikube image load registry.access.redhat.com/ubi9/httpd-24:latest` and
> `.../ubi9/ubi:latest`) so the first deploy is instant. Keep a second terminal
> running `kubectl get pods -w` so the class can watch state change live. For
> Demos 2 (§5) and 3, start a **3-node** cluster instead so pods can move between
> machines.
