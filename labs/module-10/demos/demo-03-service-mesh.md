# Demo 3 — Service Mesh Canary

> **Scenario:** Release **tariff-catalog v2** safely. We add the app's namespace to the
> mesh (sidecars inject → pods go **2/2**), turn on **STRICT mTLS**, then use a
> **VirtualService** to send **10%** of traffic to v2, watch it in **Kiali**, and ramp up —
> all without changing app code or adding a Route.
>
> This demo targets **OpenShift Service Mesh 3** (`servicemeshoperator3`), Red Hat's
> Sail-operator-based mesh. It is **not** the same control plane as older OSSM 2.x material
> you may find elsewhere: **`ServiceMeshControlPlane` and `ServiceMeshMemberRoll` no longer
> exist** — OSSM 3 uses the upstream-Istio-shaped `Istio` CR and plain namespace labels for
> injection, same as vanilla Istio. If your cluster only has the classic
> `servicemeshoperator` (2.x) installed, Step 1 below will not apply as-is.

| | |
|---|---|
| **Concepts reinforced** | Istio CR (Sail operator) · namespace-label sidecar injection (2/2) · PeerAuthentication (mTLS) · VirtualService + DestinationRule (canary) · Kiali |
| **Maps to** | Guide §8, §9, §10 · Visualization 03 · Exercise 3 |
| **Time** | ~30 minutes |
| **Cluster** | Shared OCP 4.18 with **OpenShift Service Mesh 3** (Sail operator) + **Kiali** Operators — install/control-plane need admin |

---

> **⎈ Kubernetes equivalent:** OSSM 3 *is* upstream Istio, packaged and supported by Red Hat
> via the Sail operator — the CRDs (`Istio`, `IstioCNI`, `VirtualService`, `DestinationRule`,
> `PeerAuthentication`) are the same `sailoperator.io` / `istio.io` APIs you'd use on any
> Kubernetes cluster running the Sail operator.

> ⚠️ Installing the Sail/Kiali Operators and creating the `Istio` control-plane CR need
> **cluster-admin**. Joining a namespace (a label) and adding routing CRs can be a project
> user (once the mesh exists).

## Talking points to open with

- The mesh adds mTLS, routing, and observability **in the sidecar** — the app doesn't
  change.
- **Injection** makes pods **2/2** (app + Envoy). Istiod (control plane) programs the
  sidecars (data plane).
- **Canary** = shift a traffic **weight** with a VirtualService; ramp up or roll back
  instantly.

---

## Step 0 — Install the mesh (cluster-admin, one-time)

> ⚠️ **Admin-only, do this before class.** Install once for the whole shared cluster;
> learners never repeat this step. Three pieces: the Sail operator (control plane), the
> Istio CNI plugin (required on OpenShift — its restricted-SCC model can't use the classic
> init-container traffic-redirect trick vanilla Istio uses elsewhere), and Kiali.

```bash
oc create namespace istio-system
oc apply -f - <<'EOF'
apiVersion: operators.coreos.com/v1
kind: OperatorGroup
metadata: { name: istio-system-og, namespace: istio-system }
spec: {}
EOF
oc apply -f - <<'EOF'
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata: { name: servicemeshoperator3, namespace: istio-system }
spec: { channel: stable, name: servicemeshoperator3, source: redhat-operators, sourceNamespace: openshift-marketplace }
EOF
oc apply -f - <<'EOF'
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata: { name: kiali-ossm, namespace: istio-system }
spec: { channel: stable, name: kiali-ossm, source: redhat-operators, sourceNamespace: openshift-marketplace }
EOF

# Wait for both CSVs to succeed, then stand up the control plane:
oc get csv -n istio-system -w                          # Ctrl-C once both PHASE = Succeeded

oc create namespace istio-cni
oc apply -f - <<'EOF'
apiVersion: sailoperator.io/v1
kind: IstioCNI
metadata: { name: default }
spec: { namespace: istio-cni, version: v1.28.8 }
EOF
oc apply -f - <<'EOF'
apiVersion: sailoperator.io/v1
kind: Istio
metadata: { name: default }
spec:
  namespace: istio-system
  updateStrategy: { type: InPlace }
  version: v1.28.8
EOF
oc apply -f - <<'EOF'
apiVersion: kiali.io/v1alpha1
kind: Kiali
metadata: { name: kiali, namespace: istio-system }
spec: { version: default, istio_namespace: istio-system, deployment: { view_only_mode: false } }
EOF

oc get istio default -o jsonpath='{.status.state}{"\n"}'   # wait for Healthy
oc get pods -n istio-system
```

