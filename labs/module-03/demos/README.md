# Module 3 — Guided Demos (Instructor-Led)

These are **instructor-led, narrated walkthroughs**. The instructor runs each step
live against a real **Kubernetes** cluster while explaining *what* each object does
and *why* it matters. Participants watch and follow along, then practice
independently in the [`../exercises`](../exercises).

Module 3 is **"Kubernetes Workloads, Storage & Networking"** — how you actually run
applications on the cluster you explored in Module 2. Like Module 2, the labs use
plain **`kubectl`** against a **[minikube](../../setup/minikube-kubernetes.md)**
cluster — *not* OpenShift. Every command works **verbatim as `oc`** on OpenShift;
each demo opens with an **⎈ Same on OpenShift** note pointing out the handful of
OpenShift-specific conveniences (Routes, Projects, `oc new-app`) that arrive in
Module 4.

All scenarios use a **telecom domain** framing (subscriber API, tariff catalog, CDR
store, SMS gateway, self-care portal, nightly billing) so the objects land in a
familiar context. Data and services are fictional and illustrative.

## Demos in this module

| # | Demo | Concepts reinforced | Telecom scenario | Time |
|---|------|---------------------|------------------|------|
| 1 | [Deploy, scale & self-heal](demo-01-deploy-scale-self-heal.md) | Deployment → ReplicaSet → Pods · labels/selectors · scale · self-heal | `subscriber-api` always-on | ~25 min |
| 2 | [Rolling updates & rollbacks](demo-02-rolling-updates-rollbacks.md) | `set image` · `rollout status/history/undo/pause/resume` · change-cause | `tariff-catalog` zero-downtime upgrade | ~30 min |
| 3 | [Services & discovery](demo-03-services-and-discovery.md) | ClusterIP · NodePort · headless · EndpointSlices · CoreDNS · Ingress object | self-care portal → backends | ~30 min |
| 4 | [Config & storage](demo-04-config-and-storage.md) | ConfigMap · Secret (base64) · PVC · StorageClass · persistence | tariff config + CDR archive | ~30 min |
| 5 | [StatefulSets, DaemonSets & Jobs](demo-05-statefulsets-daemonsets-jobs.md) | StatefulSet identity + per-pod PVC · DaemonSet per node · Job · CronJob | CDR store, node probe, billing rollup | ~30 min |

## Conventions

- Commands use **`kubectl`** — vanilla Kubernetes. On OpenShift (Module 4+) the
  *same* commands work as **`oc`**; each demo's **⎈ Same on OpenShift** note flags
  the OpenShift conveniences (Routes vs Ingress, Projects vs Namespaces).
- **Single-node vs multi-node.** Demos 1–4 run fine on a single-node minikube. The
  **DaemonSet** part of Demo 5 only shows "one per node" meaningfully on a
  **multi-node** cluster — start one with `minikube start --nodes 3` (see the
  [minikube setup guide](../../setup/minikube-kubernetes.md)). On minikube you are
  **cluster-admin**, so node and `kube-system` inspection just works.
- Replace placeholders like `<pod>` / `<node>` with your own values. Nothing here
  needs credentials; minikube wires up your kubeconfig automatically. Secrets in the
  config demo use **fictional placeholder values** — never commit real ones.
- Each demo ends with a **Cleanup** section — run it so the next demo starts clean.
- Companion material: the [concept guide](../../../guides/module-03-workloads-storage-networking.md)
  and the [exercises](../exercises/README.md).

## Pre-flight check (run once before Demo 1)

```bash
# Install/start minikube first — see ../../setup/minikube-kubernetes.md
minikube start --driver=docker        # single node is enough for Demos 1-4
kubectl version                        # client + server
kubectl config current-context         # -> minikube
kubectl get nodes                      # node(s) Ready
kubectl create namespace mod3-demos 2>/dev/null; \
  kubectl config set-context --current --namespace=mod3-demos
```

> **Instructor tip:** pre-pull the demo images into the cluster before class
> (`minikube image load registry.access.redhat.com/ubi9/httpd-24:latest`,
> `.../ubi9/ubi-minimal:latest`, and `docker.io/library/nginx:1.25-alpine` /
> `:1.26-alpine`) so the first deploy and the rolling-update demo are instant. Keep
> a second terminal running `kubectl get pods -w` so the class watches state change
> live. For Demo 5's DaemonSet, start a **3-node** cluster so "one per node" is
> visible.

---

> **✅ Verified:** kubectl 1.34 · Kubernetes 1.33 (3-node kind, equivalent plain
> Kubernetes). Every command and output in these demos is from a real run on that
> cluster.
