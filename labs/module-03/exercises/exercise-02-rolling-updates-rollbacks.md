# Exercise 2 — Rolling Updates & Rollbacks

> **Scenario:** The **tariff-catalog** web tier needs a version bump shipped with
> **zero failed requests**, and you must be able to undo it instantly if monitoring
> complains. You'll roll forward, read the revision history, and roll back — proving
> the version change with the server's own `nginx -v`.

| | |
|---|---|
| **Practice** | `set image`, `change-cause`, `rollout status/history/undo`, ReplicaSet-per-version |
| **Maps to** | Guide §4 · Demo 2 |
| **Difficulty** | ⭐⭐ Intermediate · ~25 min · single-node OK |

---

## Tasks

1. Create a Deployment **`tariff-catalog`** from `docker.io/library/nginx:1.25-alpine`
   with **3 replicas**, and record an initial **change-cause** of your choosing.
2. Confirm the running version is **1.25.x** by execing `nginx -v` in a pod.
3. **Roll it forward** to `nginx:1.26-alpine`, recording a change-cause, and wait
   for the rollout to finish. Confirm the version is now **1.26.x**.
4. Show the **two ReplicaSets** (new one at 3, old one at 0) and read the **rollout
   history** — both your change-causes should appear.
5. **Roll back** to the previous revision. Confirm the version returns to **1.25.x**
   and observe how the history **re-numbers**.

> **Hint (Task 1):** set the cause with
> `kubectl annotate deployment/tariff-catalog kubernetes.io/change-cause="..." --overwrite`.

> **Hint (Task 3):** `kubectl set image deployment/tariff-catalog nginx=<image>`
> then `kubectl rollout status deployment/tariff-catalog`.

---

## Validation

```bash
# Task 2 / 3 / 5 — read the actual server version from a running pod
POD=$(kubectl get pods -l app=tariff-catalog --field-selector=status.phase=Running -o jsonpath='{.items[0].metadata.name}')
kubectl exec "$POD" -- nginx -v

# Task 4 — two ReplicaSets: new one DESIRED 3, old one DESIRED 0
kubectl get rs -l app=tariff-catalog \
  -o 'custom-columns=NAME:.metadata.name,DESIRED:.spec.replicas,IMAGE:.spec.template.spec.containers[0].image'

# Task 4 / 5 — revision history
kubectl rollout history deployment/tariff-catalog
```

---

## Reflection

- During the update, how does the Deployment keep capacity from dropping below 3?
- Why is the old ReplicaSet kept at 0 replicas instead of being deleted?
- After a rollback, why does the revision number *increase* rather than return to an
  earlier number?

---

<details>
<summary><strong>✅ Solution</strong> (try the tasks first)</summary>

```bash
# 1. Deploy v1 + initial cause
kubectl create deployment tariff-catalog \
  --image=docker.io/library/nginx:1.25-alpine --replicas=3
kubectl annotate deployment/tariff-catalog \
  kubernetes.io/change-cause="nginx 1.25 - initial release" --overwrite
kubectl rollout status deployment/tariff-catalog

# 2. Prove the version
POD=$(kubectl get pods -l app=tariff-catalog -o jsonpath='{.items[0].metadata.name}')
kubectl exec "$POD" -- nginx -v        # nginx version: nginx/1.25.5

# 3. Roll forward to 1.26 + cause
kubectl set image deployment/tariff-catalog nginx=docker.io/library/nginx:1.26-alpine
kubectl annotate deployment/tariff-catalog \
  kubernetes.io/change-cause="upgrade nginx 1.25 -> 1.26" --overwrite
kubectl rollout status deployment/tariff-catalog
POD=$(kubectl get pods -l app=tariff-catalog --field-selector=status.phase=Running -o jsonpath='{.items[0].metadata.name}')
kubectl exec "$POD" -- nginx -v        # nginx version: nginx/1.26.3

# 4. Two ReplicaSets + history
kubectl get rs -l app=tariff-catalog \
  -o 'custom-columns=NAME:.metadata.name,DESIRED:.spec.replicas,IMAGE:.spec.template.spec.containers[0].image'
kubectl rollout history deployment/tariff-catalog

# 5. Roll back
kubectl rollout undo deployment/tariff-catalog
kubectl rollout status deployment/tariff-catalog
POD=$(kubectl get pods -l app=tariff-catalog --field-selector=status.phase=Running -o jsonpath='{.items[0].metadata.name}')
kubectl exec "$POD" -- nginx -v        # back to nginx/1.25.5
kubectl rollout history deployment/tariff-catalog

# Cleanup
kubectl delete deployment tariff-catalog
```

**Verified output (key lines):**

```
nginx version: nginx/1.25.5         # before
nginx version: nginx/1.26.3         # after roll-forward

NAME                        DESIRED   IMAGE
tariff-catalog-5bd7bbd4bb   3         docker.io/library/nginx:1.26-alpine
tariff-catalog-6d99c7b5b6   0         docker.io/library/nginx:1.25-alpine

REVISION  CHANGE-CAUSE                  # after rollback, re-numbered:
2         upgrade nginx 1.25 -> 1.26
3         nginx 1.25 - initial release
nginx version: nginx/1.25.5          # after rollback
```

**Key point:** a Deployment keeps one ReplicaSet *per version*. Roll-forward shifts
replicas new←old with new pods Ready before old ones leave (no downtime); rollback is
just another rolling update toward an old template, so history numbers keep climbing.
</details>

---

> **✅ Verified:** kubectl 1.34 · Kubernetes 1.33 (3-node kind, equivalent plain
> Kubernetes) · images `nginx:1.25-alpine` / `nginx:1.26-alpine`. The deploy, the
> visible 1.25.5→1.26.3 upgrade, the two-ReplicaSet listing, the history, and the
> rollback back to 1.25.5 (with re-numbered history) were all run live.