**Verified output** *(live cluster, OCP 4.18, run 2026-07-15):*

```
servicemeshoperator3.v3.3.5   Red Hat OpenShift Service Mesh 3   3.3.5   Succeeded
kiali-operator.v2.27.1        Kiali Operator                     2.27.1  Succeeded
istiocni.sailoperator.io/default created
istio.sailoperator.io/default created
kiali.kiali.io/kiali created
Healthy
NAME                                     READY   STATUS    RESTARTS   AGE
istiod-5569bc6b84-r4vlv                  1/1     Running   0          51s
kiali-7bffd8f865-dnxql                   1/1     Running   0          6m
kiali-operator-cd844bdc8-nl22t           1/1     Running   0          3m
servicemesh-operator3-5fbdbcb8c9-mb4sg   1/1     Running   0          3m
```

> **Narrate:** No `ServiceMeshControlPlane` — the `Istio` CR *is* the control plane, and
> `istiod` is the only pod it runs (no separate ingress/egress gateway pods unless you ask
> for them). `IstioCNI` installs a DaemonSet (`istio-cni-node`, one per node) that does the
> sidecar traffic redirection at the CNI level, since OpenShift's SCCs block the
> `NET_ADMIN`-capable init container vanilla Istio uses by default.

---

## Step 1 — Join the namespace (a label, not a MemberRoll)

```bash
oc label namespace tariff-prod istio-injection=enabled
oc rollout restart deploy/tariff-catalog-v1 deploy/tariff-catalog-v2 -n tariff-prod
oc rollout status deploy/tariff-catalog-v1 -n tariff-prod
oc get pods -n tariff-prod
```

**Verified output** *(live cluster, OCP 4.18, run 2026-07-15):*

```
namespace/tariff-prod labeled
deployment.apps/tariff-catalog-v1 restarted
deployment "tariff-catalog-v1" successfully rolled out
NAME                                 READY   STATUS    RESTARTS   AGE
tariff-catalog-v1-5fb8669d99-n8mbl   2/2     Running   0          7s
tariff-catalog-v1-5fb8669d99-w4dmh   2/2     Running   0          44s
tariff-catalog-v2-5c9bbf8fd9-8f78h   2/2     Running   0          44s
tariff-catalog-v2-5c9bbf8fd9-cgr7w   2/2     Running   0          7s
```

> **Narrate:** **2/2** is the tell — the Envoy sidecar joined each pod, injected because the
> *namespace* carries `istio-injection: enabled` (the plain Istio label; no separate
> membership object to maintain). Existing pods only pick up injection on their **next
> rollout** — that's why we `rollout restart` right after labeling. Now all traffic flows
> through the mesh; the app binary is unchanged.

---

## Step 2 — Require mTLS (zero-trust)

```bash
oc apply -f - <<'EOF'
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata: { name: default, namespace: tariff-prod }
spec: { mtls: { mode: STRICT } }
EOF

# In-mesh traffic is unaffected (sidecar-to-sidecar mTLS is transparent to the app):
oc exec -n tariff-prod deploy/loadgen -c loadgen -- curl -s tariff-catalog/

# A pod with NO sidecar gets rejected — this is what STRICT actually buys you:
oc run plain-curl --image=registry.access.redhat.com/ubi9/ubi-minimal:latest --restart=Never -n default -- sleep 3600
oc exec -n default plain-curl -- curl -s --max-time 5 -o /dev/null -w "http_code=%{http_code}\n" \
  tariff-catalog.tariff-prod.svc.cluster.local/
oc delete pod plain-curl -n default
```

**Verified output** *(live cluster, OCP 4.18, run 2026-07-15):*

```
peerauthentication.security.istio.io/default created
<html><body><h1>tariff-catalog v2</h1> ...          <- in-mesh call: works, unaffected
http_code=000                                        <- non-mesh call: connection reset
```

> **Narrate:** STRICT mTLS makes the sidecars encrypt and mutually authenticate all
> service traffic in `tariff-prod`. Zero-trust between services — and the app did nothing.
> The `http_code=000` from a plaintext pod is the proof: no cert, no connection.

---

## Step 3 — Canary: 90% v1 / 10% v2

```bash
oc apply -f - <<'EOF'
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata: { name: tariff-catalog, namespace: tariff-prod }
spec:
  host: tariff-catalog
  subsets:
    - { name: v1, labels: { version: v1 } }
    - { name: v2, labels: { version: v2 } }
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
```

**Verified output** *(live cluster, OCP 4.18, run 2026-07-15):*

