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

**Expected output** *(requires a cluster — representative of OCP 4.18):*

```
NAME                              READY   STATUS             RESTARTS   AGE
subscriber-api-7d9c6b8f4-abcde    0/1     CrashLoopBackOff   6          5m
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

**Expected output** *(requires a cluster — representative):*

```
Events:
  Type     Reason     Age                 From     Message
  ----     ------     ----                ----     -------
  Normal   Pulled     5m                  kubelet  Container image already present
  Warning  BackOff    30s (x12 over 5m)   kubelet  Back-off restarting failed container

# --previous (the container that just died):
... starting subscriber-api on :8080 ...
FATAL: could not connect to subscriber-db:5432: connection refused
exit status 1
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

**Expected output** *(requires a cluster — representative):*

```
NAME                             READY   STATUS      RESTARTS   AGE
subscriber-db-6f5b9c7d8-fghij    0/1     OOMKilled   4          6m

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

---

## Step 4 — Different layer, same loop: a degraded ClusterOperator (admin)

```bash
oc get co | awk 'NR==1 || $4=="False"'      # header + any AVAILABLE=False operators
oc describe co ingress | sed -n '/Conditions:/,+8p'
```

**Expected output** *(requires a cluster + admin — representative):*

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

**Expected output** *(requires a cluster + admin — representative):*

```
[must-gather] OUT Using must-gather plug-in image: registry.redhat.io/.../must-gather
[must-gather] OUT namespace/openshift-must-gather-xxxx created
...
cluster-scoped-resources   event-filter.html   namespaces   timestamp
```

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

> **◐ Partially verified:** the `oc` command **syntax** follows the OCP 4.18 / oc 4.22 references,
> and the diagnostic commands' **help text** (`oc debug -h`, `oc adm must-gather -h`) was
> **confirmed offline with oc 4.22**. The failure output — pod statuses, events, OOMKilled last
> state, degraded-operator conditions, `must-gather` run — **requires a live cluster** (app steps
> as a project user; ClusterOperators and `must-gather` as admin) and was not run at authoring
> (cluster asleep/unreachable). Output is **representative of OpenShift 4.18**; validate live.
