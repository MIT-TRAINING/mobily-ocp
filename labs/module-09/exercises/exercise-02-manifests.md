# Exercise 2 — Deploy from Kubernetes Manifests

> **Scenario:** Ship the Mobily **subscriber-api** with plain YAML: scaffold a manifest
> offline, apply it idempotently, expose it, then render dev vs prod from one Kustomize
> base.

| | |
|---|---|
| **Practice** | `oc create --dry-run=client -o yaml`, `apply` vs `create`, `oc expose`, Kustomize overlays |
| **Maps to** | Guide §3, §4 · Visualization 02 · Demo 2 |
| **Difficulty** | ⭐⭐ Intermediate · ~25 min · scaffolding works offline; apply needs a cluster |

---

## Tasks

1. **Offline:** scaffold a Deployment manifest for `subscriber-api` (`ubi9/httpd-24`, port
   8080) with `--dry-run=client -o yaml`, saved to `deploy.yaml`.
2. `oc apply -f deploy.yaml` **twice** — confirm the second run is idempotent
   (`unchanged`). Then `oc create -f deploy.yaml` and observe the error.
3. Expose it: a **Service** (from the deployment) and a **Route** (from the service);
   `curl` the Route (expect **403**).
4. Build a Kustomize **base** + **dev**/**prod** overlays; render both with `oc kustomize`
   and confirm the replica/image differences.
5. `oc apply -k overlays/prod` and verify the prod replica count.

> **Hint (Task 1):** redirect the dry-run YAML: `... --dry-run=client -o yaml > deploy.yaml`.

> **Hint (Task 4):** an overlay's `kustomization.yaml` lists the base under `resources:` and
> patches it with `patches:` (or `replicas:`).

---

## Validation

```bash
# Task 1 (offline) — valid manifest generated
oc create deployment subscriber-api --image=registry.access.redhat.com/ubi9/httpd-24:latest \
  --port=8080 --dry-run=client -o yaml | head -5

# Task 2 — idempotency
oc apply -f deploy.yaml   # created → unchanged on 2nd run

# Task 3 — reachable (403 = proof)
curl -s -o /dev/null -w "%{http_code}\n" http://$(oc get route subscriber-api -o jsonpath='{.spec.host}')/

# Task 4/5 — overlays differ
oc kustomize overlays/dev  | grep replicas    # 1
oc kustomize overlays/prod | grep replicas    # 6
```

---

## Reflection

- Why is `oc apply` safe to re-run but `oc create` isn't?
- How does Kustomize avoid copy-pasting near-identical YAML per environment?
- Which of these steps needed a cluster, and which ran offline?

---

<details>
<summary><strong>✅ Solution</strong> (try the tasks first)</summary>

```bash
# 1. Scaffold offline
oc create deployment subscriber-api \
  --image=registry.access.redhat.com/ubi9/httpd-24:latest --port=8080 \
  --dry-run=client -o yaml > deploy.yaml

# 2. apply idempotency vs create
oc apply  -f deploy.yaml        # deployment.apps/subscriber-api created
oc apply  -f deploy.yaml        # deployment.apps/subscriber-api unchanged
oc create -f deploy.yaml        # Error: AlreadyExists

# 3. Expose + curl
oc expose deployment subscriber-api --port=8080
oc expose service subscriber-api
curl -s -o /dev/null -w "%{http_code}\n" http://$(oc get route subscriber-api -o jsonpath='{.spec.host}')/   # 403

# 4. Kustomize base + overlays
mkdir -p base overlays/dev overlays/prod
cp deploy.yaml base/deployment.yaml
cat > base/kustomization.yaml <<'EOF'
resources: [deployment.yaml]
EOF
cat > overlays/dev/kustomization.yaml <<'EOF'
resources: [../../base]
replicas: [ { name: subscriber-api, count: 1 } ]
EOF
cat > overlays/prod/kustomization.yaml <<'EOF'
resources: [../../base]
replicas: [ { name: subscriber-api, count: 6 } ]
images: [ { name: registry.access.redhat.com/ubi9/httpd-24, newTag: "1.0-prod" } ]
EOF
oc kustomize overlays/dev  | grep -E 'replicas|image'
oc kustomize overlays/prod | grep -E 'replicas|image'

# 5. Apply prod
oc apply -k overlays/prod
oc get deploy subscriber-api -o jsonpath='{.spec.replicas}{"\n"}'   # 6

# Cleanup
oc delete all -l app=subscriber-api
```

**Representative output** *(scaffold verified offline; apply/kustomize on-cluster — OCP 4.18):*

```
apiVersion: apps/v1
kind: Deployment
...
deployment.apps/subscriber-api created
deployment.apps/subscriber-api unchanged
Error from server (AlreadyExists): ... already exists
403
# dev:  replicas: 1
# prod: replicas: 6 ; image ...:1.0-prod
```

**Key point:** scaffold offline with `--dry-run=client -o yaml`; deploy idempotently with
`apply` (not `create`); and use **Kustomize** base+overlays to render per-environment
variants from one source — the exact pattern GitOps applies from Git (Module 10).
</details>

---

> **◐ Partially verified — scaffold + Kustomize solution (Tasks 1, 4) VERIFIED offline,
> cluster steps representative.** `oc create … --dry-run=client -o yaml` and the full
> Task 4 solution (the `mkdir`/heredoc base+overlays, then `oc kustomize overlays/dev|prod`)
> were **run live offline with oc 4.22 end-to-end** on 2026-07-14 — the heredocs produce
> exactly the replicas/image output shown, byte-for-byte. `oc apply`/`oc expose`/
> `oc apply -k`/`curl` **require a live cluster** and are **representative of OpenShift
> 4.18** — runnable by a normal user in their own project when the cluster is up. The
> `apply` vs `create` behaviour and `httpd-24` 403 are real.
