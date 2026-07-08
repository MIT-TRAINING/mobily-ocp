# Exercise 2 — Diagnose a Broken App

> **Scenario:** Mobily's `subscriber-api` is in `CrashLoopBackOff` and customers can't look up
> balances. No guessing — you'll run the **troubleshooting loop**: read the status (which layer?),
> let **events** narrate, read the **previous** logs, follow the failure **downstream** to the real
> root cause, apply the **smallest** fix, and confirm. Then you'll prove you can tell an
> **app**-layer problem from a **platform**-layer one.

| | |
|---|---|
| **Practice** | pod status → `describe`/events → `oc logs --previous` · dependency chain · app vs. platform (`oc get co`) · `oc debug` · `must-gather` |
| **Maps to** | Guide §7–§10 · Visualization 02 · Demo 2 |
| **Difficulty** | ⭐⭐ Intermediate · ~20 min · app steps are project-user; `oc get co`/`must-gather` need admin |

> ⚠️ Reading **your** pods/events/logs is project-user. Reading **ClusterOperators**/nodes and
> running **`must-gather`** is cluster-admin — pair with your instructor for Task 5.

---

## Tasks

1. Get the pods in `mobily-apps`. Record `subscriber-api`'s exact **status string** — and say
   which **layer** (app vs. platform) that status points to, and why.
2. Use **events** (`oc describe`) and **`oc logs --previous`** to find what the crashing container
   said last. It names a dependency — which one?
3. Follow it **downstream**: inspect that dependency's pod. What is its `Last State` / reason?
   That's your real root cause.
4. Apply the **smallest** fix (change one thing) and confirm `subscriber-api` recovers.
5. **Different layer, same loop:** run `oc get co`. If any operator is `Degraded`, read its
   condition message and say what layer you'd descend to next. (Then note when you'd run
   `must-gather`.)

> **Hint (Task 1):** `CrashLoopBackOff` = starts then exits → **application/runtime** layer, not
> scheduling or image pull.

> **Hint (Task 2):** for a crash-loop, plain `oc logs` may be empty — use `--previous`.

> **Hint (Task 3):** the api's log names a host:port; that host is the pod to inspect next.

---

## Validation

```bash
# 1. status string:
oc get pods -n mobily-apps                          # subscriber-api ... CrashLoopBackOff

# 2. why it crashed (previous container):
oc describe pod -n mobily-apps -l app=subscriber-api | sed -n '/Events:/,$p'
oc logs -n mobily-apps -l app=subscriber-api --previous --tail=8

# 3. the real culprit downstream:
oc get pods -n mobily-apps -l app=subscriber-db     # OOMKilled?
oc describe pod -n mobily-apps -l app=subscriber-db | grep -A3 'Last State'

# 4. smallest fix + confirm:
oc set resources deploy/subscriber-db -n mobily-apps --limits=memory=512Mi
oc get pods -n mobily-apps                           # both Running, subscriber-api 1/1

# 5. platform layer:
oc get co | awk 'NR==1 || $4=="False"'
```

Expected: `subscriber-api` `CrashLoopBackOff` → logs show `connection refused: subscriber-db` →
`subscriber-db` `OOMKilled` (exit 137) → after raising its memory limit both pods `Running`.

---

## Reflection

- Why does the pod's **status string** tell you the *layer* before you read any log?
- `subscriber-api` was crash-looping — but it was never the broken component. How did the loop lead
  you to the real cause without touching it?
- You see a `503` through a Route but the pod is `1/1 Ready`. Which layer, and what single command
  reveals it? (Hint: endpoints.)

---

<details>
<summary><strong>✅ Solution</strong> (try the tasks first)</summary>

```bash
# 1. status = the class of problem (application/runtime layer)
oc get pods -n mobily-apps
#   subscriber-api-...   0/1   CrashLoopBackOff   6   5m   <- starts then exits

# 2. events + previous logs name the dependency
oc describe pod -n mobily-apps -l app=subscriber-api | sed -n '/Events:/,$p'
#   Warning BackOff  Back-off restarting failed container
oc logs -n mobily-apps -l app=subscriber-api --previous --tail=8
#   FATAL: could not connect to subscriber-db:5432: connection refused

# 3. follow it downstream — the REAL root cause
oc get pods -n mobily-apps -l app=subscriber-db
#   subscriber-db-...   0/1   OOMKilled   4   6m
oc describe pod -n mobily-apps -l app=subscriber-db | grep -A3 'Last State'
#   Reason: OOMKilled   Exit Code: 137

# 4. smallest fix (the db, not the api) + confirm
oc set resources deploy/subscriber-db -n mobily-apps --limits=memory=512Mi
oc get pods -n mobily-apps                 # subscriber-db Running; subscriber-api 1/1 Ready

# 5. platform layer — same loop, different entry point
oc get co | awk 'NR==1 || $4=="False"'     # any AVAILABLE=False operator
oc describe co <name> | sed -n '/Conditions:/,+8p'   # message names the cause -> descend a layer
#   for a platform problem or a support case: oc adm must-gather --dest-dir=./mg
```

**Why:** the **status string is a diagnosis** — `CrashLoopBackOff` is runtime, so you go straight
to logs (with `--previous`, because the live container is too young to have logged). The api's error
points **downstream**: the bug is `subscriber-db` being **OOMKilled**, not the api. Fix the smallest
thing — raise the db's memory — and the api recovers untouched. **`oc get co`** is the *platform*
entry point (a different toolbox); a degraded operator's **condition message** names the cause and
tells you which layer to descend to. Reach for **`must-gather`** when it's platform-level or headed
to a support case. Events tell you *where*; logs tell you *why*.
</details>

---

> **◐ Partially verified:** the `oc` command **syntax** follows the OCP 4.18 / oc 4.22 references,
> and diagnostic help text (`oc debug -h`, `oc adm must-gather -h`) was **confirmed offline with oc
> 4.22**. The failure output — statuses, events, `OOMKilled` last state, degraded-operator
> conditions — **requires a live cluster** (app steps as a project user; ClusterOperators/
> `must-gather` as admin) and was not run at authoring (cluster asleep/unreachable). Output is
> **representative of OpenShift 4.18**; validate live when the cluster is up.
