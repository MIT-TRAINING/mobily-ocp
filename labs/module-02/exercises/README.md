# Module 2 — Exercises (Hands-On Practice)

These are **participant-driven** tasks. Unlike the [demos](../demos) (which the
instructor performs), here **you** do the work on a live **Kubernetes** cluster
with **`kubectl`**, then verify it with the provided **validation** commands. Each
exercise has a fully worked **solution** at the bottom — try the tasks first, then
check.

Module 2 uses a plain Kubernetes cluster via
**[minikube](../../setup/minikube-kubernetes.md)** — *not* OpenShift. On minikube
you are **cluster-admin**, so you can freely inspect the control plane, label and
taint nodes, and drain them. (OpenShift and `oc` arrive in Module 3 — the same
commands carry over.)

All scenarios are **telecom-flavored** so you practice in a realistic context.
Sample data (MSISDNs, plans, CDRs) is fictional.

## Exercises in this module

| # | Exercise | What you'll practice | Telecom scenario | Difficulty |
|---|----------|----------------------|------------------|------------|
| 1 | [Explore the cluster](exercise-01-explore-the-cluster.md) | `cluster-info`, `api-resources`, `explain`, `get -o`, events | **Number Portability** read-only recon | ⭐ Beginner |
| 2 | [Desired state & self-healing](exercise-02-desired-state-self-healing.md) | create deploy, `scale`, kill pods, `spec` vs `status` | **SMS Gateway** always-on | ⭐⭐ Intermediate |
| 3 | [Steer the scheduler](exercise-03-steer-the-scheduler.md) | requests, `nodeSelector`, diagnose `Pending` | **CDR Processor** placement | ⭐⭐ Intermediate |
| 4 | [Trace a pod's birth](exercise-04-trace-a-pods-birth.md) | `apply`, read events, map the flow, `-o wide` | **Usage Metering** rollout | ⭐⭐ Intermediate |
| 5 | [Capstone: a discoverable service](exercise-05-capstone-service-discovery.md) | Service, endpoints, DNS, self-healing combined | **Self-Care Portal** → subscriber-api | ⭐⭐⭐ Advanced |

## Before you start

```bash
# Install/start minikube first — see ../../setup/minikube-kubernetes.md
minikube start --driver=docker
kubectl version
kubectl config current-context     # -> minikube
kubectl create namespace mod2-ex 2>/dev/null; \
  kubectl config set-context --current --namespace=mod2-ex
```

- Commands use **`kubectl`** — vanilla Kubernetes. On OpenShift (Module 3+) the
  same commands work as **`oc`**; the few OpenShift conveniences (`oc new-project`,
  `oc expose`, `oc debug`) are noted inline where relevant.
- Exercises **1, 2, 4, 5** run fine on a **single-node** minikube. Exercise **3**
  (and the node-drain stretch in Ex 2) is richer with a **multi-node** cluster —
  start it with `minikube start --nodes 3` (see the
  [setup guide](../../setup/minikube-kubernetes.md)). Each notes what it needs.
- Replace placeholders like `<node>` / `<pod>` with your own values. Nothing here
  needs credentials — minikube configures your kubeconfig automatically.

## How to self-assess

Each exercise's **Validation** section gives commands whose output confirms
success. If your output matches, you've completed the task. Stuck? The
**Solution** walks through one correct approach — but the learning sticks better if
you struggle a little first.

Companion material: the [interactive visualizations](../index.html), the guided
[demos](../demos), the [cheat sheets](../cheetsheets/README.md), and the
[concept guide](../../../guides/module-02-kubernetes-architecture.md).
