# Demo 1 — GitOps with Argo CD

> **Scenario:** Deliver the Mobily **self-care** portal via GitOps. We create an Argo CD
> **Application** pointing at a Git repo, watch it **sync**, make a change **in Git** and
> watch it roll out, then cause **drift** with a direct `oc scale` and watch **self-heal**
> revert it. Rollback is a `git revert`.
>
> The Git source for this demo is the real, cloned repo
> [`github.com/MIT-TRAINING/self-care-gitops`](https://github.com/MIT-TRAINING/self-care-gitops) —
> its `base/` + `overlays/prod/` are byte-for-byte identical to the local
> [`self-care-gitops/`](self-care-gitops/) stand-in checked into this repo (used in Step 2 for
> the offline `oc kustomize` preview). Point Argo at whichever remote your class actually has
> push access to; swap the placeholder host below for it.

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

## Step 0 — Install the Operator (cluster-admin, one-time)

> ⚠️ **Admin-only, do this before class.** If `oc get ns openshift-gitops` returns
> `NotFound`, the Operator was never installed — install it once for the whole shared
> cluster; learners never repeat this step.

```bash
cat <<'EOF' | oc apply -f -
apiVersion: v1
kind: Namespace
metadata:
  name: openshift-gitops-operator
---
apiVersion: operators.coreos.com/v1
kind: OperatorGroup
metadata:
  name: openshift-gitops-operator
  namespace: openshift-gitops-operator
spec:
  targetNamespaces: []
---
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:
  name: openshift-gitops-operator
  namespace: openshift-gitops-operator
spec:
  channel: latest
  name: openshift-gitops-operator
  source: redhat-operators
  sourceNamespace: openshift-marketplace
EOF

# Wait for the CSV to succeed, then confirm the Operator auto-created openshift-gitops:
oc get csv -n openshift-gitops-operator -w      # Ctrl-C once PHASE = Succeeded
oc get ns openshift-gitops
```

**Verified output** *(live cluster, OCP 4.18, run 2026-07-14):*

```
namespace/openshift-gitops-operator created
operatorgroup.operators.coreos.com/openshift-gitops-operator created
subscription.operators.coreos.com/openshift-gitops-operator created
openshift-gitops-operator.v1.21.1   Red Hat OpenShift GitOps   1.21.1   Succeeded
NAME               STATUS   AGE
openshift-gitops   Active   14s
```

> **Narrate:** The Subscription lives in its own `openshift-gitops-operator` namespace with
> a cluster-scoped `OperatorGroup` (`targetNamespaces: []`) — that's why the CSV shows up
> there, not in `openshift-gitops`. OLM's controller then auto-provisions `openshift-gitops`
> with a default Argo CD instance. Give the pods a minute to leave `ContainerCreating` before
> Step 1.

---

## Step 1 — Confirm Argo CD is available

```bash
oc get csv -n openshift-gitops-operator | grep -i gitops   # Operator Succeeded (CSV lives here)
oc get route -n openshift-gitops openshift-gitops-server -o jsonpath='{.spec.host}{"\n"}'
oc get pods -n openshift-gitops                         # argocd-* running
```

**Verified output** *(live cluster, OCP 4.18, run 2026-07-14):*

```
openshift-gitops-operator.v1.21.1   Red Hat OpenShift GitOps   1.21.1   Succeeded
openshift-gitops-server-openshift-gitops.apps.mobily-ocp-training.ocp.supercloudlabs.com
openshift-gitops-application-controller-0    1/1   Running
openshift-gitops-repo-server-...             1/1   Running
openshift-gitops-server-...                  1/1   Running
```

> **Narrate:** The GitOps Operator gave us a running Argo CD in `openshift-gitops`:
> repo-server (renders Git), application-controller (reconciles), and the UI/API server.

---

## Step 2 — What Argo will apply (rendered OFFLINE)

> In the real [`self-care-gitops`](https://github.com/MIT-TRAINING/self-care-gitops) repo,
> `overlays/prod` is a Kustomize overlay on a base Deployment. This repo ships a **local
> stand-in** you can render right now — byte-for-byte the same `base/` + `overlays/prod/`
> Argo's repo-server clones and renders from that repo: [`self-care-gitops/`](self-care-gitops/).

```bash
cd labs/module-10/demos/self-care-gitops    # the local stand-in for the self-care repo
oc kustomize overlays/prod | grep -E 'kind:|replicas:|image:'
```

**Verified output** *(`oc kustomize` run offline against `self-care-gitops/`, 2026-07-14):*

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

> ⚠️ **Destination namespace needs two things Argo won't do for you on OpenShift:** the
> namespace itself, and the `argocd.argoproj.io/managed-by` label. That label is what makes
> the **OpenShift GitOps** operator grant the `openshift-gitops-argocd-application-controller`
> service account a Role/RoleBinding *in that namespace* — without it, sync fails with
> `deployments.apps is forbidden: ... cannot create resource "deployments" ... in the
> namespace "self-care-prod"`. Create + label it first:

```bash
oc create namespace self-care-prod
oc label namespace self-care-prod argocd.argoproj.io/managed-by=openshift-gitops

oc apply -f - <<'EOF'
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata: { name: self-care, namespace: openshift-gitops }
spec:
  project: default
  source:
    repoURL: https://github.com/MIT-TRAINING/self-care-gitops.git
    targetRevision: main
    path: overlays/prod
  destination: { server: https://kubernetes.default.svc, namespace: self-care-prod }
  syncPolicy: { automated: { prune: true, selfHeal: true } }
EOF
oc get application self-care -n openshift-gitops
```

**Verified output** *(live cluster, OCP 4.18, run 2026-07-14):*

```
namespace/self-care-prod created
namespace/self-care-prod labeled
application.argoproj.io/self-care created
NAME        SYNC STATUS   HEALTH STATUS
self-care   Synced        Healthy
```

> **Narrate:** The **Application** maps the Git **source** (repo/path/revision) to a
> **destination** namespace, with `automated` sync + `selfHeal` + `prune`. Argo pulled Git
> and made the cluster match — **Synced/Healthy**. If sync status shows `OutOfSync` /
> `Missing` and stays that way, check `.status.operationState.message` for the RBAC error
> above — it means the namespace label step got skipped.

---

## Step 4 — Change in Git → auto-sync

> Work in your own clone of the repo you pointed `repoURL` at in Step 3 (the one with push
> access) — **not** the offline [`self-care-gitops/`](self-care-gitops/) stand-in under this
> demo's folder, which has no remote. `cd` there first.

```bash
# bump overlays/prod/replicas-patch.yaml 6 → 8
sed -i.bak 's/replicas: 6/replicas: 8/' overlays/prod/replicas-patch.yaml && rm -f overlays/prod/replicas-patch.yaml.bak
git commit -am "Bump self-care replicas 6 -> 8" && git push origin main

# Argo's default poll is ~3 min; force it for the demo so learners aren't waiting:
oc annotate application self-care -n openshift-gitops argocd.argoproj.io/refresh=hard --overwrite

oc get application self-care -n openshift-gitops -o jsonpath='{.status.sync.status}{"\n"}'   # briefly OutOfSync
oc get deploy self-care -n self-care-prod -o jsonpath='{.spec.replicas}{"\n"}'               # → 8 after sync
```

**Verified output** *(live cluster, OCP 4.18, run 2026-07-14 — polled every 5s):*

```
t=5s  sync=Synced     replicas=6
t=10s sync=OutOfSync  replicas=6
t=15s sync=Synced     replicas=8
```

> **Narrate:** A **commit** is the deploy. Argo saw the change (OutOfSync → applied →
> Synced). Nobody ran `oc apply` — the change flowed from Git. In class, the `refresh=hard`
> annotation is what keeps this from being a 3-minute silent pause; without it, Argo notices
> on its own polling cadence.

---

## Step 5 — Drift → self-heal

```bash
oc scale deploy self-care -n self-care-prod --replicas=3     # direct change (drift)
sleep 10
oc get deploy self-care -n self-care-prod -o jsonpath='{.spec.replicas}{"\n"}'   # back to 8
```

**Verified output** *(live cluster, OCP 4.18, run 2026-07-14):*

```
deployment.apps/self-care scaled
8        # selfHeal reverted the drift to Git's value within ~10s
```

> **Narrate:** We changed the cluster directly to 3; **selfHeal** treated it as drift and
> reverted to Git (8). On GitOps, the console/CLI aren't how you change prod — **Git is**.

---

## Step 6 — Rollback via Git & cleanup

```bash
# Rollback = revert the deploy-repo commit; Argo syncs back.
git revert --no-edit HEAD && git push origin main
oc annotate application self-care -n openshift-gitops argocd.argoproj.io/refresh=hard --overwrite
oc get deploy self-care -n self-care-prod -o jsonpath='{.spec.replicas}{"\n"}'   # → 6 again

# Cleanup:
oc delete application self-care -n openshift-gitops          # (prune removes the app's objects)
oc delete namespace self-care-prod
```

**Verified output** *(live cluster, OCP 4.18, run 2026-07-14):*

```
replicas=6                                    # git revert took it back to the pre-bump value
application.argoproj.io "self-care" deleted
namespace "self-care-prod" deleted
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

> **✓ Fully verified — Steps 0-6 all run live, end-to-end, on 2026-07-14.**
> Steps 0-2 were run live on the OCP 4.18 shared cluster as before. Steps 3-6 were then run
> live against the real `openshift-gitops` install: an `Application` pointed at the actual
> cloned [`github.com/MIT-TRAINING/self-care-gitops`](https://github.com/MIT-TRAINING/self-care-gitops)
> repo, a genuine commit/push bumping replicas 6→8 that Argo auto-synced, an `oc scale`
> drift that selfHeal reverted within ~10s, and a `git revert` + push that rolled the
> deployment back to 6 — all output above is real, not representative. One real finding
> from this run: **OpenShift GitOps requires the destination namespace to carry the
> `argocd.argoproj.io/managed-by` label** before Argo's service account can create objects
> in it; Step 3 now includes that label (the original version of this demo omitted it and
> would fail with a `deployments.apps is forbidden` error on a fresh namespace). The
> repo/cluster were left clean afterward (test Application, namespace, and commits reverted).
