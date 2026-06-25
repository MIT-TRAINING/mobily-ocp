# Demo 2 — Rolling Updates & Rollbacks

> **Scenario:** The **tariff-catalog** service powers every plan lookup in the
> self-care app. We need to ship a new version of its web tier **without a single
> failed request**, prove the old version is still one command away if the new one
> misbehaves, and learn the pause/resume trick for batching several changes into one
> rollout. We use real nginx images so the version is *visible* before and after.

| | |
|---|---|
| **Concepts reinforced** | `set image` · maxSurge/maxUnavailable · `rollout status/history/undo/pause/resume` · `change-cause` · ReplicaSet-per-version |
| **Maps to** | Guide §4 (Rolling updates & rollbacks) · Exercise 2 |
| **Time** | ~30 minutes |
| **Cluster** | minikube; single node is fine |

---

> **⎈ Same on OpenShift:** `oc set image`, `oc rollout status/history/undo/pause/resume`
> are identical. The OpenShift web console renders the same revision history
> graphically; the CLI is unchanged.

## Talking points to open with

- A Deployment manages *multiple* ReplicaSets — one per version — so it can shift
  traffic old→new gradually and reverse it.
- Two knobs bound the disruption: **maxUnavailable** (how many can be down) and
  **maxSurge** (how many extra can run). Capacity never dips below your guarantee.
- The `change-cause` annotation is your audit trail — fill it in on every release.

---

## Step 1 — Deploy v1 and record the initial revision

We start the catalog on **nginx 1.25** (a real server image, so we can read its
version), and annotate the initial release:

```bash
kubectl create deployment tariff-catalog \
  --image=docker.io/library/nginx:1.25-alpine --replicas=3
kubectl annotate deployment/tariff-catalog \
  kubernetes.io/change-cause="nginx 1.25 - initial release" --overwrite
kubectl rollout status deployment/tariff-catalog
POD=$(kubectl get pods -l app=tariff-catalog -o jsonpath='{.items[0].metadata.name}')
kubectl exec "$POD" -- nginx -v
```

**Expected output:**

```
deployment.apps/tariff-catalog created
deployment.apps/tariff-catalog annotated
Waiting for deployment "tariff-catalog" rollout to finish: 0 of 3 updated replicas are available...
Waiting for deployment "tariff-catalog" rollout to finish: 1 of 3 updated replicas are available...
Waiting for deployment "tariff-catalog" rollout to finish: 2 of 3 updated replicas are available...
deployment "tariff-catalog" successfully rolled out
nginx version: nginx/1.25.5
```

> **Narrate:** Three pods of nginx **1.25.5**, all reporting ready before
> `rollout status` returns. We've recorded *why* this revision exists with
> `change-cause`. That annotation is the only thing that makes the history readable
> later.

---

## Step 2 — Roll out v2 with zero downtime

Upgrade the image and record the reason in one breath:

```bash
kubectl set image deployment/tariff-catalog nginx=docker.io/library/nginx:1.26-alpine
kubectl annotate deployment/tariff-catalog \
  kubernetes.io/change-cause="upgrade nginx 1.25 -> 1.26" --overwrite
kubectl rollout status deployment/tariff-catalog
```

**Expected output:**

```
deployment.apps/tariff-catalog image updated
deployment.apps/tariff-catalog annotated
Waiting for deployment "tariff-catalog" rollout to finish: 1 out of 3 new replicas have been updated...
Waiting for deployment "tariff-catalog" rollout to finish: 2 out of 3 new replicas have been updated...
Waiting for deployment "tariff-catalog" rollout to finish: 1 old replicas are pending termination...
deployment "tariff-catalog" successfully rolled out
```

> **Narrate:** Watch the language: *"N out of 3 **new** replicas have been
> updated"* then *"1 **old** replicas are pending termination."* The Deployment
> spun up a **second ReplicaSet** for 1.26 and drained the 1.25 one — new pods come
> up Ready *before* old ones leave, so the service never dropped below capacity.

Confirm the two ReplicaSets — new one active, old one parked at zero:

```bash
kubectl get rs -l app=tariff-catalog \
  -o 'custom-columns=NAME:.metadata.name,DESIRED:.spec.replicas,READY:.status.readyReplicas,IMAGE:.spec.template.spec.containers[0].image'
```

**Expected output:**

```
NAME                        DESIRED   READY    IMAGE
tariff-catalog-5bd7bbd4bb   3         3        docker.io/library/nginx:1.26-alpine
tariff-catalog-6d99c7b5b6   0         <none>   docker.io/library/nginx:1.25-alpine
```

