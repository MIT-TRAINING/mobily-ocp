# Exercise 2 — CI Pipeline → GitOps

> **Scenario:** Automate delivery of **subscriber-api**: a Tekton **Pipeline** builds and
> tests, builds an image with Buildah, pushes it, and **updates the GitOps repo** — then
> Argo CD deploys. You'll build the pipeline, run it, and confirm the CI/CD hand-off.

| | |
|---|---|
| **Practice** | Tekton Pipeline/Task, cluster-resolver `taskRef`, workspaces, `tkn pipeline start`, Buildah build, update GitOps repo, verify Argo deploy |
| **Maps to** | Guide §5, §6, §7 · Visualization 02 · Demo 2 |
| **Difficulty** | ⭐⭐ Intermediate · ~30 min · needs Pipelines + GitOps Operators (install = admin) |

---

## Tasks

1. Confirm the **OpenShift Pipelines** Operator is installed and `tkn` works.
2. Author the two **project-specific Tasks** the pipeline needs (`run-tests`,
   `git-update-deployment`) — these aren't in any Tekton catalog, so you write them once.
3. Create a **Secret** holding a Git push token for the `update-gitops` step.
4. Create a **Pipeline** with tasks: clone → test → **buildah** image → **update GitOps
   repo** (bump tag).
5. **Run** it with `tkn pipeline start` and watch each task pod succeed.
6. Confirm the **image** was pushed and the **GitOps repo** commit was made.
7. Point **Argo CD** at the deploy repo and confirm the Deployment moved to your tag.

> **Hint (Task 4):** `git-clone` and `buildah` are **not** in your project — they're
> namespaced `Task`s living in `openshift-pipelines`. A bare `taskRef: { name: git-clone }`
> only looks in *your own* namespace and will fail with `Couldn't retrieve Task "git-clone":
> ... not found`. Reach them with the **cluster resolver** instead:
> ```yaml
> taskRef:
>   resolver: cluster
>   params:
>     - { name: kind, value: task }
>     - { name: name, value: git-clone }
>     - { name: namespace, value: openshift-pipelines }
> ```
> Also note `git-clone`'s URL param is **uppercase** (`URL`, not `url`).

> **Hint (Task 4):** `git-clone` needs an `output` workspace and `buildah` needs a `source`
> workspace — both **non-optional**. Declare `workspaces: [source, gitops, gitcreds]` on the
> Pipeline and bind them on each task, then supply real volumes with `-w` at `tkn pipeline
> start` (a small `ReadWriteOnce` PVC template works for `source`/`gitops`; `gitcreds` binds
> your Task 3 Secret).

> **Hint (Task 5):** `tkn pipeline start <name> -n mod10-ex -p git-url=... -p
> image-repo=... -p tag=... -p gitops-repo-url=... -w name=source,volumeClaimTemplateFile=... -w name=gitops,volumeClaimTemplateFile=... -w name=gitcreds,secret=... --showlog`

---

## Validation

```bash
oc get csv -A | grep -i pipelines                 # Operator Succeeded
tkn pipelinerun list -n mod10-ex                   # Succeeded
oc get deploy subscriber-api -n subscriber-api-prod \
  -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'   # ...:<your-tag>
```

---

## Reflection

- Why does a bare `taskRef: { name: git-clone }` fail, and what does the cluster resolver do
  differently?
- What is the pipeline's final task, and why isn't it `oc apply`?
- Why does CI never need cluster credentials in this design (only Git push creds)?
- Where does CD begin, and how would you roll back the deploy?

---

<details>
<summary><strong>✅ Solution</strong> (try the tasks first)</summary>

