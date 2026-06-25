# Module 3 — Exercises (Hands-On Practice)

These are **participant-driven** tasks. Unlike the [demos](../demos) (which the
instructor performs), here **you** do the work on a live **Kubernetes** cluster
with **`kubectl`**, then verify it with the provided **validation** commands. Each
exercise has a fully worked **solution** at the bottom — try the tasks first, then
check.

Module 3 — **"Kubernetes Workloads, Storage & Networking"** — uses a plain
Kubernetes cluster via **[minikube](../../setup/minikube-kubernetes.md)**, *not*
OpenShift. On minikube you are **cluster-admin**, so you can freely inspect nodes,
create namespaces, and provision storage. Every command works **verbatim as `oc`**
on OpenShift (Module 4+) — the few OpenShift conveniences (Routes, Projects,
`oc new-app`) are noted inline where relevant.

All scenarios are **telecom-flavored** so you practice in a realistic context.
Sample data (MSISDNs, plans, CDRs) is fictional.

## Exercises in this module

| # | Exercise | What you'll practice | Telecom scenario | Difficulty |
|---|----------|----------------------|------------------|------------|
| 1 | [Deploy & scale a workload](exercise-01-deploy-and-scale.md) | `create deployment`, ownership chain, `scale`, self-heal | **subscriber-api** always-on | ⭐ Beginner |
| 2 | [Rolling updates & rollbacks](exercise-02-rolling-updates-rollbacks.md) | `set image`, `rollout history/undo`, change-cause | **tariff-catalog** zero-downtime upgrade | ⭐⭐ Intermediate |
| 3 | [Expose & discover services](exercise-03-expose-and-discover.md) | ClusterIP, NodePort, EndpointSlices, CoreDNS | **self-care portal** → backends | ⭐⭐ Intermediate |
| 4 | [Config & storage](exercise-04-config-and-storage.md) | ConfigMap, Secret, PVC, persistence across pods | **tariff config** + **CDR archive** | ⭐⭐ Intermediate |
| 5 | [Capstone: a multi-tier stack](exercise-05-capstone-multitier-stack.md) | Deployment + StatefulSet + Service + Config + PVC combined | **self-care stack** end-to-end | ⭐⭐⭐ Advanced |

## Before you start

```bash
# Install/start minikube first — see ../../setup/minikube-kubernetes.md
minikube start --driver=docker        # single node is enough for Ex 1-4
kubectl version
kubectl config current-context        # -> minikube
kubectl create namespace mod3-ex 2>/dev/null; \
  kubectl config set-context --current --namespace=mod3-ex
```

- Commands use **`kubectl`** — vanilla Kubernetes. On OpenShift (Module 4+) the
  same commands work as **`oc`**; OpenShift conveniences (Routes vs Ingress,
  Projects vs Namespaces) are noted inline.
- Exercises **1–4** run fine on a **single-node** minikube. The DaemonSet portion of
  the **capstone** (Ex 5) is richer on a **multi-node** cluster — start it with
  `minikube start --nodes 3` (see the
  [setup guide](../../setup/minikube-kubernetes.md)). Each notes what it needs.
- Replace placeholders like `<pod>` / `<node>` with your own values. Nothing here
  needs credentials — minikube configures your kubeconfig automatically. Any Secret
  values are **fictional placeholders**; never commit real ones.

## How to self-assess

Each exercise's **Validation** section gives commands whose output confirms success.
If your output matches, you've completed the task. Stuck? The **Solution** walks
through one correct approach — but the learning sticks better if you struggle a
little first.

Companion material: the guided [demos](../demos/README.md) and the
[concept guide](../../../guides/module-03-workloads-storage-networking.md).

---

> **✅ Verified:** kubectl 1.34 · Kubernetes 1.33 (3-node kind, equivalent plain
> Kubernetes). Every solution's commands were run live on that cluster.
