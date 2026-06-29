# Demo 1 — `oc` CLI & the Web Console

> **Scenario:** It's the team's first session on the Mobily OpenShift cluster. Before
> anyone deploys a thing, we establish the two front doors every admin lives in — the
> **`oc`** CLI and the **web console** — log in, learn *who* we are and *what version*
> the cluster runs, carve out a **Project**, and prove the single most reassuring fact
> in this course: **`oc` is just `kubectl` with OpenShift superpowers.**

| | |
|---|---|
| **Concepts reinforced** | `oc login` · `whoami` · `oc version` (two version numbers) · Projects vs Namespaces · `oc`=`kubectl` · `oc explain` · console perspectives |
| **Maps to** | Guide §11 · Visualization 01 · Exercise 1 |
| **Time** | ~25 minutes |
| **Cluster** | Shared OCP 4.18 (or Developer Sandbox) |

---

> **⎈ Kubernetes equivalent:** `oc login`, `oc new-project`, `oc project`, `oc status`
> are **OpenShift-only**. `get`, `describe`, `explain`, `api-resources`, `logs`, `exec`
> are the **identical `kubectl`** commands — `oc` ships them under one binary with
> OpenShift auth wired in. A **Project** is a Namespace plus self-service + quotas.

## Talking points to open with

- OpenShift has **one API**; the console and `oc` are two clients of it. Use the
  console to *discover*, `oc` to *automate*.
- You **log in**, you don't hand-edit a kubeconfig. `oc login` gets you a token and
  writes the context for you.
- There are **two** version numbers — the OpenShift version (4.18.x) and the
  Kubernetes it embeds (1.31.x). Quote the **OpenShift** one to Red Hat.

---

## Step 1 — Confirm the client (this part is real, no cluster needed)

```bash
oc version --client
```

**Expected output:**

```
Client Version: 4.22.0
Kustomize Version: v5.7.1
```

> **Narrate:** The `oc` binary bundles `kustomize` — that's why two lines print. This
> is the *client* only; next we add `--`-nothing and let it reach the cluster.

---

## Step 2 — Log in and identify yourself

Use the console's **Copy login command** token (top-right user menu) — it avoids
putting a password in shell history:

```bash
oc login --token=<sha256~…> --server=https://api.<cluster-domain>:6443
#   or: oc login https://api.<cluster-domain>:6443 -u <user> -p "$OCP_PASSWORD"
oc whoami
oc whoami --show-server
```

**Expected output** *(requires a cluster — representative):*

```
Logged into "https://api.ocp4.example.com:6443" as "developer" using the token provided.

You have one project on this server: "default"
Using project "default".

developer
https://api.ocp4.example.com:6443
```

> **Narrate:** `oc login` authenticated us against the cluster's **OAuth server**
> (one of the Cluster Operators we'll meet in Demo 3) and saved a context. `oc whoami`
> answers "who am I"; `--show-server` answers "which cluster." Two questions you'll ask
> a hundred times when juggling clusters.

---

## Step 3 — The two version numbers

```bash
oc version
```

**Expected output** *(requires a cluster — representative):*

```
Client Version: 4.22.0
Kustomize Version: v5.7.1
Server Version: 4.18.20
Kubernetes Version: v1.31.7
```

> **Narrate:** **Server Version 4.18.20** is the OpenShift product version — the one
> that maps to docs, errata, and support cases. **Kubernetes Version v1.31.7** is the
> upstream engine OpenShift 4.18 *embeds*. Same cluster, two numbers, different
> audiences.

---

## Step 4 — Create a Project to work in

```bash
oc new-project mobily-mod4 --display-name="Mobily Module 4"
oc project
```

**Expected output** *(requires a cluster — representative):*

```
Now using project "mobily-mod4" on server "https://api.ocp4.example.com:6443".

Using project "mobily-mod4" on server "https://api.ocp4.example.com:6443".
```

> **Narrate:** `oc new-project` both *created* the Project and *switched* us into it —
> a convenience plain Kubernetes doesn't have (`kubectl create namespace` doesn't
> switch context). A Project is a Namespace plus OpenShift self-service, quotas, and
> annotations. Everything we create now lands here, isolated from other tenants.

---

## Step 5 — Prove `oc` *is* `kubectl`

```bash
oc get pods
kubectl get pods
```

**Expected output** *(requires a cluster — representative):*

```
No resources found in mobily-mod4 namespace.
No resources found in mobily-mod4 namespace.
```

> **Narrate:** Identical — because both read the *same kubeconfig* and hit the *same
> API*. Everything you learned in Modules 2–3 transfers byte-for-byte. `oc` only
> *adds*; it never takes Kubernetes away.

---

## Step 6 — Read field docs for an OpenShift-only object

```bash
oc explain route.spec | head -8
```

**Expected output** *(requires a cluster — representative):*

```
GROUP:      route.openshift.io
KIND:       Route
VERSION:    v1

FIELDS:
  host  <string>
    host is an alias/DNS that points to the service. Optional. If not specified a
    host name is generated...
```

> **Narrate:** `oc explain` (a `kubectl` command) gives field-level docs for *any*
> kind — including OpenShift-only kinds like **Route** (the `route.openshift.io` API
> group). When you forget a field, `oc explain` beats a web search. Routes themselves
> arrive properly in Module 6.

---

## Step 7 — The web console (instructor screen-share)

Open the console URL (`oc whoami --show-server` → swap `api.` for `console-openshift-console.apps.`),
then tour:

- **Top-left perspective switch** — **Administrator** vs **Developer**.
- **Developer → Topology** — apps as a visual graph (empty for now).
- **Administrator → Home → Overview** — cluster health at a glance.
- **Top-right user menu → Copy login command** — where the Step 2 token came from.

> **Narrate:** Same API, friendlier face. The **Administrator** perspective is your
> home for the rest of this module (nodes, operators, cluster settings); the
> **Developer** perspective is where app teams live. Note the console is itself served
> by a Cluster Operator — which is why "the console is down" is a *platform* question
> (Demo 3).

---

## Step 8 — Cleanup

```bash
oc delete project mobily-mod4
```

**Expected output** *(requires a cluster — representative):*

```
project.project.openshift.io "mobily-mod4" deleted
```

> **Narrate:** Deleting the Project cascades — every object inside goes with it. That
> per-Project blast radius is exactly what makes Projects the unit of multi-tenancy on
> a shared Mobily cluster. *(Keep the project if you'll continue to the exercises.)*

---

## Wrap-up questions to pose

1. Why does `oc version` print **two** version numbers, and which do you quote to
   Red Hat support?
2. `oc get pods` and `kubectl get pods` returned the same thing. Why — what do they
   share?
3. What does `oc new-project` do that `kubectl create namespace` does not?
4. Name three things that are **OpenShift-only** verbs/kinds and three that are pure
   Kubernetes.

---

> **◐ Partially verified:** oc **4.22** (client) · 2026-06-29 — Step 1
> (`oc version --client`) and the `oc explain` / `oc help` *syntax* were run live.
> Steps 2–8 require a **live OpenShift cluster** and are **representative of OpenShift
> 4.18**; run them on the shared cluster/Sandbox for your own values. No
> cluster-dependent output is presented as independently verified.
</content>
