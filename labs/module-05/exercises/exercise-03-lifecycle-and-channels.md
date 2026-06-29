# Exercise 3 — Cluster Lifecycle & Update Channels

> **Scenario:** A CVE advisory means Mobily must plan a move to **4.18.21**. You won't
> upgrade the shared class cluster — but you *will* produce the **upgrade plan**: confirm
> the cluster is upgrade-ready, read the channel and recommended targets, and write the
> exact sequence (with the right gates) you'd hand to change-management.

| | |
|---|---|
| **Practice** | `oc adm upgrade` (report) · update channels · pre/post health gates · upgrade sequencing |
| **Maps to** | Guide §6 · Visualization 04 (upgrade) · Demo 3 |
| **Difficulty** | ⭐⭐ Intermediate · ~25 min · **report-only** (no real upgrade) |

> ⚠️ **Do not run a real upgrade** on the shared cluster. Everything here is
> report-only (`oc adm upgrade` with no `--to`, channel reads). Setting the channel
> needs admin; treat it as confirm-only.

---

## Tasks

1. Confirm the cluster is **upgrade-ready** with the three-command health check (from
   Exercise 1).
2. Show the **current channel** and the **available channels**.
3. List the **recommended update targets** and the **release image** each maps to.
4. Explain, in your own words, the four channels (**candidate / fast / stable / eus**)
   and which Mobily production should be on.
5. Write the **ordered upgrade procedure** to reach **4.18.21**, including the
   **pre-flight gate** and the **post-upgrade verification** (same three commands).
6. Explain **why apps stay up** during the worker-reboot phase.

> **Hint (Task 2):** `oc get clusterversion -o jsonpath='{.spec.channel}{"\n"}'` for the
> current channel; `oc adm upgrade` lists the available ones.

---

## Validation

```bash
# Task 1 — ready?
oc get clusterversion

# Task 2-3 — channel + recommended targets (report-only)
oc adm upgrade

# Task 2 (precise) — current channel
oc get clusterversion -o jsonpath='{.spec.channel}{"\n"}'
```

---

## Reflection

- Why is `stable-4.18` the right channel for production, and what's the risk of `fast`
  or `candidate`?
- Why are the **pre-flight gate** and the **post-upgrade check** the *same* three
  commands?
- What does the **CVO** do, and what does the **MCO** do, during the upgrade?

---

<details>
<summary><strong>✅ Solution</strong> (try the tasks first)</summary>

```bash
# 1. Upgrade-ready health gate
oc get clusterversion        # AVAILABLE=True, PROGRESSING=False
oc get co -o jsonpath='{range .items[?(@.status.conditions[?(@.type=="Degraded")].status=="True")]}{.metadata.name}{"\n"}{end}'   # empty
oc get nodes                 # all Ready

# 2-3. Channel + targets (report-only)
oc adm upgrade
oc get clusterversion -o jsonpath='channel={.spec.channel}{"\n"}'

# 4. Channels:
#    candidate = earliest, may be withdrawn -> test only
#    fast      = supported on release        -> early adopters / non-critical
#    stable    = promoted from fast after field data -> PRODUCTION (Mobily)
#    eus       = Extended Update Support, EUS->EUS hops -> fewest upgrades

# 5. Ordered procedure to 4.18.21 (run on a real maintenance window, NOT in class):
#    a) GATE: health green (the three commands above)
#    b) oc adm upgrade channel stable-4.18          # confirm channel
#    c) oc adm upgrade                              # confirm 4.18.21 is recommended
#    d) oc adm upgrade --to=4.18.21                 # start (CVO takes over)
#    e) watch oc get clusterversion                 # PROGRESSING=True until done
#       oc get co        # each operator -> 4.18.21 in dependency order
#       oc get mcp       # worker pool UPDATING as MCO reboots nodes (drained)
#    f) VERIFY: same three commands, now green at 4.18.21

# 6. Apps stay up because worker reboots are DRAINED one at a time (maxUnavailable),
#    so multi-replica Deployments always keep replicas on other nodes.
```

**Representative output** *(requires a cluster — OCP 4.18, report-only):*

```
Cluster version is 4.18.20

Channel: stable-4.18 (available channels: candidate-4.18, eus-4.18, fast-4.18, stable-4.18)

Recommended updates:
  VERSION   IMAGE
  4.18.21   quay.io/openshift-release-dev/ocp-release@sha256:...
  4.18.22   quay.io/openshift-release-dev/ocp-release@sha256:...

channel=stable-4.18
```

**Key point:** an OpenShift upgrade is **one supervised command** because the **CVO**
moves every Cluster Operator and the **MCO** rolls RHCOS — OS + runtime + Kubernetes +
platform as one tested unit. *You* own the gates: green before, the right channel, the
right target, green after.
</details>

---

> **◐ Partially verified:** all commands **require a live OpenShift cluster**; the real
> `--to=` upgrade is deliberately **not** part of this exercise. Output is
> **representative of OpenShift 4.18** — run the report-only forms on the shared cluster
> for real channel/target values. Nothing is presented as independently verified.
</content>
