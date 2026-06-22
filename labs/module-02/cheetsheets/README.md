# Module 2 — Cheatsheets

Quick-reference command sheets for the Module 2 labs, demos, and exercises. Keep
them open in a second window while you work.

Module 2 runs on a plain **Kubernetes** cluster
([minikube](../../setup/minikube-kubernetes.md)) driven with **`kubectl`** — *not*
OpenShift. On OpenShift (Module 3+) the same commands work as **`oc`**.

| Cheatsheet | Use it for |
|------------|-----------|
| [kubectl essentials](01-kubectl-essentials.md) | Connecting (minikube), namespaces, the core verbs, output & JSONPath, workloads (deploy/scale/rollout), Services & DNS |
| [Architecture inspection](02-architecture-inspection.md) | Looking *inside* the cluster: nodes, control-plane components, the scheduler, events, endpoints, and diagnosing `Pending`/no-endpoints |

## Conventions

- Commands are shown with **`kubectl`**. On OpenShift the same commands work as
  **`oc`**; the OpenShift conveniences (`oc login`, `oc new-project`, `oc expose`,
  `oc debug`, `oc adm`, `oc rsh`, `oc status`) are noted where a row's `kubectl`
  form differs.
- `<placeholders>` mean "substitute your own value." Nothing here needs
  credentials — minikube configures your kubeconfig automatically.
- On minikube you are **cluster-admin**, so node and `kube-system` commands all
  work. Node-spreading commands (drain, multi-node scheduling) need a multi-node
  cluster: `minikube start --nodes 3`.
- Examples use the same telecom services as the [demos](../demos) and
  [exercises](../exercises) — `subscriber-api`, `cdr-processor`, `sms-gateway`,
  `tariff-catalog`, the self-care portal.

Companion material: [interactive visualizations](../index.html) ·
[minikube setup](../../setup/minikube-kubernetes.md) ·
[concept guide](../../../guides/module-02-kubernetes-architecture.md).