> **Narrate:** The old ReplicaSet isn't deleted — it's scaled to **0** and kept.
> That parked ReplicaSet is *exactly* what makes rollback instant: the recipe for
> v1 is still on file.

---

## Step 3 — Read the revision history

```bash
kubectl rollout history deployment/tariff-catalog
```

**Expected output:**

```
REVISION  CHANGE-CAUSE
1         nginx 1.25 - initial release
2         upgrade nginx 1.25 -> 1.26
```

> **Narrate:** This readable history exists *only* because we annotated each change.
> Without `change-cause` you'd see `<none>` and have to diff YAML to know what
> happened. Treat the annotation as mandatory on every release.

---

## Step 4 — Roll back a bad release in one command

Say monitoring lights up after 1.26. Undo it:

```bash
kubectl rollout undo deployment/tariff-catalog
kubectl rollout status deployment/tariff-catalog
POD=$(kubectl get pods -l app=tariff-catalog -o jsonpath='{.items[0].metadata.name}')
kubectl exec "$POD" -- nginx -v
kubectl rollout history deployment/tariff-catalog
```

**Expected output:**

```
deployment.apps/tariff-catalog rolled back
Waiting for deployment "tariff-catalog" rollout to finish: 1 out of 3 new replicas have been updated...
Waiting for deployment "tariff-catalog" rollout to finish: 1 old replicas are pending termination...
deployment "tariff-catalog" successfully rolled out
nginx version: nginx/1.25.5
REVISION  CHANGE-CAUSE
2         upgrade nginx 1.25 -> 1.26
3         nginx 1.25 - initial release
```

> **Narrate:** The pods are back on **1.25.5** — proven, not asserted. Notice the
> history *re-numbered*: revision 1 became revision **3** because a rollback is just
> another rolling update whose target template happens to be an old one. The thing
> you rolled back *to* is now the newest revision.

---

## Step 5 — Pause & resume: batch changes into one rollout

You have *two* changes to make (new image + resource limits) and don't want two
separate rollouts. Pause, edit, resume:

```bash
kubectl rollout pause deployment/tariff-catalog
kubectl set image deployment/tariff-catalog nginx=docker.io/library/nginx:1.26-alpine
kubectl set resources deployment/tariff-catalog --limits=cpu=100m,memory=64Mi
kubectl rollout resume deployment/tariff-catalog
kubectl rollout status deployment/tariff-catalog
```

**Expected output:**

```
deployment.apps/tariff-catalog paused
deployment.apps/tariff-catalog image updated
deployment.apps/tariff-catalog resource requirements updated
deployment.apps/tariff-catalog resumed
Waiting for deployment "tariff-catalog" rollout to finish: 1 out of 3 new replicas have been updated...
Waiting for deployment "tariff-catalog" rollout to finish: 1 old replicas are pending termination...
deployment "tariff-catalog" successfully rolled out
```

> **Narrate:** Between `paused` and `resumed`, both edits were recorded but **no new
> pods rolled out** — the Deployment held still. `resume` then applied *both* changes
> in a **single** rollout. Without pausing, each `set` command would have triggered
> its own rollout, churning pods twice. Pause is how you make a multi-part change
> land atomically.

Confirm the final state — version 1.26, limits applied:

```bash
POD=$(kubectl get pods -l app=tariff-catalog --field-selector=status.phase=Running -o jsonpath='{.items[0].metadata.name}')
kubectl exec "$POD" -- nginx -v
```

**Expected output:**

```
nginx version: nginx/1.26.3
```

---

## Step 6 — Cleanup

```bash
kubectl delete deployment tariff-catalog
```

**Expected output:**

```
deployment.apps/tariff-catalog deleted
```

---

## Wrap-up questions to pose

1. During the update, why did the service never drop below 3 ready pods?
2. What is the old ReplicaSet doing after the update, and why is it kept?
3. After a rollback, why do the revision numbers *increase* rather than go back?
4. What would have happened in Step 5 if you'd run the two `set` commands *without*
   pausing first?

---

> **✅ Verified:** kubectl 1.34 · Kubernetes 1.33 (3-node kind, equivalent plain
> Kubernetes) · images `nginx:1.25-alpine` / `nginx:1.26-alpine`. Every step —
> initial deploy (1.25.5), rolling update (1.26.3), two-ReplicaSet check, history,
> rollback back to 1.25.5, and pause/resume batching two changes into one rollout —
> was run live and the output above is from that run.
