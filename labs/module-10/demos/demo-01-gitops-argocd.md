# Demo 1 — GitOps with Argo CD

> **Scenario:** Deliver the Mobily **self-care** portal via GitOps. We create an Argo CD
> **Application** pointing at a Git repo, watch it **sync**, make a change **in Git** and
> watch it roll out, then cause **drift** with a direct `oc scale` and watch **self-heal**
> revert it. Rollback is a `git revert`.

| | |
|---|---|
| **Concepts reinforced** | Application CR · Synced/OutOfSync · automated sync · selfHeal (drift) · prune · rollback via Git |
| **Maps to** | Guide §2, §3, §4 · Visualization 01 · Exercise 1 |
| **Time** | ~30 minutes |
| **Cluster** | Shared OCP 4.18 with the **OpenShift GitOps** Operator (install needs admin; creating an Application can be a project user) |

---

> **⎈ Kubernetes equivalent:** Argo CD is the same on any Kubernetes; the `Application`/
> `AppProject` CRDs come from the GitOps Operator (`argoproj.io`).

> ⚠️ Installing the GitOps Operator needs **cluster-admin**. Once installed, creating an
> Application in your namespace is a normal-user action (with the right RBAC).

## Talking points to open with

- **Git is the source of truth**; Argo CD reconciles the cluster to it — you don't
  `oc apply`.
- **selfHeal** means manual cluster changes are treated as **drift** and reverted.
- **Rollback = git**: revert the commit (or target an older revision) and let Argo sync.

---

## Step 1 — Confirm Argo CD is available

```bash
oc get csv -n openshift-gitops | grep -i gitops        # Operator Succeeded
oc get route -n openshift-gitops openshift-gitops-server -o jsonpath='{.spec.host}{"\n"}'
oc get pods -n openshift-gitops                         # argocd-* running
```

**Expected output** *(requires a cluster — representative of OCP 4.18):*

```
openshift-gitops-operator.v1.x.y   OpenShift GitOps   1.x.y   Succeeded
openshift-gitops-server-openshift-gitops.apps.<cluster-domain>
argocd-application-controller-0    1/1   Running
openshift-gitops-repo-server-...   1/1   Running
openshift-gitops-server-...        1/1   Running
```

> **Narrate:** The GitOps Operator gave us a running Argo CD in `openshift-gitops`:
> repo-server (renders Git), application-controller (reconciles), and the UI/API server.

---

## Step 2 — What Argo will apply (rendered OFFLINE)

```bash
# The Git repo holds Kustomize; this is exactly what Argo's repo-server renders:
oc kustomize overlays/prod | grep -E 'kind:|replicas:|image:'
```

**Verified output** *(oc 4.22 `kustomize`, run offline — no cluster):*

```
kind: Deployment
  replicas: 6
      - image: registry.access.redhat.com/ubi9/httpd-24:latest
```

> **Narrate:** Argo CD doesn't invent manifests — its **repo-server renders your Git**
> (plain YAML, Helm, or Kustomize). `oc kustomize` shows the same output locally, so you
> can preview a change before it ever hits the cluster.

---

## Step 3 — Create the Application

```bash
oc apply -f - <<'EOF'
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata: { name: self-care, namespace: openshift-gitops }
spec:
  project: default
  source:
    repoURL: https://git.mobily.example/self-care.git
    targetRevision: main
    path: overlays/prod
  destination: { server: https://kubernetes.default.svc, namespace: self-care-prod }
  syncPolicy: { automated: { prune: true, selfHeal: true } }
EOF
oc get application self-care -n openshift-gitops
```

**Expected output** *(requires a cluster — representative):*

```
application.argoproj.io/self-care created
NAME        SYNC STATUS   HEALTH STATUS
self-care   Synced        Healthy
```

> **Narrate:** The **Application** maps the Git **source** (repo/path/revision) to a
> **destination** namespace, with `automated` sync + `selfHeal` + `prune`. Argo pulled Git
> and made the cluster match — **Synced/Healthy**.

---

## Step 4 — Change in Git → auto-sync

```bash
# In the Git repo: bump overlays/prod replicas 6 → 8, commit, push. Then:
oc get application self-care -n openshift-gitops -o jsonpath='{.status.sync.status}{"\n"}'   # briefly OutOfSync
oc get deploy self-care -n self-care-prod -o jsonpath='{.spec.replicas}{"\n"}'               # → 8 after sync
```

**Expected output** *(requires a cluster — representative):*

```
Synced          # after automated sync applies the new commit
8
```

> **Narrate:** A **commit** is the deploy. Argo saw the change (OutOfSync → applied →
> Synced). Nobody ran `oc apply` — the change flowed from Git.

---

## Step 5 — Drift → self-heal

```bash
oc scale deploy self-care -n self-care-prod --replicas=3     # direct change (drift)
sleep 10
oc get deploy self-care -n self-care-prod -o jsonpath='{.spec.replicas}{"\n"}'   # back to 8
```

**Expected output** *(requires a cluster — representative):*

```
deployment.apps/self-care scaled
8        # selfHeal reverted the drift to Git's value
```

> **Narrate:** We changed the cluster directly to 3; **selfHeal** treated it as drift and
> reverted to Git (8). On GitOps, the console/CLI aren't how you change prod — **Git is**.

---

## Step 6 — Rollback via Git & cleanup

```bash
# Rollback = revert the deploy-repo commit (or target an older revision); Argo syncs back.
# git revert <sha> && git push     → self-care returns to the previous replicas/image.
oc delete application self-care -n openshift-gitops          # (prune removes the app's objects)
```

**Expected output** *(representative):*

```
application.argoproj.io "self-care" deleted
```

> **Narrate:** No special rollback tooling — **`git revert`** is the rollback, and it's
> auditable. Deleting the Application (with prune) tears down what it deployed.

---

## Wrap-up questions to pose

1. Where is the desired state, and who applies it to the cluster?
2. What does `selfHeal` do when someone runs `oc scale` directly?
3. How do you roll back a GitOps-managed app?
4. What does Argo's repo-server do with a Kustomize/Helm source?

---

> **◐ Partially verified — Step 2 VERIFIED offline, cluster steps representative.**
> `oc kustomize` (Step 2) was **run live offline with oc 4.22** — real output. Steps needing
> a **live cluster + GitOps Operator** (Application sync, drift/self-heal) are
> **representative of OpenShift 4.18**; validate when the cluster is up (Operator install as
> admin, Application as a project user). The GitOps sync/self-heal behaviour is documented,
> real Argo CD behaviour.
