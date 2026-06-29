# Exercise 1 — `oc` CLI Essentials

> **Scenario:** It's your first hour on the Mobily OpenShift cluster. Before you can
> deploy anything you need to **log in**, learn **who you are** and **what version**
> the cluster runs, carve out a **project** to work in, and confirm the muscle memory
> that *`oc` is `kubectl` plus OpenShift verbs*.

| | |
|---|---|
| **Practice** | `oc login`, `oc whoami`, `oc version`, `oc new-project`/`project`, `oc status`, `oc explain`, `oc` vs `kubectl` |
| **Maps to** | Guide §11 · Visualization 01 · Demo 1 |
| **Difficulty** | ⭐ Beginner · ~20 min · works on Sandbox |

---

## Tasks

1. **Log in** to the cluster (`oc login …`, or paste the *Copy login command* token
   from the web console). Confirm with **`oc whoami`** and find out **which server**
   you're talking to.
2. Show the **client and server versions** in one command. Note that the *server*
   version is the **OpenShift (OCP)** version of the cluster.
3. Create a **project** named **`mobily-mod4`** and confirm it became your **active**
   project.
4. Run **`oc status`** in the empty project and read what it tells you.
5. Prove the **`oc` = `kubectl`** relationship: run the *same* read command as both
   `oc` and `kubectl` and confirm identical output.
6. Use **`oc explain`** to read the field docs for a **Route** (an OpenShift-only
   object) — e.g. `oc explain route.spec`.
7. List the **command groups** `oc` offers (`oc help`) and identify which verbs are
   **OpenShift-only** (not in `kubectl`).

> **Hint (Task 1):** the web console's top-right user menu → **Copy login command**
> gives you a ready-to-paste `oc login --token=… --server=…` (no password in shell
> history). `oc whoami --show-server` prints the API URL.

> **Hint (Task 5):** if `oc` is configured, `kubectl` uses the *same* kubeconfig — so
> `oc get pods` and `kubectl get pods` hit the same cluster/namespace.

---

## Validation

```bash
# Task 1 — you are authenticated, and you can see your server
oc whoami                       # -> your username
oc whoami --show-server         # -> https://api.<cluster-domain>:6443

# Task 2 — both versions; SERVER line is the OCP version
oc version

# Task 3 — mobily-mod4 is the active project (marked with *)
oc projects | grep mobily-mod4

# Task 6 — field docs for a Route render
oc explain route.spec | head -5
```

**Expected shape (server values vary by cluster):**

```
Client Version: 4.22.0
Kustomize Version: v5.7.1
Server Version: 4.18.x
Kubernetes Version: v1.31.x
```

---

## Reflection

- Why is it safer to log in with a **token** (Copy login command) than with
  `-u/-p` on the command line?
- The *Server Version* and *Kubernetes Version* differ (4.18.x vs 1.31.x). Why are
  there **two** version numbers, and which one do Red Hat docs/support use?
- Which of these are OpenShift-only and which are plain Kubernetes: `login`,
  `new-project`, `get`, `status`, `explain`, `adm`?

---

<details>
<summary><strong>✅ Solution</strong> (try the tasks first)</summary>

```bash
# 1. Log in (token form avoids passwords in history) and identify yourself
oc login --token=<sha256~…> --server=https://api.<cluster-domain>:6443
#   or: oc login https://api.<cluster-domain>:6443 -u <user> -p "$OCP_PASSWORD"
oc whoami                       # -> developer  (your username)
oc whoami --show-server         # -> https://api.<cluster-domain>:6443

# 2. Versions — the Server line is the OpenShift version
oc version

# 3. Create and switch to a project (new-project switches you automatically)
oc new-project mobily-mod4 --display-name="Mobily Module 4"
oc project                      # -> Using project "mobily-mod4" ...
oc projects | grep '*'          # the active project is starred

# 4. Status of the (empty) project
oc status                       # -> "In project mobily-mod4 ... no resources found"

# 5. oc IS kubectl — same kubeconfig, same result
oc get pods
kubectl get pods                # identical (both: "No resources found in mobily-mod4 namespace.")

# 6. Field docs for an OpenShift-only object
oc explain route.spec | head -15

# 7. Command groups; OpenShift-only verbs include login/new-project/new-app/status/project(s)/adm
oc help
```

**Representative output** *(requires a cluster for the server lines; client lines are real from oc 4.22):*

```
$ oc version --client
Client Version: 4.22.0
Kustomize Version: v5.7.1

$ oc version                      # on a live 4.18 cluster
Client Version: 4.22.0
Kustomize Version: v5.7.1
Server Version: 4.18.20
Kubernetes Version: v1.31.7

$ oc whoami
developer
$ oc whoami --show-server
https://api.ocp4.example.com:6443

$ oc new-project mobily-mod4 --display-name="Mobily Module 4"
Now using project "mobily-mod4" on server "https://api.ocp4.example.com:6443".

$ oc get pods   ;   kubectl get pods
No resources found in mobily-mod4 namespace.
No resources found in mobily-mod4 namespace.

$ oc explain route.spec | head -6
GROUP:      route.openshift.io
KIND:       Route
VERSION:    v1
FIELDS:
  host  <string>
    host is an alias/DNS that points to the service ...
```

**Key point:** `oc` and `kubectl` share one kubeconfig and one API — the *only*
difference is `oc` adds OpenShift verbs (`login`, `new-project`, `new-app`, `status`,
`project`, `adm`) and OpenShift kinds (`Route`, `Project`, `BuildConfig`, `ImageStream`).
The two **version numbers** exist because OpenShift 4.18 *embeds* Kubernetes 1.31 —
quote the **OCP** version to Red Hat support.

```bash
# Cleanup (or keep mobily-mod4 for later exercises)
oc delete project mobily-mod4
```
</details>

---

> **◐ Partially verified:** oc **4.22** (client) · 2026-06-29 — `oc version --client`,
> `oc help`, `oc options`, `oc login --help` were run **live**. Lines requiring a live
> OpenShift cluster (`Server Version`, `whoami`, `new-project`, `explain route`) are
> **representative of OpenShift 4.18**; run them on the shared cluster/Sandbox for your
> own values. Nothing is fabricated as fully verified.
</content>
