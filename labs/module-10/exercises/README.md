# Module 10 — Exercises (Hands-On Practice)

These are **participant-driven** tasks. You drive **`oc`** plus **`argocd`**/**`tkn`** and
Service Mesh CRs, then verify with the provided **validation** commands. Each exercise has
a fully worked **solution** — try the tasks first, then check.

Module 10 — **"GitOps, CI/CD and Service Mesh"** — covers **GitOps/Argo CD**, **CI/CD
pipelines** (Jenkins→GitOps), and **Service Mesh**. Argo CD, Pipelines, and Service Mesh
are installed as **Operators** (Module 9).

## Where to run these

| Target | What you can do | Notes |
|---|---|---|
| **Shared OpenShift 4.18 cluster** (preferred) | Argo Application, PipelineRun, mesh CRs in your project | Operator install + cluster-scoped mesh config need **cluster-admin** |
| **[Developer Sandbox](https://developers.redhat.com/developer-sandbox)** | May have GitOps/Pipelines pre-installed | No cluster-admin → follow instructor for installs/mesh control plane |
| **Local (no cluster)** | `oc kustomize` / `helm template` render the GitOps source offline | Chart/manifest authoring is fully offline |

> **CLIs:** `argocd` (Argo CD), `tkn` (Tekton). `oc kustomize` renders the GitOps source
> **without a cluster** — great for previewing what Argo will apply.

## Exercises in this module

| # | Exercise | What you'll practice | Telecom scenario | Difficulty |
|---|----------|----------------------|------------------|------------|
| 1 | [Deploy an app with Argo CD](exercise-01-gitops-argocd.md) | Application CR, sync, drift/self-heal, git rollback | **self-care** via GitOps | ⭐ Beginner |
| 2 | [CI pipeline → GitOps](exercise-02-cicd-pipeline.md) | Tekton Pipeline/Task, build image, update GitOps repo | **subscriber-api** :v2 | ⭐⭐ Intermediate |
| 3 | [Build→GitOps→Mesh canary (capstone)](exercise-03-capstone.md) | pipeline + Argo + sidecar + VirtualService canary | end-to-end **tariff-catalog** | ⭐⭐⭐ Advanced |

## Before you start

```bash
oc login https://api.<cluster-domain>:6443 -u <user> -p "$OCP_PASSWORD"   # or token
oc whoami
oc get csv -A | grep -Ei 'gitops|pipelines|servicemesh'   # Operators present?
oc new-project mod10-ex --display-name="Module 10 Exercises" 2>/dev/null || oc project mod10-ex
```

- Images: **`ubi9/httpd-24`** (rootless, HTTP on **8080**; bare `GET /` → **403** proves
  connectivity).
- Replace placeholders (`<cluster-domain>`, `<git-repo>`). **Never commit real tokens** —
  use Git deploy keys / SA tokens as placeholders.
- **Operator install + cluster-scoped mesh config** need **cluster-admin**; Applications,
  PipelineRuns, and namespaced mesh CRs are project-user actions once Operators exist.
- Cleanup: `oc delete project mod10-ex`; delete Applications/Pipelines/mesh CRs you created.

## How to self-assess

Each exercise's **Validation** section gives commands whose output confirms success.
`oc kustomize` / `helm template` let you check the GitOps source **without a cluster**.
Stuck? The **Solution** walks one correct approach.

Companion material: the guided [demos](../demos/README.md), the interactive
[visualizations](../index.html), and the
[concept guide](../../../guides/module-10-gitops-cicd-servicemesh.md).

---

> **◐ Partially verified (cluster asleep at authoring).** `oc kustomize` (GitOps source
> rendering) was run **live offline** (real). Steps needing a **live cluster + Operators**
> (Argo sync, PipelineRun, mesh routing) are **representative of OpenShift 4.18** and can be
> validated when the cluster is up (Application/pipeline/mesh CRs as a project user;
> Operator install + mesh control plane as admin).