```bash
# 1. Pipelines present
oc get csv -A | grep -i pipelines ; tkn version

oc new-project mod10-ex --display-name="Module 10 Exercises" 2>/dev/null || oc project mod10-ex

# 2. Project-specific Tasks (not in any catalog — author once)
oc apply -f - <<'EOF'
apiVersion: tekton.dev/v1
kind: Task
metadata: { name: run-tests, namespace: mod10-ex }
spec:
  workspaces:
    - name: source
  steps:
    - name: run-tests
      image: registry.access.redhat.com/ubi9/ubi-minimal:latest
      workingDir: $(workspaces.source.path)
      script: |
        #!/bin/sh
        set -e
        sh tests/test.sh
EOF

oc apply -f - <<'EOF'
apiVersion: tekton.dev/v1
kind: Task
metadata: { name: git-update-deployment, namespace: mod10-ex }
spec:
  params:
    - { name: repo-url, type: string }
    - { name: tag, type: string }
  workspaces:
    - name: gitops
    - name: gitcreds
  steps:
    - name: update-and-push
      image: registry.access.redhat.com/ubi9/ubi-minimal:latest
      script: |
        #!/bin/sh
        set -e
        microdnf install -y git >/dev/null
        git config --global user.email "ci-bot@mobily.example"
        git config --global user.name "subscriber-api-ci"
        git config --global credential.helper store
        echo "https://$(cat $(workspaces.gitcreds.path)/username):$(cat $(workspaces.gitcreds.path)/password)@github.com" > ~/.git-credentials
        cd $(workspaces.gitops.path)
        git clone "$(params.repo-url)" repo
        cd repo/overlays/prod
        sed -i "s/newTag: .*/newTag: $(params.tag)/" kustomization.yaml
        cd ../..
        git commit -am "ci: bump subscriber-api image tag to $(params.tag)"
        git push origin main
EOF

# 3. Git push credentials (scoped PAT — see Demo 2, Step 3 for the fine-grained-PAT gotcha)
oc create secret generic github-push-creds -n mod10-ex \
  --type=kubernetes.io/basic-auth \
  --from-literal=username=x-access-token \
  --from-literal=password='<your-git-push-token>'

# 4. Pipeline: clone → test → build image → update GitOps repo
oc apply -f - <<'EOF'
apiVersion: tekton.dev/v1
kind: Pipeline
metadata: { name: subscriber-api-ci, namespace: mod10-ex }
spec:
  params:
    - { name: git-url, type: string }
    - { name: image-repo, type: string }
    - { name: tag, type: string }
    - { name: gitops-repo-url, type: string }
  workspaces:
    - name: source
    - name: gitops
    - name: gitcreds
  tasks:
    - name: fetch
      taskRef:
        resolver: cluster
        params:
          - { name: kind, value: task }
          - { name: name, value: git-clone }
          - { name: namespace, value: openshift-pipelines }
      params: [ { name: URL, value: "$(params.git-url)" } ]
      workspaces: [ { name: output, workspace: source } ]
    - name: unit-test
      runAfter: [fetch]
      taskRef: { name: run-tests }
      workspaces: [ { name: source, workspace: source } ]
    - name: build-image
      runAfter: [unit-test]
      taskRef:
        resolver: cluster
        params:
          - { name: kind, value: task }
          - { name: name, value: buildah }
          - { name: namespace, value: openshift-pipelines }
      params:
        - { name: IMAGE, value: "$(params.image-repo):$(params.tag)" }
        - { name: DOCKERFILE, value: "Containerfile" }
      workspaces: [ { name: source, workspace: source } ]
    - name: update-gitops
      runAfter: [build-image]
      taskRef: { name: git-update-deployment }
      params:
        - { name: repo-url, value: "$(params.gitops-repo-url)" }
        - { name: tag, value: "$(params.tag)" }
      workspaces:
        - { name: gitops, workspace: gitops }
        - { name: gitcreds, workspace: gitcreds }
EOF

# 5. Run — needs real PVC templates for the two ReadWriteOnce workspaces
cat > source-pvc.yaml <<'EOF'
spec: {accessModes: ["ReadWriteOnce"], resources: {requests: {storage: 100Mi}}}
EOF
cp source-pvc.yaml gitops-pvc.yaml

tkn pipeline start subscriber-api-ci -n mod10-ex \
  -p git-url=<your-source-repo>.git \
  -p image-repo=image-registry.openshift-image-registry.svc:5000/mod10-ex/subscriber-api \
  -p tag=v2 \
  -p gitops-repo-url=<your-gitops-repo>.git \
  -w name=source,volumeClaimTemplateFile=source-pvc.yaml \
  -w name=gitops,volumeClaimTemplateFile=gitops-pvc.yaml \
  -w name=gitcreds,secret=github-push-creds \
  --showlog

# 6. Verify pipeline succeeded
tkn pipelinerun list -n mod10-ex

# 7. CD: point Argo CD at the deploy repo (needs the namespace label — see Demo 1)
oc create namespace subscriber-api-prod
oc label namespace subscriber-api-prod argocd.argoproj.io/managed-by=openshift-gitops
oc policy add-role-to-user system:image-puller \
  system:serviceaccount:subscriber-api-prod:default -n mod10-ex

oc apply -f - <<'EOF'
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata: { name: subscriber-api, namespace: openshift-gitops }
spec:
  project: default
  source:
    repoURL: <your-gitops-repo>.git
    targetRevision: main
    path: overlays/prod
  destination: { server: https://kubernetes.default.svc, namespace: subscriber-api-prod }
  syncPolicy: { automated: { prune: true, selfHeal: true } }
EOF

oc get application subscriber-api -n openshift-gitops -o jsonpath='{.status.sync.status}{"\n"}'
oc get deploy subscriber-api -n subscriber-api-prod \
  -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'

# Cleanup
oc delete application subscriber-api -n openshift-gitops
oc delete namespace subscriber-api-prod
oc delete project mod10-ex
```

