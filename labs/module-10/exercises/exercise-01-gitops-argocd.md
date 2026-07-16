# Exercise 1 — Deploy an App with Argo CD

> **Scenario:** Put the Mobily **self-care** portal under GitOps. Create an Argo CD
> **Application** from a Git repo, confirm it syncs, cause **drift** and watch self-heal,
> then roll back via Git.

| | |
|---|---|
| **Practice** | Application CR, Synced/OutOfSync, automated sync + selfHeal, drift, git rollback |
| **Maps to** | Guide §2, §3, §4 · Visualization 01 · Demo 1 |
| **Difficulty** | ⭐ Beginner · ~20 min · GitOps Operator install needs admin; Application is a project-user action |

---

## Tasks

> This repo ships a local stand-in for the `self-care.git` GitOps source at
> [`../demos/self-care-gitops/`](../demos/self-care-gitops/) (`base/` + `overlays/prod/`) —
> `cd` there before running `oc kustomize`.

1. **Offline:** render the GitOps source with `oc kustomize overlays/prod` and confirm the
   `replicas`/`image` it would apply.
2. Create an Argo CD **Application** pointing at the repo/path with `automated` sync +
   `selfHeal` + `prune`.
3. Confirm **SYNC STATUS = Synced** and **HEALTH = Healthy**.
4. **Drift:** `oc scale` the deployment directly, then confirm selfHeal reverts it to Git.
5. Explain how you'd **roll back** the app to a previous version.

> **Hint (Task 2):** the Application lives in `openshift-gitops`; `spec.source` = repo/path/
> targetRevision, `spec.destination` = server + namespace.

> **Hint (Task 2, easy to miss):** on OpenShift GitOps, the *destination* namespace needs
> the label `argocd.argoproj.io/managed-by: openshift-gitops` **before** you create the
> Application — that label is what grants the `openshift-gitops-argocd-application-controller`
> service account RBAC to create objects there. Without it, sync sticks at `OutOfSync` /
> `Missing` with a `deployments.apps is forbidden` error in `.status.operationState.message`.

---

## Validation

```bash
cd ../demos/self-care-gitops                                       # local stand-in repo
oc kustomize overlays/prod | grep -E 'replicas:|image:'            # offline preview
oc get application self-care -n openshift-gitops                   # Synced / Healthy
oc scale deploy self-care -n self-care-prod --replicas=3; sleep 10
oc get deploy self-care -n self-care-prod -o jsonpath='{.spec.replicas}{"\n"}'   # reverts to Git value
```

**Verified output** *(live cluster, OCP 4.18, run 2026-07-16 — real GitHub repo, real Argo CD):*

```
  replicas: 6
      - image: registry.access.redhat.com/ubi9/httpd-24:latest
NAME        SYNC STATUS   HEALTH STATUS
self-care   Synced        Healthy
6        # selfHeal reverted the oc scale --replicas=3 back to Git's value
```

---

## Reflection

- Where is the desired state, and who applies it?
- What happens to a direct `oc scale` under `selfHeal: true`?
- Why is `git revert` the rollback mechanism in GitOps?

---

<details>
<summary><strong>✅ Solution</strong> (try the tasks first)</summary>

```bash
# 1. Preview the GitOps source (OFFLINE)
cd ../demos/self-care-gitops                                       # local stand-in repo
oc kustomize overlays/prod | grep -E 'replicas:|image:'

# 2. Destination namespace needs the managed-by label BEFORE the Application syncs
oc create namespace self-care-prod
oc label namespace self-care-prod argocd.argoproj.io/managed-by=openshift-gitops

# Application (in openshift-gitops) — point repoURL at your own fork in a real class;
# this is the actual repo used to validate this exercise:
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

# 3. Status
oc get application self-care -n openshift-gitops         # Synced / Healthy

# 4. Drift → self-heal
oc scale deploy self-care -n self-care-prod --replicas=3
sleep 10
oc get deploy self-care -n self-care-prod -o jsonpath='{.spec.replicas}{"\n"}'   # back to Git value

# 5. Rollback = git revert <sha> && git push  (or targetRevision: <old-sha>) → Argo syncs back

# Cleanup
oc delete application self-care -n openshift-gitops
```

**Verified output** *(live cluster, OCP 4.18, run 2026-07-16 — real GitHub repo, real Argo CD):*

```
  replicas: 6
      - image: registry.access.redhat.com/ubi9/httpd-24:latest
namespace/self-care-prod created
namespace/self-care-prod labeled
NAME        SYNC STATUS   HEALTH STATUS
self-care   Synced        Healthy
6        # selfHeal reverted the oc scale --replicas=3 back to Git's value
```

**Key point:** Git is the source of truth; Argo CD reconciles the cluster to it. `selfHeal`
undoes direct cluster edits (drift); rollback is `git revert`. `oc kustomize` shows exactly
what Argo's repo-server will render — offline. The `managed-by` namespace label isn't
optional on OpenShift GitOps — skip it and sync silently sticks at `OutOfSync`.
</details>

---

> **✓ Fully verified — every task run live on OCP 4.18, 2026-07-16.** The offline
> `oc kustomize` render (Task 1), the Application create/sync (Task 2-3), and the drift/
> self-heal round-trip (Task 4) were all run against the real
> [`MIT-TRAINING/self-care-gitops`](https://github.com/MIT-TRAINING/self-care-gitops) repo
> and a real `openshift-gitops` instance — this is the same mechanism validated in
> [Demo 1](../demos/demo-01-gitops-argocd.md), including the `managed-by` namespace-label
> finding. Point `repoURL` at your own fork for class use; the cluster/namespace were left
> clean afterward.
