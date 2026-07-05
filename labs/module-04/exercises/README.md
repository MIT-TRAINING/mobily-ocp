# Module 4 — Exercises (Hands-On Practice)

These are **participant-driven** tasks. From this module on we work on **OpenShift**
with the **`oc`** CLI (and the web console), then verify with the provided
**validation** commands. Each exercise has a fully worked **solution** at the bottom —
try the tasks first, then check.

Module 4 — **"OpenShift Architecture and Product Overview"** — is mostly about
*reading* a real cluster: its version, nodes, Cluster Operators, and the Machine API.
You'll spend most of your time **inspecting** the platform you'll administer.

## Where to run these

| Target | What you can do | Notes |
|---|---|---|
| **Shared OpenShift 4.18 cluster** (preferred) | Most inspection commands; node/operator/machine reads | You may be a **non-admin** — some `oc adm`/node reads are restricted |
| **[Developer Sandbox](https://developers.redhat.com/developer-sandbox)** (free fallback) | Projects, `oc` basics, OperatorHub browsing | You are a **project member**, *not* cluster-admin → `oc get nodes`, `co`, `machines` are restricted; those steps are read-as-instructor-demo |

> **`oc` = `kubectl` + OpenShift verbs.** Every `kubectl` command from Modules 2–3 works
> as `oc`. The OpenShift-only verbs here are `oc login`, `oc project`, `oc new-project`,
> `oc status`, and `oc adm`.

## Exercises in this module

| # | Exercise | What you'll practice | Telecom scenario | Difficulty |
|---|----------|----------------------|------------------|------------|
| 1 | [`oc` CLI essentials](exercise-01-oc-cli-essentials.md) | `login`, `whoami`, projects, `version`, `explain`, `oc` vs `kubectl` | Stand up the **mobily-mod4** project | ⭐ Beginner |
| 2 | [Explore cluster architecture](exercise-02-explore-cluster-architecture.md) | `get nodes`, roles, RHCOS image, CRI-O version, `describe node` | Map the cluster carrying the **CDR pipeline** | ⭐⭐ Intermediate |
| 3 | [Cluster Operators & version](exercise-03-cluster-operators.md) | `clusterversion`, `clusteroperators`, DEGRADED triage, OperatorHub | Triage a **platform health** check | ⭐⭐ Intermediate |
| 4 | [Machine API + console capstone](exercise-04-machine-api-and-console-capstone.md) | `machines`, `machinesets`, console tour, tie it all together | Plan **CDR-worker** capacity | ⭐⭐⭐ Advanced |

## Before you start

```bash
# Log in (token from the web console: top-right → Copy login command), or:
oc login https://api.<cluster-domain>:6443 -u <user> -p '<your-password>'

oc whoami                 # confirm you're authenticated
oc version                # client + server — note the SERVER (OCP) version
oc new-project mobily-mod4 --display-name="Mobily Module 4" 2>/dev/null \
  || oc project mobily-mod4
```

- Replace placeholders (`<cluster-domain>`, `<user>`, `<node>`, `<machineset>`) with
  your own values. **Never commit real tokens or passwords** — use `$OCP_PASSWORD` or
  the console's *Copy login command*.
- On the **Developer Sandbox** you can't read nodes/operators/machines (not
  cluster-admin). Where an exercise needs that, follow along with your instructor's
  cluster output — the *concepts* are what matter for this module.
- Cleanup is trivial: `oc delete project mobily-mod4` removes everything you created.

## How to self-assess

Each exercise's **Validation** section gives commands whose output confirms success.
If your output matches the *shape* shown, you've completed the task. Stuck? The
**Solution** walks through one correct approach.

Companion material: the guided [demos](../demos/README.md) (instructor-led), the
interactive [visualizations](../index.html), and the
[concept guide](../../../guides/module-04-openshift-architecture.md).

---

> **◐ Partially verified.** `oc` **client-side** commands (`oc version --client`,
> `oc help`, `oc login --help`, `oc options`) were run live with **oc 4.22**. Commands
> that require a **live OpenShift cluster** (node/operator/machine reads) are labelled
> **"requires a cluster — output is representative of OpenShift 4.18"**; run them on the
> shared cluster or Sandbox to see your own values. No output here is fabricated as
> "verified" without a real run.
