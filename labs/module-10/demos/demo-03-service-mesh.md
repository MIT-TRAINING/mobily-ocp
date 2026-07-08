# Demo 3 — Service Mesh Canary

> **Scenario:** Release **tariff-catalog v2** safely. We add the app's namespace to the
> mesh (sidecars inject → pods go **2/2**), turn on **STRICT mTLS**, then use a
> **VirtualService** to send **10%** of traffic to v2, watch it in **Kiali**, and ramp up —
> all without changing app code or adding a Route.

| | |
|---|---|
| **Concepts reinforced** | ServiceMeshMemberRoll · sidecar injection (2/2) · PeerAuthentication (mTLS) · VirtualService + DestinationRule (canary) · Kiali |
| **Maps to** | Guide §8, §9, §10 · Visualization 03 · Exercise 3 |
| **Time** | ~30 minutes |
| **Cluster** | Shared OCP 4.18 with **OpenShift Service Mesh** (+ Kiali, tracing) Operators — install/control-plane need admin |

---

> **⎈ Kubernetes equivalent:** OSSM is Red Hat's Istio; the CRDs (`VirtualService`,
> `DestinationRule`, `PeerAuthentication`, `ServiceMeshControlPlane`) come from the Operators.

> ⚠️ Installing the Service Mesh Operators + creating the `ServiceMeshControlPlane` need
> **cluster-admin**. Joining a namespace and adding routing CRs can be a project user (once
> the mesh exists).

## Talking points to open with

- The mesh adds mTLS, routing, and observability **in the sidecar** — the app doesn't
  change.
- **Injection** makes pods **2/2** (app + Envoy). Istiod (control plane) programs the
  sidecars (data plane).
- **Canary** = shift a traffic **weight** with a VirtualService; ramp up or roll back
  instantly.

---

## Step 1 — Confirm the mesh & join the namespace

```bash
oc get smcp -n istio-system                        # ServiceMeshControlPlane Ready
oc apply -f - <<'EOF'
apiVersion: maistra.io/v1
kind: ServiceMeshMemberRoll
metadata: { name: default, namespace: istio-system }
spec: { members: [ tariff-prod ] }
EOF
```

**Expected output** *(requires a cluster + admin — representative of OCP 4.18):*

```
NAME    READY   STATUS            VERSION
basic   3/3     ComponentsReady   2.x
servicemeshmemberroll.maistra.io/default configured
```

> **Narrate:** The `ServiceMeshControlPlane` (SMCP) is the mesh; the
> `ServiceMeshMemberRoll` lists which namespaces join it. `tariff-prod` is now a member.

---

## Step 2 — Inject sidecars (pods go 2/2)

```bash
# apps opt in via an annotation on the pod template:
oc patch deployment tariff-catalog-v1 -n tariff-prod --type=merge \
  -p '{"spec":{"template":{"metadata":{"annotations":{"sidecar.istio.io/inject":"true"}}}}}'
oc rollout status deploy/tariff-catalog-v1 -n tariff-prod
oc get pods -n tariff-prod
```

**Expected output** *(requires a cluster — representative):*

```
deployment.apps/tariff-catalog-v1 patched
NAME                                READY   STATUS
tariff-catalog-v1-...               2/2     Running     <- app + Envoy sidecar
tariff-catalog-v2-...               2/2     Running
```

> **Narrate:** **2/2** is the tell — the Envoy sidecar joined each pod. Now all traffic
> flows through the mesh; the app binary is unchanged.

---

## Step 3 — Require mTLS (zero-trust)

```bash
oc apply -f - <<'EOF'
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata: { name: default, namespace: tariff-prod }
spec: { mtls: { mode: STRICT } }
EOF
```

**Expected output** *(requires a cluster — representative):*

```
peerauthentication.security.istio.io/default created
```

> **Narrate:** STRICT mTLS makes the sidecars encrypt and mutually authenticate all
> service traffic in `tariff-prod`. Zero-trust between services — and the app did nothing.

---

## Step 4 — Canary: 90% v1 / 10% v2

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

**Expected output** *(requires a cluster — representative):*

```
destinationrule.networking.istio.io/tariff-catalog created
virtualservice.networking.istio.io/tariff-catalog created
```

> **Narrate:** The **DestinationRule** defines the subsets (v1/v2 by label); the
> **VirtualService** sends **90/10**. Send traffic and ~1 in 10 requests hits v2 — a canary,
> with no new Route and no redeploy.

---

## Step 5 — Watch, then ramp (or roll back)

```bash
# Generate load and watch the split / v2 error rate:
for i in $(seq 1 50); do oc exec deploy/loadgen -n tariff-prod -- curl -s tariff-catalog/ >/dev/null; done
# Kiali shows the live service graph + per-version traffic & errors:
oc get route -n istio-system kiali -o jsonpath='{.spec.host}{"\n"}'
# Ramp up by editing the weights to 50/50, then 0/100 — or back to 100/0 to roll back.
```

**Expected output** *(requires a cluster — representative):*

```
kiali-istio-system.apps.<cluster-domain>
# Kiali graph: tariff-catalog → v1 (≈90%) and v2 (≈10%), error rates per version
```

> **Narrate:** **Kiali** draws the split live. If v2's error rate stays low, bump the weight
> to 50, then 100; if it spikes, set v2 to **0** — instant rollback, one edit, no redeploy.

---

## Step 6 — Cleanup

```bash
oc delete virtualservice,destinationrule tariff-catalog -n tariff-prod
oc delete peerauthentication default -n tariff-prod
```

**Expected output** *(representative):*

```
virtualservice.networking.istio.io "tariff-catalog" deleted
destinationrule.networking.istio.io "tariff-catalog" deleted
peerauthentication.security.istio.io "default" deleted
```

---

## Wrap-up questions to pose

1. What does `2/2 READY` tell you about a pod in the mesh?
2. Which two objects implement a weighted canary, and what does each do?
3. How does the mesh add mTLS without changing the app?
4. If the canary misbehaves, how fast is rollback — and what do you edit?

---

> **◐ Partially verified:** the CR **schemas** follow OSSM/Istio (v2.x) references, but every
> step **requires a live OpenShift cluster with the Service Mesh Operators** (install +
> `ServiceMeshControlPlane` need **cluster-admin**) and was not run at authoring (cluster
> asleep). Output is **representative of OpenShift 4.18 / OSSM 2.x**; exact versions and the
> `maistra.io`/`networking.istio.io` API versions vary by OSSM release. Validate live when
> the cluster is up.
