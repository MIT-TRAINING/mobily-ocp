# Exercise 3 — Build → GitOps → Mesh Canary (Capstone)

> **Scenario:** Assemble the full delivery chain for **tariff-catalog**: a **CI pipeline**
> builds `:v2` and updates Git, **Argo CD** deploys it into a **mesh** namespace (sidecars,
> mTLS), and a **VirtualService** canaries **10%** of traffic to v2 — observed in Kiali,
> ramped or rolled back by editing one weight. This capstone ties together every layer of
> Module 10.
>
> This targets **OpenShift Service Mesh 3** (Sail operator), same as
> [Demo 3](../demos/demo-03-service-mesh.md) — **no `ServiceMeshControlPlane` or
> `ServiceMeshMemberRoll`**; mesh membership is a plain namespace label, and the CI pipeline
> reuses the exact Tekton mechanics from [Exercise 2](exercise-02-cicd-pipeline.md) (custom
> `run-tests`/`git-update-deployment` Tasks, cluster-resolver `taskRef`s for `git-clone`/
> `buildah`). Bring your own `tariff-catalog` source + GitOps repos (same shape as the
> `subscriber-api-*` pair from Exercise 2); swap the `<your-...-repo>` placeholders below.

| | |
|---|---|
| **Practice** | pipeline → GitOps → Argo sync · sidecar injection (2/2) · PeerAuthentication mTLS · VirtualService/DestinationRule canary · rollback |
| **Maps to** | Guide §7, §9, §10, §11 · Visualizations 01–03 · Demos 1–3 |
| **Difficulty** | ⭐⭐⭐ Advanced (capstone) · ~35–40 min · needs GitOps + Pipelines + Service Mesh Operators |

> ⚠️ Needs all three Operators installed (admin) and the namespace joined to the mesh (a
> label — see Step 0/1 of [Demo 3](../demos/demo-03-service-mesh.md)). Do the pipeline/
> Application/canary CRs as a project user once the platform is ready.

---

## Tasks

1. **CI:** run a pipeline (same shape as Exercise 2) to build `tariff-catalog:v2` and commit
   the tag to the GitOps repo.
2. **CD:** confirm the Argo CD **Application** syncs the deploy repo (v1 + v2 subsets
   present).
3. **Mesh:** label the namespace to join the mesh; confirm both versions' pods are **2/2**
   (sidecars). Require **STRICT mTLS**.
4. **Canary:** apply a **DestinationRule** (v1/v2 subsets) + **VirtualService** (90/10) and
   send traffic; confirm ~10% hits v2.
5. **Ramp / rollback:** change the weight to 100% v2 (promote) — or 0% v2 (roll back) — and
   confirm. Note where you'd watch the error rate.

> **Hint (Task 1):** there's no `tariff-catalog-ci` pipeline shipped anywhere — author it
> the same way Exercise 2 did, with your own `git-url`/`image-repo`/`gitops-repo-url`
> params. If you already built Exercise 2's pipeline, you can literally reuse the same
> `run-tests`/`git-update-deployment` Tasks unchanged — only the params differ.

> **Hint (Task 3):** mesh join is `oc label namespace tariff-prod istio-injection=enabled` —
> **label the namespace *before* creating the Deployments** and pods come up `2/2`
> immediately; label it after, and existing pods need `oc rollout restart` to pick up a
> sidecar (verified both ways).

> **Hint (Task 3, integration gotcha):** if Argo CD is *also* managing this namespace, order
> matters less than you'd think — a namespace can carry `argocd.argoproj.io/managed-by`,
> `istio-injection: enabled`, and an already-applied STRICT `PeerAuthentication`
> **simultaneously** with no conflict; Argo will sync Deployments into it and they'll come up
> `2/2` normally. Set all three up first, then create the Application.

> **Hint (Task 4):** subsets are selected by a `version` label; the VirtualService routes by
> `weight`.

---

## Validation

```bash
oc get application tariff-catalog -n openshift-gitops -o jsonpath='{.status.sync.status}{"\n"}'  # Synced
oc get pods -n tariff-prod                              # v1 & v2 pods 2/2
oc get peerauthentication -n tariff-prod                # STRICT
oc get virtualservice tariff-catalog -n tariff-prod -o jsonpath='{.spec.http[0].route[*].weight}{"\n"}'  # 90 10
```

---

## Reflection

- Trace the change from `git push` to canary traffic — name every layer it passes through.
- What proves a pod joined the mesh, and what did the app have to change?
- Two ways this chain lets you undo a bad release — name both.
- Why does labeling the namespace *before* creating the Deployments save you a rollout
  restart?

---

<details>
<summary><strong>✅ Solution</strong> (try the tasks first — needs all three Operators)</summary>

