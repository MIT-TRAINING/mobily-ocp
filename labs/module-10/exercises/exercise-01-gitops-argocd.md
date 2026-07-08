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

1. **Offline:** render the GitOps source with `oc kustomize overlays/prod` and confirm the
   `replicas`/`image` it would apply.
2. Create an Argo CD **Application** pointing at the repo/path with `automated` sync +
   `selfHeal` + `prune`.
3. Confirm **SYNC STATUS = Synced** and **HEALTH = Healthy**.
4. **Drift:** `oc scale` the deployment directly, then confirm selfHeal reverts it to Git.
5. Explain how you'd **roll back** the app to a previous version.

> **Hint (Task 2):** the Application lives in `openshift-gitops`; `spec.source` = repo/path/
> targetRevision, `spec.destination` = server + namespace.

---

## Validation

```bash
oc kustomize overlays/prod | grep -E 'replicas:|image:'            # offline preview
oc get application self-care -n openshift-gitops                   # Synced / Healthy
oc scale deploy self-care -n self-care-prod --replicas=3; sleep 10
oc get deploy self-care -n self-care-prod -o jsonpath='{.spec.replicas}{"\n"}'   # reverts to Git value
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
oc kustomize overlays/prod | grep -E 'replicas:|image:'

# 2. Application (in openshift-gitops)
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

**Representative output** *(oc kustomize verified offline; Argo steps need a cluster — OCP 4.18):*

```
  replicas: 6
      - image: registry.access.redhat.com/ubi9/httpd-24:latest
NAME        SYNC STATUS   HEALTH STATUS
self-care   Synced        Healthy
6        # selfHeal reverted the oc scale
```

**Key point:** Git is the source of truth; Argo CD reconciles the cluster to it. `selfHeal`
undoes direct cluster edits (drift); rollback is `git revert`. `oc kustomize` shows exactly
what Argo's repo-server will render — offline.
</details>

---

> **◐ Partially verified — `oc kustomize` VERIFIED offline (oc 4.22); Argo steps
> representative.** The GitOps source render (Task 1) is real. Application sync/drift/
> self-heal **require a live cluster + GitOps Operator** and are **representative of
> OpenShift 4.18** — validate when the cluster is up (Application as a project user).
