# Exercise 2 — CI Pipeline → GitOps

> **Scenario:** Automate delivery of **subscriber-api**: a Tekton **Pipeline** builds and
> tests, builds an image with Buildah, pushes it, and **updates the GitOps repo** — then
> Argo CD deploys. You'll build the pipeline, run it, and confirm the CI/CD hand-off.

| | |
|---|---|
| **Practice** | Tekton Pipeline/Task, `tkn pipeline start`, Buildah build, update GitOps repo, verify Argo deploy |
| **Maps to** | Guide §5, §6, §7 · Visualization 02 · Demo 2 |
| **Difficulty** | ⭐⭐ Intermediate · ~25 min · needs Pipelines + GitOps Operators (install = admin) |

---

## Tasks

1. Confirm the **OpenShift Pipelines** Operator is installed and `tkn` works.
2. Create a **Pipeline** with tasks: clone → test → **buildah** image → **update GitOps
   repo** (bump tag).
3. **Run** it with `tkn pipeline start` and watch each task pod succeed.
4. Confirm the **image** was pushed and the **GitOps repo** commit was made.
5. Confirm **Argo CD** synced the deploy repo and the Deployment moved to `:v2`.

> **Hint (Task 2):** reuse Tekton Hub tasks (`git-clone`, `buildah`) via `taskRef`.

> **Hint (Task 3):** `tkn pipeline start <name> -p git-url=... -p image=... --showlog`.

---

## Validation

```bash
oc get csv -A | grep -i pipelines                 # Operator Succeeded
tkn pipelinerun list -n mod10-ex                   # Succeeded
oc get deploy subscriber-api -n subscriber-api-prod \
  -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'   # ...:v2
```

---

## Reflection

- What is the pipeline's final task, and why isn't it `oc apply`?
- Why does CI never need cluster credentials in this design?
- Where does CD begin, and how would you roll back the deploy?

---

<details>
<summary><strong>✅ Solution</strong> (try the tasks first)</summary>

```bash
# 1. Pipelines present
oc get csv -A | grep -i pipelines ; tkn version

# 2. Pipeline: clone → test → build image → update GitOps repo
oc apply -f - <<'EOF'
apiVersion: tekton.dev/v1
kind: Pipeline
metadata: { name: subscriber-api-ci, namespace: mod10-ex }
spec:
  params:
    - { name: git-url, type: string }
    - { name: image, type: string }
  tasks:
    - { name: fetch,     taskRef: { name: git-clone }, params: [ { name: url, value: "$(params.git-url)" } ] }
    - { name: test,      runAfter: [fetch],  taskRef: { name: run-tests } }
    - { name: build,     runAfter: [test],   taskRef: { name: buildah }, params: [ { name: IMAGE, value: "$(params.image)" } ] }
    - { name: gitops,    runAfter: [build],  taskRef: { name: git-update-deployment } }
EOF

# 3. Run
tkn pipeline start subscriber-api-ci -n mod10-ex \
  -p git-url=https://git.mobily.example/subscriber-api.git \
  -p image=image-registry.openshift-image-registry.svc:5000/mod10-ex/subscriber-api:v2 \
  --showlog

# 4-5. Verify
tkn pipelinerun list -n mod10-ex
oc get application subscriber-api -n openshift-gitops -o jsonpath='{.status.sync.status}{"\n"}'
oc get deploy subscriber-api -n subscriber-api-prod \
  -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'

# Cleanup
oc delete pipeline subscriber-api-ci -n mod10-ex ; oc delete pipelinerun --all -n mod10-ex
```

**Representative output** *(requires a cluster + Operators — OCP 4.18):*

```
openshift-pipelines-operator-rh.v1.x.y   ... Succeeded
NAME                          STATUS
subscriber-api-ci-run-abcde   Succeeded
Synced
image-registry.openshift-image-registry.svc:5000/mod10-ex/subscriber-api:v2
```

**Key point:** CI ends by **committing a new image tag to the GitOps repo** — not by
deploying. Argo CD picks up the commit and rolls to `:v2`. The pipeline holds **no cluster
credentials**; rollback is reverting the deploy-repo commit.
</details>

---

> **◐ Partially verified:** `tkn`/`oc` syntax follows Pipelines 1.x / oc 4.22; all steps
> **require a live cluster with the Pipelines + GitOps Operators** and were not run at
> authoring (cluster asleep). Output is **representative of OpenShift 4.18** (task names vary
> by your Tekton Hub set). Validate live when the cluster is up (Operator install as admin;
> PipelineRun as a project user).
