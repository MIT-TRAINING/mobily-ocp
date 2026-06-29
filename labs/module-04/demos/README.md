# Module 4 — Guided Demos (Instructor-Led)

These are **instructor-led, narrated walkthroughs**. The instructor runs each step
live against the real **OpenShift 4.18** cluster while explaining *what* each
component is and *why* it matters. Participants watch and follow along, then practice
independently in the [`../exercises`](../exercises).

Module 4 — **"OpenShift Architecture and Product Overview"** — is mostly about
*reading* the platform you'll administer: logging in, exploring nodes (RHCOS + CRI-O),
the Cluster Operators that run the platform, and the Machine API behind the nodes.
From this module on we use the **`oc`** CLI and the **web console** — `oc` is
`kubectl` plus OpenShift verbs, so every `kubectl` command you saw in Modules 2–3
still works. Each demo carries a **⎈ Kubernetes equivalent** note where it helps.

All scenarios use a **telecom domain** framing (subscriber API, tariff catalog, CDR
pipeline, SMS gateway) so the components land in a familiar context. Data and services
are fictional and illustrative.

## Demos in this module

| # | Demo | Concepts reinforced | Telecom scenario | Time |
|---|------|---------------------|------------------|------|
| 1 | [`oc` CLI & the web console](demo-01-oc-and-console-tour.md) | `login` · `whoami` · `version` · Projects · `oc`=`kubectl` · console perspectives | Stand up the **mobily-mod4** project | ~25 min |
| 2 | [Explore nodes — RHCOS & CRI-O](demo-02-explore-nodes-rhcos-crio.md) | node roles · RHCOS OS image · CRI-O runtime · taints/labels · `describe node` | Map the cluster carrying the **CDR pipeline** | ~25 min |
| 3 | [Cluster Operators & the CVO](demo-03-cluster-operators-and-version.md) | `clusterversion` · `clusteroperators` · A/P/D triage · OperatorHub | Pre-release **platform health check** | ~30 min |
| 4 | [The Machine API](demo-04-machine-api.md) | `machinesets` · `machines` · Machine→Node · scale (admin) | Plan **CDR-worker** capacity | ~25 min |

## Conventions

- Commands use **`oc`** — the OpenShift CLI. Everything except `oc login`,
  `oc project`/`new-project`, `oc status`, and `oc adm` is the **identical `kubectl`**
  command; each demo's **⎈ Kubernetes equivalent** note flags this.
- **Permissions matter.** Most of Module 4 is *read-only inspection*, but
  `oc get nodes`, `oc get clusteroperators`, and `oc get machines` are **cluster-scope**
  reads. On the shared cluster the instructor runs them as an admin (or cluster-reader);
  on the free **[Developer Sandbox](https://developers.redhat.com/developer-sandbox)**
  participants are *project members* and cannot read those — they follow the
  instructor's screen for Demos 2–4. Scaling a MachineSet (Demo 4) is **admin-only**.
- Replace placeholders like `<cluster-domain>` / `<node>` / `<machineset>` with your
  own values. **Never type or commit real tokens/passwords** — use the console's
  *Copy login command* token or `$OCP_PASSWORD`.
- Each demo ends with a **Cleanup** section (Demo 1 creates a project; Demos 2–4 are
  read-only and need no cleanup).
- Companion material: the
  [concept guide](../../../guides/module-04-openshift-architecture.md), the interactive
  [visualizations](../index.html), and the [exercises](../exercises/README.md).

## Pre-flight check (run once before Demo 1)

```bash
# Log in via the web console token (top-right user menu → Copy login command), or:
oc login https://api.<cluster-domain>:6443 -u <user> -p "$OCP_PASSWORD"

oc whoami                       # confirm authenticated
oc version                      # client + SERVER (the OCP version)
oc whoami --show-server         # which cluster
```

> **Instructor tip:** keep a second terminal handy and have the **web console** open
> side-by-side — Module 4 lands best when participants see the *same fact* on the CLI
> and in the console (e.g. `oc get clusteroperators` next to **Administration →
> Cluster Settings**). For Demo 4, pre-confirm whether the class cluster exposes the
> Machine API (installer-provisioned infra); on UPI/bare-metal it may be absent — fall
> back to the visualization.

---

> **◐ Partially verified.** `oc` **client-side** commands were run live with **oc
> 4.22**; every command that needs a **live OpenShift cluster** (node/operator/machine
> reads) is labelled **"requires a cluster — output is representative of OpenShift
> 4.18"** and the demo footers say **◐ Partially verified**. No cluster-dependent
> output here is presented as independently verified — run it live to capture your own.
</content>
