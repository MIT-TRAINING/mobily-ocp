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
oc get co | awk 'NR==1 || $3=="False"'
```

> **Fixed a bug:** the original filter used `$4` (that's the **PROGRESSING** column, not
> **AVAILABLE**). `oc get co`'s columns are `NAME VERSION AVAILABLE PROGRESSING DEGRADED SINCE
> MESSAGE` — AVAILABLE is `$3`.

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
oc get co | awk 'NR==1 || $3=="False"'     # any AVAILABLE=False operator (AVAILABLE is column 3)
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

> **● Mostly live-verified — 2026-07-16**, on the shared **OCP 4.18.45** training cluster, using a
> real deliberately-broken `subscriber-api`/`subscriber-db` pair in a scratch `mobily-apps` project
> (a TCP-probing `subscriber-api` container and a `subscriber-db` given a tight memory limit).
> Tasks 1–2 are **fully real**: the `subscriber-api` container genuinely crash-loops on a real
> `connection refused`, with real events/`BackOff` output captured live. **Task 3's `OOMKilled`
> state is confirmed real** — this exact scenario (image `quay.io/sclorg/postgresql-15-c9s` at a
> 20Mi memory limit) produced a real `OOMKilled`/exit 137 in this course's companion Demo 2, run on
> this same cluster the same week. Re-running it for this exercise showed **real run-to-run
> variance**: at 20Mi and 14Mi the db pod instead sat at `1/1 Ready` while genuinely refusing
> connections and producing zero log output — a legitimate, separate gotcha (no readiness probe
> means `Ready` only reflects "container process started," not "app is actually serving"), worth
> knowing but not the specific failure this exercise targets. If you don't get a clean `OOMKilled`
> on the first try, lower the memory limit further or retry — it depends on node memory pressure at
> the time. Task 4's fix and Task 5's `awk` bug (fixed — see inline note) were verified live. The
> scratch project was deleted after.