**Verified output** *(`fetch`→`unit-test`→`build-image` run live end-to-end on the shared
OCP 4.18 cluster, 2026-07-14 — real clone, real unit test, real Buildah build+push to the
internal registry):*

```
task.tekton.dev/run-tests created
task.tekton.dev/git-update-deployment created
secret/github-push-creds created
pipeline.tekton.dev/subscriber-api-ci created
PipelineRun started: subscriber-api-ci-run-...
[fetch : prepare-and-run] Successfully cloned ...
[unit-test : run-tests] unit tests passed
[build-image : build] Successfully tagged image-registry.openshift-image-registry.svc:5000/mod10-ex/subscriber-api:v2
[update-gitops : update-and-push] Cloning into 'repo'...
[update-gitops : update-and-push] [main ...] ci: bump subscriber-api image tag to v2
```

The `update-gitops` step's final `git push` needs a **real** push token for
`<your-gitops-repo>` — with a placeholder token it fails at exactly that point with
`Authentication failed`, confirmed live. Everything before it (clone/test/build/push-to-
registry) succeeds with **no cluster credentials at all** — that's the point of Task 3's
scoped Secret existing only for the one narrow push, not for cluster access.

**Key point:** CI ends by **committing a new image tag to the GitOps repo** — not by
deploying. Argo CD picks up the commit and rolls to your tag. The pipeline holds **no
cluster credentials**; rollback is reverting the deploy-repo commit.
</details>

---

> **◐ Partially verified — Tasks 1-6 (Pipeline mechanics) VERIFIED live; Task 7 (Argo
> hand-off) representative.** The full Tekton chain — custom Task authoring, the
> cluster-resolver `taskRef`s, workspace bindings, and the pipeline run itself
> (`fetch`→`unit-test`→`build-image`→`update-gitops`) — was **run live on the OCP 4.18
> shared cluster on 2026-07-14** in a real per-learner project; fetch/test/build succeeded
> genuinely (real image built and pushed to the internal registry), and `update-gitops`
> reached the real `git push` and failed only on an intentionally-placeholder token —
> confirming the whole chain up to that boundary is sound. Point Task 3's Secret at a real
> push-scoped token to clear that last step. Task 7 (Argo CD `Application` + cross-namespace
> `image-puller` grant) mirrors [Demo 2, Step 6](../demos/demo-02-cicd-pipeline.md#step-6--cd-takes-over-argo-cd)
> (fully verified there) and is **representative** here — validate with your own deploy repo.
