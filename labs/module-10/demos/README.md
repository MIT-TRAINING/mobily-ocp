# Module 10 — Guided Demos (Instructor-Led)

These are **instructor-led, narrated walkthroughs**. The instructor runs each step live
while explaining *what* each object does and *why*. Participants watch and follow along,
then practice in the [`../exercises`](../exercises).

Module 10 — **"GitOps, CI/CD and Service Mesh"** — covers **GitOps/Argo CD**, **CI/CD
pipelines** (the Jenkins→GitOps flow), and **Service Mesh**. Argo CD, OpenShift Pipelines,
and Service Mesh are all installed as **Operators** (Module 9's OLM).

All scenarios use a **telecom domain** framing (a `self-care` portal via GitOps, a
`subscriber-api` CI pipeline, a `tariff-catalog` canary). Data is fictional.

## Demos in this module

| # | Demo | Concepts reinforced | Telecom scenario | Time |
|---|------|---------------------|------------------|------|
| 1 | [GitOps with Argo CD](demo-01-gitops-argocd.md) | Application CR · sync · drift/self-heal · rollback via git | Deliver **self-care** from Git | ~30 min |
| 2 | [CI pipeline → GitOps](demo-02-cicd-pipeline.md) | Tekton/Jenkins pipeline · build image · update GitOps repo · Argo deploys | Ship **subscriber-api** :v2 | ~30 min |
| 3 | [Service Mesh canary](demo-03-service-mesh.md) | sidecar injection (2/2) · mTLS · VirtualService weighted routing | Canary **tariff-catalog** | ~30 min |

## Conventions

- Commands use **`oc`** plus **`argocd`**/**`tkn`** and Service Mesh CRs. Manifest/Helm/
  Kustomize rendering is standard Kubernetes; Argo CD/Tekton/OSSM CRDs come from their
  Operators.
- **Podman-first images:** the sample app is **`ubi9/httpd-24`** (rootless, HTTP on
  **8080**; bare `GET /` → **403** proves connectivity).
- **Permissions.** **Installing the Operators** (GitOps, Pipelines, Service Mesh) and
  cluster-scoped mesh config need **cluster-admin** — instructor-led. Creating an Argo CD
  **Application**, running a **pipeline**, and adding mesh CRs can be done by a project user
  once the Operators exist. Each demo marks admin-only steps.
- Replace placeholders (`<cluster-domain>`, `<git-repo>`). **Never commit real secrets/
  tokens** — sample values are fictional; use Git deploy keys / SA tokens as placeholders.
- Each demo ends with a **Cleanup** section.
- Companion material: the
  [concept guide](../../../guides/module-10-gitops-cicd-servicemesh.md), the interactive
  [visualizations](../index.html), and the [exercises](../exercises/README.md).

## Pre-flight check (run once before Demo 1)

```bash
oc login https://api.<cluster-domain>:6443 -u <user> -p "$OCP_PASSWORD"   # or token
oc whoami
oc get csv -A | grep -Ei 'gitops|pipelines|servicemesh'   # Operators present? (else install via OperatorHub)
oc get route -n openshift-gitops openshift-gitops-server -o jsonpath='{.spec.host}{"\n"}' 2>/dev/null  # Argo CD URL
```

> **Instructor tip:** pre-install the **OpenShift GitOps**, **OpenShift Pipelines**, and
> **OpenShift Service Mesh** Operators (Module 9) before class — they take a few minutes and
> need cluster-admin. Keep the **Argo CD UI** and **Kiali** open beside the terminal; the
> topology/graph views make sync and traffic-split land visually. `oc kustomize` renders the
> GitOps source **offline** — handy to show "what Argo will apply."

---

> **◐ Partially verified (cluster asleep at authoring).** `oc kustomize` (GitOps source
> rendering) was run **live offline** and is real. Everything that needs a **live cluster +
> Operators** (Argo CD sync, pipeline runs, sidecar injection, mesh routing) is labelled
> **"requires a cluster — representative of OpenShift 4.18"**. These can be validated when
> the cluster is up (Application/pipeline/mesh-CR steps as a project user; Operator install
> + cluster-scoped mesh config as admin).
