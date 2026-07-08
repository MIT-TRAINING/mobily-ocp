# Exercise 3 — Build → GitOps → Mesh Canary (Capstone)

> **Scenario:** Assemble the full delivery chain for **tariff-catalog**: a **CI pipeline**
> builds `:v2` and updates Git, **Argo CD** deploys it into a **mesh** namespace (sidecars,
> mTLS), and a **VirtualService** canaries **10%** of traffic to v2 — observed in Kiali,
> ramped or rolled back by editing one weight. This capstone ties together every layer of
> Module 10.

| | |
|---|---|
| **Practice** | pipeline → GitOps → Argo sync · sidecar injection (2/2) · PeerAuthentication mTLS · VirtualService/DestinationRule canary · rollback |
| **Maps to** | Guide §7, §9, §10, §11 · Visualizations 01–03 · Demos 1–3 |
| **Difficulty** | ⭐⭐⭐ Advanced (capstone) · ~35–40 min · needs GitOps + Pipelines + Service Mesh Operators |

> ⚠️ Needs all three Operators installed (admin) and the namespace joined to the mesh. Do
> the pipeline/Application/canary CRs as a project user once the platform is ready.

---

## Tasks

1. **CI:** run the Module-10 pipeline to build `tariff-catalog:v2` and commit the tag to the
   GitOps repo.
2. **CD:** confirm the Argo CD **Application** syncs the deploy repo (v1 + v2 subsets
   present).
3. **Mesh:** confirm the namespace is a mesh member and both versions' pods are **2/2**
   (sidecars). Require **STRICT mTLS**.
4. **Canary:** apply a **DestinationRule** (v1/v2 subsets) + **VirtualService** (90/10) and
   send traffic; confirm ~10% hits v2.
5. **Ramp / rollback:** change the weight to 100% v2 (promote) — or 0% v2 (roll back) — and
   confirm. Note where you'd watch the error rate.

> **Hint (Task 3):** `oc get pods -n tariff-prod` → look for `2/2 READY`.

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

---

<details>
<summary><strong>✅ Solution</strong> (try the tasks first — needs all three Operators)</summary>

```bash
# 1. CI → image + GitOps commit (see Exercise 2)
tkn pipeline start tariff-catalog-ci -n mod10-ex \
  -p git-url=https://git.mobily.example/tariff-catalog.git \
  -p image=image-registry.openshift-image-registry.svc:5000/mod10-ex/tariff-catalog:v2 --showlog

# 2. CD — Argo syncs the deploy repo (v1 + v2)
oc get application tariff-catalog -n openshift-gitops        # Synced / Healthy

# 3. Mesh membership + injection + mTLS
oc get smmr default -n istio-system -o jsonpath='{.spec.members}{"\n"}'   # includes tariff-prod
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
for i in $(seq 1 50); do oc exec deploy/loadgen -n tariff-prod -- curl -s tariff-catalog/ >/dev/null; done
# watch the split in Kiali:
oc get route -n istio-system kiali -o jsonpath='{.spec.host}{"\n"}'

# 5. Promote (100% v2) or roll back (0% v2) — edit the two weights:
oc patch virtualservice tariff-catalog -n tariff-prod --type=json \
  -p='[{"op":"replace","path":"/spec/http/0/route/0/weight","value":0},
       {"op":"replace","path":"/spec/http/0/route/1/weight","value":100}]'   # promote v2

# Cleanup
oc delete virtualservice,destinationrule tariff-catalog -n tariff-prod
oc delete peerauthentication default -n tariff-prod
```

**Representative output** *(requires a cluster + 3 Operators — OCP 4.18 / OSSM 2.x):*

```
Synced
tariff-catalog-v1-...   2/2   Running
tariff-catalog-v2-...   2/2   Running
["tariff-prod"]
90 10
# Kiali graph shows ~90% v1 / ~10% v2 with per-version error rates
```

**Key point (the whole module):** `git push` → **CI** builds `:v2` → commit to GitOps repo
→ **Argo CD** deploys into a **mesh** namespace → **sidecars** (2/2) + **mTLS** secure it →
a **VirtualService** canaries 10% to v2 → **Kiali** observes it. Two rollbacks: revert the
GitOps commit (redeploy old image) **or** set the canary weight to 0% (instant traffic
cutover) — no code change either way.
</details>

---

> **◐ Partially verified:** CR schemas follow Argo/Tekton/OSSM references; every step
> **requires a live cluster with the GitOps + Pipelines + Service Mesh Operators** and was
> not run at authoring (cluster asleep). Output is **representative of OpenShift 4.18 /
> OSSM 2.x** (API versions vary by release). Validate live when the cluster is up
> (platform install as admin; the app/canary CRs as a project user).
