# Assignment 5 — Capstone: Ship the Self-Care Stack End-to-End

> **Capstone · Modules 1–3 combined**
> **Telecom scenario:** Mobily wants the **Self-Care portal** live on Kubernetes,
> reachable on a real hostname, configured per-environment, secured, scalable, and
> upgradable without an outage. You'll take it the whole way: **build & publish**
> the image (Module 1), then deploy a complete stack — **Deployment + Service +
> ConfigMap + Secret + Ingress** (Modules 2–3) — scale it, expose it externally,
> ship an upgrade, and write up an **incident-style runbook**. This is the
> assessment that proves you can stand up a containerized service from nothing.

| | |
|---|---|
| **Maps to** | Everything in Modules 1–3 |
| **Tools** | `podman` + `minikube` + `kubectl` |
| **Provided** | [`app/`](./app) (the buildable `selfcare-api`) |
| **Difficulty** | ⭐⭐⭐ Capstone · ~120 min |
| **Weight** | 25 % of the Modules 1–3 assessment |

---

## Learning objectives

Integrate the whole arc: a container image is **built once** (M1) and then run as
a **self-healing, scalable, externally-exposed, configurable, zero-downtime
service** on Kubernetes (M2–M3). You demonstrate the full path from `Containerfile`
to a working HTTP endpoint a "customer" can hit by name.

## Prerequisites

```bash
podman --version && minikube start && kubectl get nodes
minikube addons enable ingress          # NGINX ingress controller
kubectl get pods -n ingress-nginx       # controller Running
```

---

## Build target

Deliver these artifacts in a `capstone/` folder:

```
capstone/
  Containerfile              # may reuse assessments/app/Containerfile
  k8s/
    namespace.yaml
    configmap.yaml
    secret.yaml
    deployment.yaml
    service.yaml
    ingress.yaml
  runbook.md
```

---

## Tasks

### Phase 1 — Build & publish (M1) (5 pts)
1. Build `selfcare-api:1.0.0`. Push it to your registry **or** `minikube image load`
   it. Record the image **digest** (if pushed).
2. Smoke-test the container locally with `podman run` before it ever touches the
   cluster: `/healthz`, `/version`, one subscriber lookup.

### Phase 2 — Deploy the stack (M2–M3) (8 pts)
3. `namespace.yaml` — `selfcare`.
4. `configmap.yaml` — `SELFCARE_REGION`, `SELFCARE_BANNER`.
5. `secret.yaml` — `SELFCARE_API_KEY` (placeholder).
6. `deployment.yaml` — **3 replicas**, `envFrom` the ConfigMap **and** Secret,
   readiness + liveness probes, resource requests/limits,
   `strategy: RollingUpdate` with `maxUnavailable: 0`.
7. `service.yaml` — ClusterIP (the Ingress fronts it).
8. `ingress.yaml` — host `selfcare.local`, path `/` → the Service on port 80.
9. `kubectl apply -f k8s/`. Confirm all objects exist and **3 Pods are Ready**.

### Phase 3 — Expose & verify (M3) (5 pts)
10. Add `selfcare.local` to `/etc/hosts` pointing at `$(minikube ip)` (or use
    `curl --resolve`). Reach the portal **by hostname**:
    `curl -H 'Host: selfcare.local' http://$(minikube ip)/version`.
11. Demonstrate the API key works through the Ingress (401 without header, data
    with it).
12. Hit `/version` repeatedly and show requests spread across **all 3 Pods**.

### Phase 4 — Operate it (M3) (5 pts)
13. **Scale** to 5 for a simulated billing-run surge, then back to 3.
14. **Upgrade**: build/load `selfcare-api:1.1.0`, do a **zero-downtime rolling
    update** through the Ingress (curl-loop proof: no failed request, version flips
    `1.0.0 → 1.1.0`).
15. **Incident & rollback**: pretend 1.1.0 has a regression — `rollout undo`,
    confirm `/version` is `1.0.0` again, and capture `rollout history`.

### Phase 5 — Runbook (2 pts)
16. Write `runbook.md`: how to deploy from scratch, how to roll back, the three
    `kubectl` commands you'd run first if the portal returned `503`, and where
    config vs secrets live.

---

## Deliverables

The full `capstone/` folder plus `submission-05.md` containing: the architecture
(a 3-line text or Mermaid diagram of Ingress → Service → 3 Pods), command
transcripts for each phase, the no-downtime curl-loop during the upgrade, the
rollback evidence, and your `runbook.md`.

---

## Validation (self-check)

