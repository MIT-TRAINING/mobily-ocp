# Demo 2 — CI Pipeline → GitOps

> **Scenario:** Automate delivery of the Mobily **subscriber-api**: a **pipeline** (Tekton;
> Jenkins equivalent noted) checks out the code, **builds and tests** it, builds a container
> **image** with Buildah, pushes it, and **updates the GitOps repo** — then **Argo CD**
> deploys. CI and CD stay cleanly separated.

| | |
|---|---|
| **Concepts reinforced** | Pipeline/Task (Tekton) · Buildah/S2I build · push image · update GitOps repo · Argo CD deploys · CI vs CD boundary |
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
  creds**.

---

## Step 1 — Confirm Pipelines is available

```bash
oc get csv -A | grep -i pipelines            # OpenShift Pipelines Operator Succeeded
tkn version                                   # Tekton CLI (client)
```

**Expected output** *(requires a cluster — representative):*

```
openshift-pipelines-operator-rh.v1.x.y   Red Hat OpenShift Pipelines   1.x.y   Succeeded
Client version: 0.x.y
Pipeline version: v1.x.y
```

> **Narrate:** The Operator installs Tekton cluster-wide and gives us the `tkn` CLI and the
> Pipeline/Task CRDs.

---

## Step 2 — A minimal build→push→update-Git pipeline (Tekton)

```bash
oc apply -f - <<'EOF'
apiVersion: tekton.dev/v1
kind: Pipeline
metadata: { name: subscriber-api-ci, namespace: mod10-demos }
spec:
  params:
    - { name: git-url, type: string }
    - { name: image, type: string }
  tasks:
    - name: fetch     # git-clone (from Tekton Hub)
      taskRef: { name: git-clone }
      params: [ { name: url, value: "$(params.git-url)" } ]
    - name: unit-test
      runAfter: [fetch]
      taskRef: { name: run-tests }
    - name: build-image     # buildah — rootless, daemonless (Module 1)
      runAfter: [unit-test]
      taskRef: { name: buildah }
      params: [ { name: IMAGE, value: "$(params.image)" } ]
    - name: update-gitops   # bump the image tag in the deploy repo, commit/PR
      runAfter: [build-image]
      taskRef: { name: git-update-deployment }
EOF
```

**Expected output** *(requires a cluster — representative):*

```
pipeline.tekton.dev/subscriber-api-ci created
```

> **Narrate:** Four tasks: **clone → test → build image (Buildah) → update the GitOps
> repo**. The last task is the hand-off — it commits a new tag; it does **not** deploy.

---

## Step 3 — Run it and watch each step

```bash
tkn pipeline start subscriber-api-ci \
  -p git-url=https://git.mobily.example/subscriber-api.git \
  -p image=image-registry.openshift-image-registry.svc:5000/mod10-demos/subscriber-api:v2 \
  --showlog
tkn pipelinerun list -n mod10-demos
```

**Expected output** *(requires a cluster — representative):*

```
PipelineRun started: subscriber-api-ci-run-abcde
[fetch]       cloning https://git.mobily.example/subscriber-api.git ...
[unit-test]   ok  12 tests passed
[build-image] STEP-BUILD ... Successfully pushed ...subscriber-api:v2
[update-gitops] committed image tag v2 to deploy repo
NAME                           STATUS      ...
subscriber-api-ci-run-abcde    Succeeded
```

> **Narrate:** Each task ran in **its own pod** (serverless). The final task pushed a commit
> to the **deploy repo** — CI is done; it never touched the cluster's Deployment.

---

## Step 4 — CD takes over (Argo CD)

```bash
oc get application subscriber-api -n openshift-gitops -o jsonpath='{.status.sync.status}{"\n"}'
oc get deploy subscriber-api -n subscriber-api-prod \
  -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
```

**Expected output** *(requires a cluster — representative):*

```
Synced
image-registry.openshift-image-registry.svc:5000/mod10-demos/subscriber-api:v2
```

> **Narrate:** Argo CD saw the deploy-repo commit and rolled the Deployment to **:v2** — the
> exact Module-9 GitOps loop, triggered by CI. Rollback = revert that commit.

---

## Step 5 — Jenkins equivalent (discuss)

```groovy
// Jenkinsfile (same idea, server-based)
pipeline {
  stages {
    stage('Build & Test') { steps { sh 'make test' } }
    stage('Image')        { steps { sh 'buildah bud -t $IMAGE . && buildah push $IMAGE' } }
    stage('Update GitOps'){ steps { sh 'yq -i ".image.tag=\"v2\"" deploy/values.yaml && git commit -am v2 && git push' } }
  }
}
```

> **Narrate:** Jenkins does the same four things from a Jenkinsfile. Whichever engine, the
> **hand-off to GitOps** (commit to the deploy repo) is identical — so the CD half is
> unchanged.

---

## Step 6 — Cleanup

```bash
oc delete pipeline subscriber-api-ci -n mod10-demos
oc delete pipelinerun --all -n mod10-demos
```

**Expected output** *(representative):*

```
pipeline.tekton.dev "subscriber-api-ci" deleted
```

---

## Wrap-up questions to pose

1. What is the output of the CI pipeline, and what does its last step do?
2. Why doesn't the pipeline run `oc apply` to deploy?
3. How is Tekton different from Jenkins architecturally?
4. Where does CD (GitOps) pick up, and how would you roll back?

---

> **◐ Partially verified:** `tkn`/`oc` **syntax** follows the Pipelines 1.x / oc 4.22
> reference, but every step **requires a live OpenShift cluster with the Pipelines + GitOps
> Operators** and was not run at authoring (cluster asleep). Output is **representative of
> OpenShift 4.18**; task/pipeline names vary by your Tekton Hub tasks. Validate live when
> the cluster is up (Operator install as admin; PipelineRun as a project user).