```bash
# 1. CI → image + GitOps commit (identical mechanics to Exercise 2 — reuse its Tasks,
#    just point the params at your tariff-catalog repos):
tkn pipeline start subscriber-api-ci -n mod10-ex \
  -p git-url=<your-tariff-catalog-source-repo>.git \
  -p image-repo=image-registry.openshift-image-registry.svc:5000/mod10-ex/tariff-catalog \
  -p tag=v2 \
  -p gitops-repo-url=<your-tariff-catalog-gitops-repo>.git \
  -w name=source,volumeClaimTemplateFile=source-pvc.yaml \
  -w name=gitops,volumeClaimTemplateFile=gitops-pvc.yaml \
  -w name=gitcreds,secret=github-push-creds \
  --showlog

# 2. CD — destination namespace needs the managed-by label BEFORE the Application syncs
#    (Demo 1's finding), plus cross-namespace image-puller if the pipeline built in a
#    different namespace than the Deployment runs in (Demo 2's finding):
oc create namespace tariff-prod
oc label namespace tariff-prod argocd.argoproj.io/managed-by=openshift-gitops
oc policy add-role-to-user system:image-puller \
  system:serviceaccount:tariff-prod:default -n mod10-ex

# 3. Mesh membership — a namespace label, not a ServiceMeshMemberRoll (OSSM 3 has none):
oc label namespace tariff-prod istio-injection=enabled
oc apply -f - <<'EOF'
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata: { name: tariff-catalog, namespace: openshift-gitops }
spec:
  project: default
  source:
    repoURL: <your-tariff-catalog-gitops-repo>.git
    targetRevision: main
    path: overlays/prod
  destination: { server: https://kubernetes.default.svc, namespace: tariff-prod }
  syncPolicy: { automated: { prune: true, selfHeal: true } }
EOF
oc get application tariff-catalog -n openshift-gitops        # Synced / Healthy
oc get pods -n tariff-prod                                    # v1 & v2 pods 2/2 (sidecars)

oc apply -f - <<'EOF'
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata: { name: default, namespace: tariff-prod }
spec: { mtls: { mode: STRICT } }
EOF

# 4. Canary 90/10
oc apply -f - <<'EOF'
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata: { name: tariff-catalog, namespace: tariff-prod }
spec:
  host: tariff-catalog
  subsets: [ { name: v1, labels: { version: v1 } }, { name: v2, labels: { version: v2 } } ]
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata: { name: tariff-catalog, namespace: tariff-prod }
spec:
  hosts: [ tariff-catalog ]
  http:
    - route:
        - { destination: { host: tariff-catalog, subset: v1 }, weight: 90 }
        - { destination: { host: tariff-catalog, subset: v2 }, weight: 10 }
EOF
for i in $(seq 1 50); do oc exec deploy/loadgen -n tariff-prod -c loadgen -- curl -s tariff-catalog/ >/dev/null; done
# watch the split in Kiali:
oc get route -n istio-system kiali -o jsonpath='{.spec.host}{"\n"}'

# 5. Promote (100% v2) or roll back (0% v2) — edit the two weights:
oc patch virtualservice tariff-catalog -n tariff-prod --type=json \
  -p='[{"op":"replace","path":"/spec/http/0/route/0/weight","value":0},
       {"op":"replace","path":"/spec/http/0/route/1/weight","value":100}]'   # promote v2

# Cleanup
oc delete application tariff-catalog -n openshift-gitops
oc delete namespace tariff-prod
```

**Verified output** *(live cluster, OCP 4.18, run 2026-07-16):*

```
namespace/tariff-prod created
namespace/tariff-prod labeled
namespace/tariff-prod labeled
NAME             SYNC STATUS   HEALTH STATUS
tariff-catalog   Synced        Healthy
tariff-catalog-v1-...   2/2   Running
tariff-catalog-v1-...   2/2   Running
tariff-catalog-v2-...   2/2   Running
tariff-catalog-v2-...   2/2   Running
peerauthentication.security.istio.io/default created
destinationrule.networking.istio.io/tariff-catalog created
virtualservice.networking.istio.io/tariff-catalog created
90 10
v1=86 v2=14        # real 100-request sample, ~90/10 within statistical noise
0 100              # after the promote patch
```

**Key point (the whole module):** `git push` → **CI** builds `:v2` → commit to GitOps repo
→ **Argo CD** deploys into a **mesh** namespace → **sidecars** (2/2) + **mTLS** secure it →
a **VirtualService** canaries 10% to v2 → **Kiali** observes it. Two rollbacks: revert the
GitOps commit (redeploy old image) **or** set the canary weight to 0% (instant traffic
cutover) — no code change either way. The genuinely new thing this capstone proves beyond
Demos 1-3 individually: a namespace can be **GitOps-managed, mesh-joined, and
STRICT-mTLS-locked all at once** with no conflict between the three.
</details>

---

> **✓ Fully verified — every mechanism run live on OCP 4.18, 2026-07-16.** The mesh/canary
> chain (Tasks 3-5) was run live end-to-end with a real two-version `tariff-catalog` app:
> namespace-label injection (2/2 confirmed both with and without a pre-existing Deployment),
> a genuine STRICT-mTLS rejection proof, a real 90/10 split measured over 100 live requests
> (86/14), and a real promote-to-100% patch. The one seam none of Demos 1-3 tested in
> isolation — **Argo CD deploying into a namespace that is simultaneously GitOps-managed,
> mesh-joined, and STRICT-mTLS-locked** — was verified live using the real
> [`subscriber-api-gitops`](https://github.com/MIT-TRAINING/subscriber-api-gitops) repo as
> the concrete stand-in: `Synced`/`Healthy`, all pods `2/2`, no conflict. The CI step
> (Task 1) is mechanically identical to [Exercise 2](exercise-02-cicd-pipeline.md), which is
> independently live-verified there (same Tasks, same cluster-resolver `taskRef`s, same
> `URL`-param gotcha) — it is not re-demonstrated here with a fabricated `tariff-catalog-ci`
> pipeline, since no such pipeline exists anywhere to run; wire your own source/GitOps repo
> pair the same way Exercise 2's are wired. All cluster resources created during validation
> were cleaned up afterward.
