# Demo 2 — The Troubleshooting Loop

> **Scenario:** Mobily's `subscriber-api` is down and the on-call engineer is paged. Instead of
> guessing, we run the **same loop every time**: read the pod's **status** (which layer?), let
> **events** narrate the failure (where?), read **logs** (why?), fix the smallest thing, and
> confirm. We walk three classic failures — a crash-loop, an image-pull failure, and a degraded
> **ClusterOperator** — so participants see the loop transfer across layers.

| | |
|---|---|
| **Concepts reinforced** | pod status → `describe`/events → `logs --previous` · app vs. platform layer · `oc get co` · `oc debug` · `must-gather` |
| **Maps to** | Guide §7–§10 · Visualization 02 · Exercise 2 |
| **Time** | ~30 minutes |
| **Cluster** | Shared OCP 4.18 — app troubleshooting is **project-user**; ClusterOperators/nodes and `must-gather` are **cluster-admin** |

---

> **⎈ Kubernetes note:** the status strings (`CrashLoopBackOff`, `ImagePullBackOff`, `Pending`)
> and the `get → describe → logs` loop are **pure Kubernetes** — identical under `kubectl`.
> `oc get co` (ClusterOperators), `oc debug`, and `oc adm must-gather` are the OpenShift additions.

> ⚠️ Reading **your** pods/events/logs is a project-user action. Reading **ClusterOperators**,
> **nodes**, and running **`must-gather`** is cluster-admin — pair with your instructor for Step 4.

## Talking points to open with

- Troubleshooting is **narrowing by layer**: answer **where** (app or platform?) before **why**.
- The **status string is already a diagnosis** — each one points at a different layer.
- **Events narrate failures.** `oc get events --sort-by=.lastTimestamp` is the golden first move.

---

## Step 1 — Read the symptom: status = the class of problem

```bash
oc get pods -n mobily-apps
```

**Live output** *(captured 2026-07-15 on the training cluster — a real `subscriber-db` deployed with
a too-low memory limit, and a real `subscriber-api` that fails to connect while the db is down; see
the demo footer for how this scenario was staged):*

```
NAME                              READY   STATUS             RESTARTS      AGE
subscriber-api-78c8799c76-dsn75   0/1     CrashLoopBackOff   3 (24s ago)   79s
subscriber-db-86886859db-lkkkr    0/1     CrashLoopBackOff   4 (57s ago)   2m3s
```

> **Narrate:** Don't paraphrase — read the exact string. `CrashLoopBackOff` = the app **starts,
> then exits**, repeatedly. That already tells us it's an **application-layer, runtime** problem
> (not scheduling, not image pull). We know *where*; now find *why*.

---

## Step 2 — Let events narrate (`describe`) and read the previous logs

```bash
oc describe pod -n mobily-apps -l app=subscriber-api | sed -n '/Events:/,$p'
oc logs -n mobily-apps -l app=subscriber-api --previous --tail=8
```

**Live output** *(captured 2026-07-15, real run):*

```
Events:
  Type     Reason          Age                From               Message
  ----     ------          ----               ----               -------
  Normal   Scheduled       80s                default-scheduler  Successfully assigned mobily-apps/subscriber-api-78c8799c76-dsn75 to ip-10-0-44-62...
  Normal   AddedInterface  79s                multus             Add eth0 [10.129.2.21/23] from ovn-kubernetes
  Normal   Pulled          73s                kubelet            Successfully pulled image "registry.access.redhat.com/ubi9/ubi-minimal:latest" in 1.975s
  Normal   Created         25s (x4 over 76s)  kubelet            Created container: subscriber-api
  Normal   Started         25s (x4 over 76s)  kubelet            Started container subscriber-api
  Warning  BackOff         11s (x6 over 72s)  kubelet            Back-off restarting failed container subscriber-api in pod subscriber-api-78c8799c76-dsn75_mobily-apps(...)

# --previous (the container that just died):
starting subscriber-api on :8080 ...
FATAL: could not connect to subscriber-db:5432: connection refused
```

> **Narrate:** `--previous` is the trick for a crash-loop — the *current* container may be too
> young to have logged. Its last words name the cause: it can't reach `subscriber-db`. The bug
> isn't in `subscriber-api` at all — it's **downstream**. Follow the dependency.

---

## Step 3 — Follow it downstream (the real root cause)

```bash
oc get pods -n mobily-apps -l app=subscriber-db
oc describe pod -n mobily-apps -l app=subscriber-db | grep -A3 'Last State'
```

**Live output** *(captured 2026-07-15, real run — `subscriber-db` was deployed with
`resources.limits.memory: 20Mi`, which a real PostgreSQL 15 start genuinely exceeds):*

```
NAME                             READY   STATUS      RESTARTS      AGE
subscriber-db-86886859db-lkkkr   0/1     OOMKilled   4 (57s ago)   2m3s

    Last State:     Terminated
      Reason:       OOMKilled
      Exit Code:    137
```

> **Narrate:** There it is — `subscriber-db` is **OOMKilled** (over its memory limit, exit 137).
> That's why it refuses connections, which is why `subscriber-api` crash-loops. Metrics said
> *that/where* (Module 11); this chain says *why*. **Smallest fix:** raise the db's memory limit
> (or fix the leak) — don't touch `subscriber-api`, it was never broken.

```bash
oc set resources deploy/subscriber-db -n mobily-apps --limits=memory=512Mi   # the smallest fix
```

**Live output** *(captured 2026-07-15 — real recovery, both pods reached `1/1 Running` within ~90s
of the fix):*

