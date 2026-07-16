# Demo 2 — CI Pipeline → GitOps

> **Scenario:** Automate delivery of the Mobily **subscriber-api**: a **pipeline** (Tekton;
> Jenkins equivalent noted) checks out the code, **builds and tests** it, builds a container
> **image** with Buildah, pushes it, and **updates the GitOps repo** — then **Argo CD**
> deploys. CI and CD stay cleanly separated.
>
> This demo uses two real, cloned GitHub repos:
> [`MIT-TRAINING/subscriber-api-ci`](https://github.com/MIT-TRAINING/subscriber-api-ci)
> (source: `Containerfile` + static content + `tests/test.sh` — what the pipeline clones,
> tests, and builds) and
> [`MIT-TRAINING/subscriber-api-gitops`](https://github.com/MIT-TRAINING/subscriber-api-gitops)
> (Kustomize `base/` + `overlays/prod/` — what the pipeline's last step commits to, and what
> Argo CD watches). Point at your own org's repos in a real delivery; swap the URLs below.

| | |
|---|---|
| **Concepts reinforced** | Pipeline/Task (Tekton) · Buildah build · push image · update GitOps repo · Argo CD deploys · CI vs CD boundary |
| **Maps to** | Guide §5, §6, §7 · Visualization 02 · Exercise 2 |
| **Time** | ~30 minutes |
| **Cluster** | Shared OCP 4.18 with **OpenShift Pipelines** (+ GitOps) Operators (install needs admin) |

---

> **⎈ Kubernetes equivalent:** Tekton `Pipeline`/`Task`/`PipelineRun` are CRDs from the
> Pipelines Operator. Jenkins runs the same idea from a Jenkinsfile.

> ⚠️ Installing the Pipelines/GitOps Operators needs **cluster-admin**. Running a
> `PipelineRun` in your namespace is a project-user action.

## Talking points to open with

- **CI = code → tested image**; **CD/GitOps = image → running.** Keep them separate.
- Tekton is **serverless** — each step is a pod; nothing runs when idle. Jenkins is the
  server-based alternative.
- The pipeline's **last step updates Git**, not the cluster — so CI holds **no cluster
  creds** (it does hold Git-push creds for the deploy repo — a different, narrower thing).

---

## Step 0 — Install the Pipelines Operator (cluster-admin, one-time)

> ⚠️ **Admin-only, do this before class.** If `oc get csv -A | grep -i pipelines` returns
> nothing, install once for the whole shared cluster; learners never repeat this step.

```bash
oc apply -f - <<'EOF'
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:
  name: openshift-pipelines-operator-rh
  namespace: openshift-operators
spec:
  channel: latest
  name: openshift-pipelines-operator-rh
  source: redhat-operators
  sourceNamespace: openshift-marketplace
EOF

# Wait for the CSV to succeed, then for the operator's TektonConfig to go Ready:
oc get csv -n openshift-operators -w                                     # Ctrl-C once PHASE = Succeeded
oc get tektonconfig config -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}{"\n"}'
```

**Verified output** *(live cluster, OCP 4.18, run 2026-07-14):*

```
subscription.operators.coreos.com/openshift-pipelines-operator-rh created
openshift-pipelines-operator-rh.v1.22.4   Red Hat OpenShift Pipelines   1.22.4   Succeeded
True
```

> **Narrate:** The Operator installs the full Tekton stack (`openshift-pipelines`
> namespace): pipelines/triggers/chains/results controllers, plus a set of **namespaced
> `Task`s** (`git-clone`, `buildah`, `s2i-*`, …) it drops into `openshift-pipelines` itself
> for every project to reuse. Give it a couple of minutes — `tekton-results` comes up last.

---

## Step 1 — Confirm Pipelines is available

```bash
oc get csv -A | grep -i pipelines            # Operator Succeeded
tkn version -n openshift-pipelines           # Tekton CLI + server versions
oc get task -n openshift-pipelines           # the shared Tasks every project can reference
```

**Verified output** *(live cluster, OCP 4.18, run 2026-07-14):*

```
openshift-pipelines-operator-rh.v1.22.4   Red Hat OpenShift Pipelines   1.22.4   Succeeded
Client version: 0.45.0
Pipeline version: v1.9.3
Triggers version: v0.35.0
NAME                        AGE
buildah                     5m
git-clone                   5m
s2i-java                    5m
...                          (git-cli, maven, kn, openshift-client, skopeo-copy, etc.)
```

> **Narrate:** Unlike older Pipelines releases, there is **no `ClusterTask` CRD anymore** —
> `git-clone`/`buildah`/etc. are plain namespaced `Task`s living in `openshift-pipelines`.
> To reference one from *your* project's Pipeline, you need the **cluster resolver**
> (Step 3) — a bare `taskRef: { name: git-clone }` only looks in your own namespace and
> won't find them.

---

## Step 2 — Two things Tekton Hub doesn't ship: `run-tests` and `git-update-deployment`

> `git-clone` and `buildah` are real, operator-shipped Tasks. **`run-tests` and
> `git-update-deployment` are not** — no catalog ships tasks under those names, because
> "run our tests" and "bump our deploy repo" are project-specific. Author them once per
> project, alongside the source (or, as here, straight into the pipeline's namespace):

```bash
oc create namespace mod10-demos

oc apply -f - <<'EOF'
apiVersion: tekton.dev/v1
kind: Task
metadata: { name: run-tests, namespace: mod10-demos }
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
metadata: { name: git-update-deployment, namespace: mod10-demos }
spec:
  params:
    - { name: repo-url, type: string }
    - { name: tag, type: string }
  workspaces:
    - name: gitops       # scratch clone of the deploy repo
    - name: gitcreds     # basic-auth Secret: username + a Git push token
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
```

**Verified output** *(live cluster, OCP 4.18, run 2026-07-14):*

```
namespace/mod10-demos created
task.tekton.dev/run-tests created
task.tekton.dev/git-update-deployment created
```

> **Narrate:** `run-tests` just runs the repo's own `tests/test.sh` against the cloned
> source. `git-update-deployment` clones the **deploy** repo (a second, separate clone —
> not the source workspace), edits `overlays/prod/kustomization.yaml`'s `images:` tag, and
> pushes. This is the literal hand-off point from CI to GitOps.

---

## Step 3 — Git push credentials for the GitOps hand-off

> The `update-gitops` task needs a token that can push to `subscriber-api-gitops`. Use a
> **scoped token** (fine-grained PAT limited to that one repo, or a classic PAT with just
> `repo` scope) — never a personal all-repo credential — and keep the expiry short.
>
> ⚠️ **Real finding from validating this demo:** a **fine-grained** PAT scoped to an
> *organization* repo can come back `403 Permission ... denied` even when it looks
> correctly scoped, if the org hasn't enabled fine-grained PAT access (Org Settings →
> Third-party Access → Personal access tokens) or the token needs owner approval. A
> **classic** PAT with `repo` scope sidesteps this entirely and is the more reliable choice
> for an org-owned deploy repo.

```bash
oc create secret generic github-push-creds \
  --namespace mod10-demos \
  --type=kubernetes.io/basic-auth \
  --from-literal=username=x-access-token \
  --from-literal=password='<your-git-push-token>'
```

**Verified output** *(live cluster, OCP 4.18, run 2026-07-14 — value redacted):*

```
secret/github-push-creds created
```

---

## Step 4 — The full pipeline (Tekton)

```bash
oc apply -f - <<'EOF'
apiVersion: tekton.dev/v1
kind: Pipeline
metadata: { name: subscriber-api-ci, namespace: mod10-demos }
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
    - name: fetch                          # git-clone, via cluster resolver (Step 1)
      taskRef:
        resolver: cluster
        params:
          - { name: kind, value: task }
          - { name: name, value: git-clone }
          - { name: namespace, value: openshift-pipelines }
      params: [ { name: URL, value: "$(params.git-url)" } ]   # NB: uppercase URL, not "url"
      workspaces: [ { name: output, workspace: source } ]
    - name: unit-test
      runAfter: [fetch]
      taskRef: { name: run-tests }
      workspaces: [ { name: source, workspace: source } ]
    - name: build-image                    # buildah — rootless, daemonless (Module 1)
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
    - name: update-gitops                  # bump the image tag in the deploy repo, commit/push
      runAfter: [build-image]
      taskRef: { name: git-update-deployment }
      params:
        - { name: repo-url, value: "$(params.gitops-repo-url)" }
        - { name: tag, value: "$(params.tag)" }
      workspaces:
        - { name: gitops, workspace: gitops }
        - { name: gitcreds, workspace: gitcreds }
EOF
```

**Verified output** *(live cluster, OCP 4.18, run 2026-07-14):*

```
pipeline.tekton.dev/subscriber-api-ci created
```

> **Narrate:** Four tasks: **clone → test → build image (Buildah) → update the GitOps
> repo**. The last task is the hand-off — it commits a new tag; it does **not** deploy.
> Note the `resolver: cluster` blocks on `fetch`/`build-image` — that's how a Pipeline in
> `mod10-demos` reaches Tasks that live in `openshift-pipelines` (Step 1's finding).

---

## Step 5 — Run it and watch each step

```bash
tkn pipeline start subscriber-api-ci -n mod10-demos \
  -p git-url=https://github.com/MIT-TRAINING/subscriber-api-ci.git \
  -p image-repo=image-registry.openshift-image-registry.svc:5000/mod10-demos/subscriber-api \
  -p tag=v2 \
  -p gitops-repo-url=https://github.com/MIT-TRAINING/subscriber-api-gitops.git \
  -w name=source,volumeClaimTemplateFile=source-pvc.yaml \
  -w name=gitops,volumeClaimTemplateFile=gitops-pvc.yaml \
  -w name=gitcreds,secret=github-push-creds

tkn pipelinerun logs --last -n mod10-demos
```

*(`source-pvc.yaml` / `gitops-pvc.yaml` are each a minimal `spec: {accessModes: ["ReadWriteOnce"], resources: {requests: {storage: 100Mi}}}` — any small RWO PVC template works.)*

**Verified output** *(live cluster, OCP 4.18, run 2026-07-14 — trimmed):*

```
PipelineRun started: subscriber-api-ci-run-tp84x

[fetch : prepare-and-run] Successfully cloned https://github.com/MIT-TRAINING/subscriber-api-ci.git ...
[unit-test : run-tests] unit tests passed
[build-image : build] STEP 1/3: FROM registry.access.redhat.com/ubi9/httpd-24:latest
[build-image : build] STEP 2/3: COPY html/ /var/www/html/
[build-image : build] STEP 3/3: EXPOSE 8080
[build-image : build] Successfully tagged image-registry.openshift-image-registry.svc:5000/mod10-demos/subscriber-api:v2
[update-gitops : update-and-push] Cloning into 'repo'...
[update-gitops : update-and-push] [main 559c089] ci: bump subscriber-api image tag to v2
[update-gitops : update-and-push] To https://github.com/MIT-TRAINING/subscriber-api-gitops.git
[update-gitops : update-and-push]    3856150..559c089  main -> main

NAME                         SUCCEEDED   REASON
subscriber-api-ci-run-tp84x   True        Succeeded
```

> **Narrate:** Each task ran in **its own pod** (serverless). The final task pushed a real
> commit to the **deploy repo** (`3856150..559c089`) — CI is done; it never touched the
> cluster's Deployment. `image-registry...svc:5000/...` push worked with **no extra
> registry secret** — the namespace's default `pipeline` ServiceAccount already carries
> `system:image-builder` for its own namespace's imagestreams.

---

## Step 6 — CD takes over (Argo CD)

> Same `argocd.argoproj.io/managed-by` finding as Demo 1: the destination namespace needs
> that label before Argo can create objects in it. There's a **second** finding here that
> Demo 1 didn't hit: the built image lives in **`mod10-demos`**'s imagestream, but the
> Deployment runs in **`subscriber-api-prod`** — a different namespace's default
> ServiceAccount can't pull it without an explicit `system:image-puller` grant in the
> *producing* namespace.

```bash
oc create namespace subscriber-api-prod
oc label namespace subscriber-api-prod argocd.argoproj.io/managed-by=openshift-gitops
oc policy add-role-to-user system:image-puller \
  system:serviceaccount:subscriber-api-prod:default -n mod10-demos

oc apply -f - <<'EOF'
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata: { name: subscriber-api, namespace: openshift-gitops }
spec:
  project: default
  source:
    repoURL: https://github.com/MIT-TRAINING/subscriber-api-gitops.git
    targetRevision: main
    path: overlays/prod
  destination: { server: https://kubernetes.default.svc, namespace: subscriber-api-prod }
  syncPolicy: { automated: { prune: true, selfHeal: true } }
EOF

oc get application subscriber-api -n openshift-gitops -o jsonpath='{.status.sync.status}{" / "}{.status.health.status}{"\n"}'
oc get deploy subscriber-api -n subscriber-api-prod \
  -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
```

**Verified output** *(live cluster, OCP 4.18, run 2026-07-14):*

```
namespace/subscriber-api-prod created
namespace/subscriber-api-prod labeled
clusterrole.rbac.authorization.k8s.io/system:image-puller added
application.argoproj.io/subscriber-api created
Synced / Healthy
image-registry.openshift-image-registry.svc:5000/mod10-demos/subscriber-api:v2
```

```bash
# Confirmed live: 6/6 pods Running, serving the content baked into the CI image
oc exec -n subscriber-api-prod deploy/subscriber-api -- curl -s http://localhost:8080/
```
```
  "msisdn": "9665XXXXXXXX",
  "plan": "Mobily Postpaid Gold",
```

> **Narrate:** Argo CD saw the deploy-repo commit and rolled the Deployment to **:v2** — the
> exact Module-9/Demo-1 GitOps loop, triggered by CI. Without the `image-puller` grant, the
> Deployment goes `Progressing` forever with pods stuck `ImagePullBackOff` — worth showing
> once so learners recognize the symptom. Rollback = revert that commit.

---

## Step 7 — Jenkins equivalent (discuss)

```groovy
// Jenkinsfile (same idea, server-based)
pipeline {
  stages {
    stage('Build & Test') { steps { sh 'sh tests/test.sh' } }
    stage('Image')        { steps { sh 'buildah bud -t $IMAGE -f Containerfile . && buildah push $IMAGE' } }
    stage('Update GitOps'){ steps { sh 'sed -i "s/newTag: .*/newTag: v2/" overlays/prod/kustomization.yaml && git commit -am v2 && git push' } }
  }
}
```

> **Narrate:** Jenkins does the same four things from a Jenkinsfile. Whichever engine, the
> **hand-off to GitOps** (commit to the deploy repo) is identical — so the CD half is
> unchanged.

---

## Step 8 — Cleanup

```bash
oc delete application subscriber-api -n openshift-gitops   # prune removes the Deployment
oc delete namespace subscriber-api-prod
oc delete namespace mod10-demos                            # pipeline, tasks, PVCs, secret
```

**Verified output** *(live cluster, OCP 4.18, run 2026-07-14):*

```
application.argoproj.io "subscriber-api" deleted
namespace "subscriber-api-prod" deleted
namespace "mod10-demos" deleted
```

---

## Wrap-up questions to pose

1. What is the output of the CI pipeline, and what does its last step do?
2. Why doesn't the pipeline run `oc apply` to deploy?
3. How is Tekton different from Jenkins architecturally?
4. Where does CD (GitOps) pick up, and how would you roll back?
5. Why did the built image need an explicit `system:image-puller` grant to be deployed in a
   *different* namespace from where it was built?

---

> **✓ Fully verified — Steps 0-8 all run live, end-to-end, on 2026-07-14.**
> The OpenShift Pipelines Operator (v1.22.4) was installed live; the full pipeline
> (`fetch` → `unit-test` → `build-image` → `update-gitops`) ran against the real
> [`subscriber-api-ci`](https://github.com/MIT-TRAINING/subscriber-api-ci) source repo,
> genuinely built and pushed an image to the internal registry, and genuinely committed +
> pushed a tag bump to
> [`subscriber-api-gitops`](https://github.com/MIT-TRAINING/subscriber-api-gitops); Argo CD
> then picked up that real commit and rolled out `:v2` to 6/6 Healthy pods, confirmed by
> `curl`-ing the actual served content. All output above is real, not representative.
>
> Three real findings surfaced during validation that the original (never-run) version of
> this demo would not have survived on a fresh namespace:
> 1. **`ClusterTask` is gone** in current OpenShift Pipelines — `git-clone`/`buildah` are
>    namespaced `Task`s in `openshift-pipelines`, reached via `resolver: cluster`, not a
>    bare `taskRef: { name: ... }`.
> 2. **`git-clone`'s params are uppercase** (`URL`, not `url`) on the operator-shipped Task.
> 3. **Cross-namespace internal-registry pulls need an explicit `system:image-puller`
>    RoleBinding** in the namespace that built the image, granted to the consuming
>    namespace's ServiceAccount — on top of Demo 1's `argocd.argoproj.io/managed-by`
>    namespace label.
>
> One environment-specific note, not a demo bug: this shared training cluster's 3 workers
> were near their CPU-request ceiling from other course namespaces, which blocked Tekton's
> task pods from scheduling until the cluster was scaled to 5 workers. Check
> `oc describe nodes` for `Insufficient cpu` if `PipelineRun`s hang `Pending` on a busy
> shared cluster.
>
> The cluster and both repos were left clean afterward (test `Application`, namespaces, and
> the tag-bump commit reverted; the Git push token was deleted from the cluster secret).
