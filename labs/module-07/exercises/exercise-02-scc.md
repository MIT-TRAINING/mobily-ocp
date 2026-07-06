# Exercise 2 — Security Context Constraints

> **Scenario:** Find out *which* SCC your pods run under and *what UID* they get, reproduce
> the classic **root-required** denial, and (with admin help) allow it the correct way — by
> granting a **ServiceAccount** a broader SCC.

| | |
|---|---|
| **Practice** | read `openshift.io/scc`, inspect the assigned UID, interpret an SCC denial, `oc adm policy add-scc-to-user` (admin), the SCC ladder |
| **Maps to** | Guide §7, §8 · Visualization 02 · Demo 2 |
| **Difficulty** | ⭐⭐ Intermediate · ~25 min · **SCC grant needs cluster-admin** |

---

## Tasks

1. Deploy a rootless app (`ubi9/httpd-24`); find **which SCC** admitted it and **what UID**
   it runs as.
2. Force a second deployment to require **`runAsUser: 0`** and observe it **fail to
   schedule**; read the exact error.
3. Give the failing app its **own ServiceAccount**.
4. **(admin)** Grant that SA the **`anyuid`** SCC and confirm the pod now runs (as root,
   under `anyuid`). *If you're not admin*, explain the command and predict the result.
5. List the SCC ladder and state which SCC a normal web app should use, and why
   `privileged` is reserved.

> **Hint (Task 1):** `oc get pod <p> -o jsonpath='{.metadata.annotations.openshift\.io/scc}'` and `oc exec <p> -- id`.

> **Hint (Task 4):** `oc adm policy add-scc-to-user anyuid -z <sa>` (`-z` = service account).

---

## Validation

```bash
# Task 1 — SCC + UID of the good pod
P=$(oc get pods -l app=good-app -o jsonpath='{.items[0].metadata.name}')
oc get pod "$P" -o jsonpath='{.metadata.annotations.openshift\.io/scc}{"\n"}'   # restricted-v2
oc exec "$P" -- id                                                             # random high UID

# Task 2 — the denial
oc describe rs -l app=legacy-app | grep -i 'unable to validate\|forbidden' | head

# Task 4 — after the grant, the pod runs under anyuid
P2=$(oc get pods -l app=legacy-app -o jsonpath='{.items[0].metadata.name}')
oc get pod "$P2" -o jsonpath='{.metadata.annotations.openshift\.io/scc}{"\n"}'  # anyuid
```

---

## Reflection

- What UID did the rootless app get, and why not 0 or a fixed number?
- To allow the root image, did you change the **pod** or the **ServiceAccount**? Why does
  that matter?
- What's a *better* fix than granting `anyuid`?

---

<details>
<summary><strong>✅ Solution</strong> (try the tasks first)</summary>

```bash
# 1. Rootless app — inspect SCC + UID
oc create deployment good-app --image=registry.access.redhat.com/ubi9/httpd-24:latest
oc rollout status deploy/good-app
P=$(oc get pods -l app=good-app -o jsonpath='{.items[0].metadata.name}')
oc get pod "$P" -o jsonpath='scc={.metadata.annotations.openshift\.io/scc}{"\n"}'   # restricted-v2
oc exec "$P" -- id                                                                  # uid=100075xxxx

# 2. Force root → denial
oc create deployment legacy-app --image=registry.access.redhat.com/ubi9/httpd-24:latest
oc patch deployment legacy-app --type=json \
  -p='[{"op":"add","path":"/spec/template/spec/securityContext","value":{"runAsUser":0}}]'
oc rollout status deploy/legacy-app --timeout=30s || true
oc describe rs -l app=legacy-app | grep -i 'unable to validate\|forbidden' | head

# 3. Dedicated SA
oc create serviceaccount legacy-sa
oc set serviceaccount deployment/legacy-app legacy-sa

# 4. (admin) grant anyuid → runs as root
oc adm policy add-scc-to-user anyuid -z legacy-sa
oc rollout status deploy/legacy-app
P2=$(oc get pods -l app=legacy-app -o jsonpath='{.items[0].metadata.name}')
oc get pod "$P2" -o jsonpath='scc={.metadata.annotations.openshift\.io/scc}{"\n"}'  # anyuid
oc exec "$P2" -- id                                                                 # uid=0(root)

# 5. Ladder
oc get scc

# Cleanup
oc adm policy remove-scc-from-user anyuid -z legacy-sa   # admin
oc delete deployment good-app legacy-app ; oc delete sa legacy-sa
```

**Representative output** *(requires a cluster; Task 4 needs admin — OCP 4.18):*

```
scc=restricted-v2
uid=1000750000 gid=0(root) groups=1000750000,0(root)

... pods "legacy-app-..." is forbidden: unable to validate against any security
    context constraint: ... runAsUser: Invalid value: 0: must be in the ranges: [1000750000, ...]

scc=anyuid
uid=0(root) ...
```

**Key point:** OpenShift is secure by default — `restricted-v2` assigns a **random
non-root UID** and rejects `runAsUser: 0`. You loosen it by granting the **ServiceAccount**
a broader SCC (`add-scc-to-user anyuid -z sa`), never by editing the pod. The best fix is a
**rootless image** so you can stay on `restricted-v2`; reserve `privileged` for node agents.
</details>

---

> **◐ Partially verified:** `oc adm policy add-scc-to-user --help` confirmed with **oc
> 4.22**; cluster steps **require a live OpenShift cluster** (Task 4 needs **cluster-admin**)
> and were not run at authoring (cluster asleep). Output is **representative of OpenShift
> 4.18**; the random-UID assignment and `runAsUser: 0` rejection are real, documented
> behaviours. Validate live (grant as admin) when the cluster is up.