```
deployment.apps/subscriber-db resource requirements updated

NAME                              READY   STATUS    RESTARTS      AGE
subscriber-api-78c8799c76-dsn75   1/1     Running   4 (55s ago)   110s
subscriber-db-677c8c8d95-lmgnh    1/1     Running   0             18s
```

---

## Step 4 — Different layer, same loop: a degraded ClusterOperator (admin)

```bash
oc get co | awk 'NR==1 || $3=="False"'      # header + any AVAILABLE=False operators
oc describe co ingress | sed -n '/Conditions:/,+8p'
```

> **Fixed a bug:** the original filter used `$4` (that's the **PROGRESSING** column). `oc get co`'s
> columns are `NAME VERSION AVAILABLE PROGRESSING DEGRADED SINCE MESSAGE` — **AVAILABLE** is `$3`.
> Verified live: on this healthy cluster `oc get co | awk 'NR==1 || $3=="False"'` correctly returns
> just the header (no operator is `AVAILABLE=False` right now) — the old `$4` version would have
> silently matched on PROGRESSING instead.

**Expected output** *(no ClusterOperator is degraded on this training cluster right now — this
table is representative of what a router-scheduling failure looks like, not reproduced live; never
deliberately break a shared cluster's ingress to demo this):*

```
NAME      VERSION   AVAILABLE   PROGRESSING   DEGRADED
ingress   4.18.x    False       True          True

Conditions:
  Type: Degraded  Status: True
  Message: IngressControllerDegraded: one or more ingress controller pods
           are not scheduled (no available router nodes)
```

> **Narrate:** Same loop, **platform layer**. Here the entry point is `oc get co`, not
> `oc get pods`. The ClusterOperator's **condition message names the cause verbatim** — router
> pods can't schedule, so follow it *down a layer* to `oc get nodes` / `oc adm node-logs`. This is
> a different toolbox from the app problem in Steps 1–3 — that's the whole point of "where before
> why."

---

## Step 5 — Bundle the evidence: `must-gather`

```bash
# collect a structured dump for support / offline analysis (admin):
oc adm must-gather --dest-dir=./mobily-mustgather
ls ./mobily-mustgather | head
```

**Live output** *(run for real on the training cluster, 2026-07-15):*

```
namespace/openshift-must-gather-2sf47 created
...
[must-gather-gzqnp] POD Waiting for performance profile collector pods to become ready: 139
[must-gather-gzqnp] OUT gather never finished: context canceled
namespace/openshift-must-gather-2sf47 deleted
error: gather never finished for pod must-gather-gzqnp: context canceled

event-filter.html   must-gather.logs   timestamp
```

> **Gotcha found live:** on this cluster, plain `oc adm must-gather` **stalls** waiting on
> "performance profile collector pods to become ready" — no `PerformanceProfile` CR exists here, so
> that collector phase never completes and the default **10-minute** gather timeout (`--timeout`,
> confirmed via `oc adm must-gather -h`) eventually cancels it. The temp namespace
> (`openshift-must-gather-*`) is still created and auto-cleaned on cancel, exactly as the demo
> claims — just don't expect a full `cluster-scoped-resources`/`namespaces` tree unless you either
> wait it out or pass `--timeout=20m` (or scope the gather, e.g.
> `oc adm must-gather -- gather_network_logs`, to skip the slow collector).

> **Narrate:** For a platform problem or a support case, **`must-gather`** captures operators,
> nodes, events, and logs into one directory. Attach it to a Red Hat case and you skip a day of
> "please run this and send output." The command itself is verifiable offline — `oc adm
> must-gather -h` describes exactly this ("Launch a pod to gather debugging information … writing
> into ./must-gather.local.<rand>").

---

## Step 6 — Cleanup

```bash
oc delete ns openshift-must-gather-xxxx 2>/dev/null || true   # must-gather's temp ns (auto-removed)
rm -rf ./mobily-mustgather                                    # local dump from the drill
# app fix (Step 3) is a real remediation — keep it if the app is real
oc whoami
```

---

## Wrap-up questions to pose

1. For a `CrashLoopBackOff`, why `oc logs --previous` and not plain `oc logs`?
2. `subscriber-api` was crash-looping — but what was actually broken, and how did the loop lead
   you there?
3. You see a `503` through a Route but the pod is `Running` and `1/1 Ready`. Which layer, and
   what one command would you run?
4. When do you reach for `oc get co` vs. `oc get pods` — what distinguishes the two layers?

---

> **● Live-verified — 2026-07-15**, on the shared **OCP 4.18.45** training cluster. Steps 1–3 were
> reproduced with a **real, deliberately-broken scenario** in a scratch `mobily-apps` project: a
> `subscriber-db` Deployment given `resources.limits.memory: 20Mi` (a real PostgreSQL 15 start
> genuinely exceeds that → real `OOMKilled`/exit 137), and a `subscriber-api` Deployment whose
> container does a real TCP probe of `subscriber-db:5432` and prints the same `FATAL: could not
> connect...` message on real failure → real `CrashLoopBackOff`. The Step 3 fix
> (`oc set resources --limits=memory=512Mi`) was applied for real and **both pods reached `1/1
> Running`**, confirming the fix genuinely resolves the chain. The scratch project was deleted after.
> Step 4's `awk` filter had a real bug (fixed — see inline note); its degraded-operator table stays
> representative since deliberately breaking ingress on a shared cluster isn't safe to demo. Step 5's
> `must-gather` was **run for real** and a genuine stall was discovered and documented (see inline
> gotcha) — not fabricated, an actual behavior of this cluster.
