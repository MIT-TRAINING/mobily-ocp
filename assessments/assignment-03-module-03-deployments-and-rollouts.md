# Assignment 3 — Deployments, Scaling & Zero-Downtime Rollouts

> **Module 3 · Kubernetes Workloads, Storage and Networking**
> **Telecom scenario:** It's the night before Mobily's monthly **billing run**, and
> self-care traffic triples. A single Pod (Assignment 2) won't survive a node
> reboot, can't scale, and can't be upgraded without an outage. You'll put
> `selfcare-api` behind a **Deployment**, scale it for peak load, expose it with a
> **Service**, then ship **v1.1.0** as a **zero-downtime rolling update** — and
> **roll it back** when "QA" flags a regression.

| | |
|---|---|
| **Maps to** | Deployments & ReplicaSets · Services · rolling updates & rollbacks |
| **Tools** | `minikube` + `kubectl` |
| **Provided** | `selfcare-api:1.0.0` (Assignment 1) + a `1.1.0` you build here |
| **Difficulty** | ⭐⭐⭐ Advanced · ~70 min |
| **Weight** | 20 % of the Modules 1–3 assessment |

---

## Learning objectives

By the end you can:

1. Explain the **Deployment → ReplicaSet → Pod** ownership chain and how it
   self-heals to the declared replica count.
2. **Scale** a workload up and down declaratively and imperatively.
3. Expose Pods with a **Service** (stable virtual IP + DNS) and reach them.
4. Perform a **rolling update** with a surge/unavailable budget so no request is
   dropped, and watch the ReplicaSet handover.
5. **Roll back** to the previous revision and explain how the history is kept.

## Prerequisites

```bash
minikube start
kubectl create namespace selfcare 2>/dev/null || true   # or apply your A2 namespace.yaml
minikube image load selfcare-api:1.0.0                   # from Assignment 1
```

Build the **v1.1.0** image (the "new tariff banner" release). The app stamps its
version from a build-arg:

```bash
cd assessments/app
# NOTE: build --no-cache here. The only change is the ARG, and the ENV layer text
# is byte-identical to 1.0.0, so Buildah would otherwise REUSE the cached layer
# and silently ship 1.0.0 again (a real layer-cache gotcha from Module 1).
podman build --no-cache --build-arg APP_VERSION=1.1.0 -t selfcare-api:1.1.0 .
podman run --rm -d --name v -p 19090:8080 selfcare-api:1.1.0 && sleep 2
curl -s localhost:19090/version | grep '"version"'      # must say 1.1.0
podman rm -f v
minikube image load selfcare-api:1.1.0
```

---

## Tasks

### Part A — Deployment + self-healing (5 pts)
1. Write `deployment.yaml`: a **Deployment** `selfcare-api` in namespace
   `selfcare`, **3 replicas**, image `selfcare-api:1.0.0`,
   `imagePullPolicy: IfNotPresent`, readiness + liveness probes on `/healthz`,
   and modest `resources.requests/limits`.
2. `apply` it. Confirm **3** Pods `Running` and that a **ReplicaSet** owns them
   (`kubectl get rs -n selfcare`).
3. **Prove self-healing:** delete one Pod and watch the ReplicaSet recreate it
   back to 3. Which controller did that, and how did it know?

### Part B — Scale for the billing run (4 pts)
4. Scale to **5** replicas *declaratively* (edit the manifest, `apply`). Confirm 5.
5. Scale back to **2** *imperatively* (`kubectl scale`). Confirm 2. When would you
   use each method in real operations?

### Part C — Expose with a Service (4 pts)
6. Write `service.yaml`: a **NodePort** Service `selfcare-api` selecting
   `app=selfcare-api`, `port: 80 → targetPort: 8080`, `nodePort: 30080`.
7. Reach it via `minikube service selfcare-api -n selfcare --url` (or
   `curl $(minikube ip):30080/version`). Hit it several times — note the `"pod"`
   field in `/version` **changes**, proving the Service load-balances across Pods.
8. From a throwaway Pod, resolve the Service's **cluster DNS** name
   (`selfcare-api.selfcare.svc.cluster.local`) and curl it. Why is this name
   stable even as Pods come and go?

### Part D — Zero-downtime rolling update (5 pts)
9. Set the Deployment's `strategy` to `RollingUpdate` with
   `maxUnavailable: 0, maxSurge: 1`. Update the image to `selfcare-api:1.1.0` and
   `apply`.
10. **While it rolls**, run a tight `curl` loop against the Service and show that
    **every** request returns `200` (no `Connection refused`, no `5xx`) — and that
    the `"version"` flips from `1.0.0` to `1.1.0` partway through.
11. Inspect `kubectl rollout status` and `kubectl get rs` — show the **old**
    ReplicaSet scaling to 0 while the **new** one scales to the replica count.

### Part E — Roll back (2 pts)
12. "QA" rejects 1.1.0. `kubectl rollout undo` to the previous revision, confirm
    `/version` is back to `1.0.0`, and show `kubectl rollout history` listing both
    revisions.

---

## Deliverables

`submission-03.md` with: your `deployment.yaml` and `service.yaml`; output of
`kubectl get deploy,rs,pod -n selfcare` at 3 replicas; the self-healing
before/after; the `curl`-loop transcript during the rollout (showing no failed
request and the version flip); `kubectl rollout history deployment/selfcare-api`;
and written answers to Tasks 3, 5, and 8.

---

## Validation (self-check)

