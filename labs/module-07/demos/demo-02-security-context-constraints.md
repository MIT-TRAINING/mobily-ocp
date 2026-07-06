# Demo 2 — Security Context Constraints

> **Scenario:** A Mobily team wants to run a **legacy image that insists on root (UID
> 0)**. On OpenShift it won't start — the default **restricted-v2** SCC forbids root. We
> reproduce the failure, read *which SCC* a well-behaved pod got, then (as admin) grant
> the pod's **ServiceAccount** the `anyuid` SCC so the legacy image runs — while stressing
> that the *right* fix is a rootless image.

| | |
|---|---|
| **Concepts reinforced** | `restricted-v2` default · random non-root UID · the `openshift.io/scc` annotation · `oc adm policy add-scc-to-user` · SCC ladder / least privilege |
| **Maps to** | Guide §7, §8 · Visualization 02 · Exercise 2 |
| **Time** | ~30 minutes |
| **Cluster** | Shared OCP 4.18 — the **SCC grant** (Step 4) needs **cluster-admin** |

---

> **⎈ Kubernetes equivalent:** SCC is OpenShift-specific. Upstream Kubernetes uses **Pod
> Security Admission** (`restricted`/`baseline`/`privileged`) — similar idea, coarser. On
> OpenShift the SCC is the enforcing gate.

## Talking points to open with

- OpenShift is **secure by default**: `restricted-v2` refuses root and assigns a **random
  UID**.
- You don't loosen a pod by editing it — you grant its **ServiceAccount** a broader SCC.
- The *real* fix is almost always a **rootless image** (UBI/sclorg), not a broader SCC.

---

## Step 1 — A well-behaved (rootless) pod, and the SCC it got

```bash
oc create deployment good-app --image=registry.access.redhat.com/ubi9/httpd-24:latest
oc rollout status deploy/good-app
POD=$(oc get pods -l app=good-app -o jsonpath='{.items[0].metadata.name}')
oc get pod "$POD" -o jsonpath='scc={.metadata.annotations.openshift\.io/scc} uid={.spec.containers[0].securityContext}{"\n"}'
oc exec "$POD" -- id
```

**Expected output** *(requires a cluster — representative):*

```
deployment.apps/good-app created
deployment "good-app" successfully rolled out
scc=restricted-v2 uid=
uid=1000750000 gid=0(root) groups=1000750000,0(root)
```

> **Narrate:** The `openshift.io/scc` annotation shows it ran under **restricted-v2**, and
> `id` shows a **random high UID (1000750000)** — not root, not 1001. The UBI image is
> built for arbitrary non-root UIDs, so it's happy. This is the default every app gets.

---

## Step 2 — A root-requiring image is denied

```bash
oc create deployment legacy-app --image=registry.access.redhat.com/ubi9/httpd-24:latest
# force it to demand root to simulate a legacy image:
oc patch deployment legacy-app --type=json -p='[{"op":"add","path":"/spec/template/spec/securityContext","value":{"runAsUser":0}}]'
oc rollout status deploy/legacy-app --timeout=30s
oc get events --field-selector reason=FailedCreate | tail -3
oc describe rs -l app=legacy-app | grep -A2 -i 'unable to validate\|forbidden' | head
```

**Expected output** *(requires a cluster — representative):*

```
deployment.apps/legacy-app created
deployment.apps/legacy-app patched
error: timed out waiting for the condition
... Error creating: pods "legacy-app-..." is forbidden: unable to validate against
    any security context constraint: [ ... spec.containers[0].securityContext.runAsUser:
    Invalid value: 0: must be in the ranges: [1000750000, 1000759999] ]
```

> **Narrate:** `runAsUser: 0` is **rejected** — restricted-v2 only allows the project's
> UID range. The pod never starts. This is OpenShift protecting you from a root
> container, exactly as designed.

---

## Step 3 — Give the app its own ServiceAccount

```bash
oc create serviceaccount legacy-sa
oc set serviceaccount deployment/legacy-app legacy-sa
```

**Expected output** *(requires a cluster — representative):*

```
serviceaccount/legacy-sa created
deployment.apps/legacy-app serviceaccount updated
```

> **Narrate:** We scope the coming SCC grant to a **dedicated SA** — never to `default`
> (which every pod shares). Least privilege starts with a per-app identity.

---

## Step 4 — (Admin) Grant the SA the `anyuid` SCC → the pod runs

```bash
# CLUSTER-ADMIN required:
oc adm policy add-scc-to-user anyuid -z legacy-sa
oc rollout status deploy/legacy-app
POD=$(oc get pods -l app=legacy-app -o jsonpath='{.items[0].metadata.name}')
oc get pod "$POD" -o jsonpath='scc={.metadata.annotations.openshift\.io/scc}{"\n"}'
oc exec "$POD" -- id
```

**Expected output** *(requires cluster-admin — representative):*

```
clusterrole.rbac.authorization.k8s.io/system:openshift:scc:anyuid added: "legacy-sa"
deployment "legacy-app" successfully rolled out
scc=anyuid
uid=0(root) gid=0(root) groups=0(root)
```

> **Narrate:** Now the pod runs under **anyuid** as **root**. Note we changed *no* pod
> field to allow root — we granted the **ServiceAccount** a broader SCC (`-z` = service
> account). Powerful, and to be used sparingly. The *better* fix: rebuild the image
> rootless and stay on restricted-v2.

---

## Step 5 — The SCC ladder

```bash
oc get scc      # least → most privileged
```

**Expected output** *(requires a cluster — representative, abbreviated):*

```
NAME               PRIV    CAPS   ...  RUNASUSER
restricted-v2      false   ...         MustRunAsRange
nonroot-v2         false   ...         MustRunAsNonRoot
hostmount-anyuid   false   ...         RunAsAny
anyuid             false   ...         RunAsAny
privileged         true    ...         RunAsAny
```

> **Narrate:** Pick the **narrowest** SCC that works. `privileged` (host + root + all
> caps) is for node-level agents (CNI, storage, monitoring), never ordinary apps. Grant
> up the ladder only with a concrete reason.

---

## Step 6 — Cleanup

```bash
oc adm policy remove-scc-from-user anyuid -z legacy-sa    # admin
oc delete deployment good-app legacy-app
oc delete serviceaccount legacy-sa
```

**Expected output** *(representative):*

```
clusterrole.rbac.authorization.k8s.io/system:openshift:scc:anyuid removed: "legacy-sa"
deployment.apps "good-app" deleted
deployment.apps "legacy-app" deleted
serviceaccount "legacy-sa" deleted
```

---

## Wrap-up questions to pose

1. What UID did the well-behaved pod run as, and under which SCC?
2. Why was the `runAsUser: 0` pod rejected?
3. To allow root, what did we modify — the pod, or the ServiceAccount's SCC grant?
4. What's the *better* fix than granting `anyuid`, and why?

---

> **◐ Partially verified:** `oc adm policy add-scc-to-user --help` and
> `oc set serviceaccount --help` were confirmed with **oc 4.22** (client-side). The
> cluster steps **require a live OpenShift cluster** (Step 4 needs **cluster-admin**) and
> were not run at authoring time (cluster asleep). Output is **representative of OpenShift
> 4.18**; the `restricted-v2` random-UID assignment and the `runAsUser: 0` rejection are
> real, documented behaviours. Validate live as an admin when the cluster is up.