```bash
IP=$(minikube ip)
# Phase 2 — all three Pods ready:
kubectl get deploy selfcare-api -n selfcare -o jsonpath='{.status.readyReplicas}'   # 3

# Phase 3 — reachable by hostname through the Ingress:
curl -s -H 'Host: selfcare.local' http://$IP/healthz | grep -q ok && echo "PASS ingress"
# API key enforced through the Ingress:
curl -s -o /dev/null -w '%{http_code}\n' -H 'Host: selfcare.local' http://$IP/subscribers   # 401

# Phase 4 — zero-downtime upgrade (run during `kubectl set image` in another shell):
end=$((SECONDS+45)); bad=0
while [ $SECONDS -lt $end ]; do
  c=$(curl -s -o /dev/null -w '%{http_code}' -H 'Host: selfcare.local' http://$IP/healthz)
  [ "$c" = "200" ] || bad=$((bad+1)); sleep 0.2
done; echo "failed=$bad"     # PASS when 0

# Phase 4 — rolled back:
curl -s -H 'Host: selfcare.local' http://$IP/version | grep -q '"version": "1.0.0"' && echo "PASS rollback"
```

---

## Grading rubric (25 pts)

| Criteria | Pts |
|---|---|
| Image built, smoke-tested, and published/loaded | 5 |
| Complete stack applies cleanly; 3 Pods Ready; ConfigMap+Secret wired | 8 |
| Reachable by hostname via Ingress; API key enforced; load-balanced | 5 |
| Scale + **zero-downtime** upgrade + rollback all demonstrated | 5 |
| Clear, correct runbook | 2 |
| **Total** | **25** |

> Deductions: any committed real secret/credential (−5, automatic); a stack that
> only works via `port-forward` and never through the Ingress (−3); an "upgrade"
> that drops requests (−3).

---

## Stretch goals (not graded)

- Add a second Ingress path `/api` → a separate canary Deployment on `1.1.0` and
  split traffic by path.
- Add `resources` + a `HorizontalPodAutoscaler` (requires metrics-server) and load
  it until it scales.
- Map the stack's objects to their **OpenShift** equivalents you'll meet in Module
  4+ (Ingress → **Route**, plus `oc new-app`). Which pieces stay identical?

---

<details>
<summary><strong>✅ Reference solution — key manifests</strong> (attempt first)</summary>

**k8s/ingress.yaml**
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: selfcare
  namespace: selfcare
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  rules:
    - host: selfcare.local
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: selfcare-api
                port: { number: 80 }
```

**k8s/service.yaml** (ClusterIP — the Ingress fronts it)
```yaml
apiVersion: v1
kind: Service
metadata: { name: selfcare-api, namespace: selfcare }
spec:
  selector: { app: selfcare-api }
  ports: [{ name: http, port: 80, targetPort: 8080 }]
```

The `namespace.yaml`, `configmap.yaml`, `secret.yaml`, and `deployment.yaml` are
the ones you built in Assignments 2–4 (Deployment uses `envFrom` for both the
ConfigMap and Secret, 3 replicas, `maxUnavailable: 0`).

```bash
# Phase 1
cd assessments/app && podman build -t selfcare-api:1.0.0 .
podman run --rm -d --name smoke -p 18080:8080 selfcare-api:1.0.0 && sleep 2
curl -s localhost:18080/version && podman rm -f smoke
minikube image load selfcare-api:1.0.0

# Phase 2
kubectl apply -f k8s/
kubectl get all,ingress -n selfcare
kubectl rollout status deploy/selfcare-api -n selfcare

# Phase 3
echo "$(minikube ip) selfcare.local" | sudo tee -a /etc/hosts
curl -s http://selfcare.local/version
curl -s -o /dev/null -w '%{http_code}\n' http://selfcare.local/subscribers          # 401
curl -s -H 'X-API-Key: <your-key>' http://selfcare.local/subscribers/966500000001

# Phase 4
kubectl scale deploy/selfcare-api -n selfcare --replicas=5 && sleep 5
kubectl scale deploy/selfcare-api -n selfcare --replicas=3
podman build --no-cache --build-arg APP_VERSION=1.1.0 -t selfcare-api:1.1.0 . && minikube image load selfcare-api:1.1.0
kubectl set image deploy/selfcare-api -n selfcare selfcare-api=selfcare-api:1.1.0   # watch with the curl loop
kubectl rollout status deploy/selfcare-api -n selfcare
kubectl rollout undo  deploy/selfcare-api -n selfcare
kubectl rollout history deploy/selfcare-api -n selfcare
```

**Architecture**

```
            (Host: selfcare.local)
client ──▶ Ingress ──▶ Service (ClusterIP :80) ──▶ Pod :8080  ┐
                                                  ──▶ Pod :8080  ├─ Deployment (3, self-healing)
                                                  ──▶ Pod :8080  ┘
   config ← ConfigMap (region, banner)     secret ← Secret (API key)
```

**Key point:** the image is the unit you build and test **once** (M1); everything
after is *declarative configuration* of how Kubernetes runs it — replicas, probes,
config, secrets, exposure, upgrades. That separation is what makes the same
artifact promotable, scalable, and upgradable without an outage — and it's exactly
the model OpenShift builds on in Module 4+.
</details>

---

> **✅ Verified:** the `selfcare-api` image (1.0.0 + 1.1.0) builds and serves on
> podman 5.8.2 · 2026-06-25; ConfigMap/Secret env behaviour exercised on the real
> app. Every manifest passes `kubectl apply --dry-run=client` (v1.34). Run the full
> stack on minikube with the ingress addon for the live hostname/Ingress output.