```bash
# A2/A3 — 3 healthy pods, one ReplicaSet:
kubectl get deploy selfcare-api -n selfcare -o jsonpath='{.status.readyReplicas}'   # 3

# C7 — Service load-balances (run a few times; pod id varies):
for i in 1 2 3 4; do curl -s $(minikube ip):30080/version | grep '"pod"'; done

# D10 — no-downtime rollout (run in one shell during `kubectl apply` in another):
end=$((SECONDS+40)); ok=0; bad=0
while [ $SECONDS -lt $end ]; do
  code=$(curl -s -o /dev/null -w '%{http_code}' $(minikube ip):30080/healthz)
  [ "$code" = "200" ] && ok=$((ok+1)) || bad=$((bad+1)); sleep 0.2
done
echo "ok=$ok bad=$bad"     # PASS when bad=0

# E12 — rolled back:
curl -s $(minikube ip):30080/version | grep -q '"version": "1.0.0"' && echo "PASS rollback"
```

---

## Grading rubric (20 pts)

| Criteria | Pts |
|---|---|
| Deployment runs 3 replicas; self-healing demonstrated + explained | 5 |
| Scale up (declarative) and down (imperative) both shown | 4 |
| Service reachable; load-balancing **and** cluster-DNS shown | 4 |
| Rolling update with **zero failed requests** + ReplicaSet handover shown | 5 |
| Successful rollback + `rollout history` | 2 |
| **Total** | **20** |

> Deduction: a rollout that drops requests because `maxUnavailable>0` *and* probes
> are missing/wrong (−3). The whole point is **zero-downtime**.

---

## Stretch goals (not graded)

- Add `minReadySeconds: 5` and re-run the rollout — how does it change the pace?
- `kubectl rollout pause` mid-update (a canary), verify a *mix* of 1.0.0/1.1.0
  Pods serve, then `resume`.
- Set a bad image tag (`selfcare-api:9.9.9`) and watch the rollout **stall** on
  `ImagePullBackOff` without taking down the running v1.0.0 Pods. Why is that safe?

---

<details>
<summary><strong>✅ Reference solution</strong> (attempt the tasks first)</summary>

**deployment.yaml**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: selfcare-api
  namespace: selfcare
  labels: { app: selfcare-api }
spec:
  replicas: 3
  revisionHistoryLimit: 5
  selector:
    matchLabels: { app: selfcare-api }
  strategy:
    type: RollingUpdate
    rollingUpdate: { maxUnavailable: 0, maxSurge: 1 }
  template:
    metadata:
      labels: { app: selfcare-api }
    spec:
      containers:
        - name: selfcare-api
          image: selfcare-api:1.0.0
          imagePullPolicy: IfNotPresent
          ports: [{ containerPort: 8080 }]
          env:
            - { name: SELFCARE_REGION, value: "minikube-dev" }
          readinessProbe:
            httpGet: { path: /healthz, port: 8080 }
            initialDelaySeconds: 2
            periodSeconds: 5
          livenessProbe:
            httpGet: { path: /healthz, port: 8080 }
            initialDelaySeconds: 5
            periodSeconds: 10
          resources:
            requests: { cpu: "50m", memory: "64Mi" }
            limits:   { cpu: "250m", memory: "128Mi" }
```

**service.yaml**
```yaml
apiVersion: v1
kind: Service
metadata:
  name: selfcare-api
  namespace: selfcare
spec:
  type: NodePort
  selector: { app: selfcare-api }
  ports:
    - { name: http, port: 80, targetPort: 8080, nodePort: 30080 }
```

```bash
# A — deploy + self-heal
kubectl apply -f deployment.yaml
kubectl get deploy,rs,pod -n selfcare
kubectl delete pod -n selfcare -l app=selfcare-api --field-selector=status.phase=Running | head -1
kubectl get pod -n selfcare -w     # the ReplicaSet controller recreates it back to 3

# B — scale
sed -i 's/replicas: 3/replicas: 5/' deployment.yaml && kubectl apply -f deployment.yaml   # declarative
kubectl scale deploy/selfcare-api -n selfcare --replicas=2                                 # imperative

# C — expose
kubectl apply -f service.yaml
curl -s $(minikube ip):30080/version            # repeat -> "pod" varies = load balanced
kubectl run tmp -n selfcare --rm -it --image=registry.access.redhat.com/ubi9/ubi-minimal -- \
  curl -s selfcare-api.selfcare.svc.cluster.local/healthz
# DNS name is stable because it points at the Service's clusterIP, not at any Pod IP.

# D — rolling update to 1.1.0 (strategy already RollingUpdate/maxUnavailable:0)
kubectl set image deploy/selfcare-api -n selfcare selfcare-api=selfcare-api:1.1.0
kubectl rollout status deploy/selfcare-api -n selfcare
kubectl get rs -n selfcare        # old RS -> 0, new RS -> N

# E — rollback
kubectl rollout undo deploy/selfcare-api -n selfcare
kubectl rollout history deploy/selfcare-api -n selfcare
curl -s $(minikube ip):30080/version    # back to 1.0.0
```

**Key point:** a Deployment owns a ReplicaSet which owns Pods; the **ReplicaSet
controller** continuously reconciles actual→desired replica count (self-healing).
A rolling update creates a *second* ReplicaSet and shifts Pods across with a
surge/unavailable budget — with good probes and `maxUnavailable: 0`, not a single
request is dropped. Every revision's ReplicaSet is retained, which is exactly what
makes `rollout undo` instant.
</details>

---

> **✅ Verified:** the `selfcare-api:1.0.0` and `:1.1.0` images (incl. the
> `--no-cache` build-arg gotcha) were built and run on podman 5.8.2 · 2026-06-25 —
> `/version` confirmed `1.0.0` vs `1.1.0`. All Kubernetes manifests pass
> `kubectl apply --dry-run=client` (v1.34). Run on minikube for the live rollout
> transcript (cluster-specific).