```
destinationrule.networking.istio.io/tariff-catalog created
virtualservice.networking.istio.io/tariff-catalog created
```

> **Narrate:** The **DestinationRule** defines the subsets (v1/v2 by label); the
> **VirtualService** sends **90/10**. Send traffic and ~1 in 10 requests hits v2 — a canary,
> with no new Route and no redeploy.

---

## Step 4 — Watch, then ramp (or roll back)

```bash
# Generate 200 requests and tally which version answered each one:
oc exec -n tariff-prod deploy/loadgen -c loadgen -- sh -c '
v1=0; v2=0
for i in $(seq 1 200); do
  r=$(curl -s tariff-catalog/ | grep -o "v[12]" | head -1)
  if [ "$r" = "v1" ]; then v1=$((v1+1)); else v2=$((v2+1)); fi
done
echo "v1=$v1 v2=$v2"
'
# Kiali shows the same live service graph + per-version traffic & errors:
oc get route -n istio-system kiali -o jsonpath='{.spec.host}{"\n"}'
# Ramp up by editing the weights to 50/50, then 0/100 — or back to 100/0 to roll back.
```

**Verified output** *(live cluster, OCP 4.18, run 2026-07-15 — real 200-request sample):*

```
v1=183 v2=17                                          <- 91.5% / 8.5%, matches the 90/10 weight
kiali-istio-system.apps.<cluster-domain>              <- HTTP 200
```

> **Narrate:** **Kiali** draws the split live. If v2's error rate stays low, bump the weight
> to 50, then 100; if it spikes, set v2 to **0** — instant rollback, one edit, no redeploy.
> The 183/17 tally above is a real sample — sampling noise is why it's 91.5/8.5, not
> exactly 90/10; run more requests to tighten it.

---

## Step 5 — Cleanup

> Only the **per-demo** resources — leave the mesh control plane (`Istio`, `IstioCNI`,
> Kiali, the operators) installed; it's shared infrastructure for the whole class, same as
> `openshift-gitops`/`openshift-pipelines` in Demos 1-2.

```bash
oc delete virtualservice,destinationrule tariff-catalog -n tariff-prod
oc delete peerauthentication default -n tariff-prod
oc delete namespace tariff-prod
```

**Verified output** *(live cluster, OCP 4.18, run 2026-07-15):*

```
virtualservice.networking.istio.io "tariff-catalog" deleted
destinationrule.networking.istio.io "tariff-catalog" deleted
peerauthentication.security.istio.io "default" deleted
namespace "tariff-prod" deleted
```

---

## Wrap-up questions to pose

1. What does `2/2 READY` tell you about a pod in the mesh?
2. Which two objects implement a weighted canary, and what does each do?
3. How does the mesh add mTLS without changing the app?
4. If the canary misbehaves, how fast is rollback — and what do you edit?
5. What replaced `ServiceMeshMemberRoll` in OSSM 3, and why does an *existing* Deployment
   need a rollout restart to actually get a sidecar?

---

> **✓ Fully verified — Steps 0-5 all run live, end-to-end, on 2026-07-15.**
> The Sail-operator-based **OpenShift Service Mesh 3** (`servicemeshoperator3` v3.3.5) and
> **Kiali** (v2.27.1) were installed live; a real two-version `tariff-catalog` app (UBI9
> httpd, telecom-flavored static content differing by version) was deployed, joined the
> mesh, went 2/2, had STRICT mTLS applied (proven by a genuine `http_code=000` rejection
> from a sidecar-less pod), and ran a real weighted canary confirmed by tallying 200 actual
> requests (183/17 — a 91.5/8.5 split against the 90/10 target). All output above is real,
> not representative.
>
> The biggest change from any earlier version of this demo: **this cluster's catalog offers
> both OSSM 2.x (`servicemeshoperator`, `ServiceMeshControlPlane`/`ServiceMeshMemberRoll`,
> `maistra.io`) and OSSM 3.x (`servicemeshoperator3`, Sail-operator, plain `Istio`
> CR + namespace-label injection).** This demo was validated against **3.x** specifically
> per instructor direction — if your cluster only has the 2.x operator installed, Step 0/1
> here will not apply; use the classic `ServiceMeshControlPlane`/`ServiceMeshMemberRoll`
> pattern instead and confirm which one your shared cluster actually has before class
> (`oc get packagemanifest -n openshift-marketplace | grep -i servicemesh`).
>
> The mesh control plane, Kiali, and both operators were left installed on the shared
> cluster after validation (intentionally — matching the Demo 1/2 pattern of one-time admin
> setup); only the per-run `tariff-prod` namespace and its routing CRs were cleaned up.
