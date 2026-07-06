# Demo 1 — Custom RBAC & Least Privilege

> **Scenario:** Mobily's **billing** project needs scoped access: developers who can
> deploy, a read-only auditor, and a bespoke "CDR log reader" that can read pod logs and
> nothing else. We author a **custom Role**, bind default ClusterRoles per-project, and
> **prove** every boundary with `oc auth can-i --as`.

| | |
|---|---|
| **Concepts reinforced** | custom Role rule (apiGroups/resources/verbs) · `oc create role/rolebinding` · default view/edit/admin · `can-i`/`who-can`/`--as` |
| **Maps to** | Guide §3, §4, §6, §7 · Visualization 01 · Exercise 1 |
| **Time** | ~30 minutes |
| **Cluster** | Shared OCP 4.18 — a normal project user can do all of this in their own project |

---

> **⎈ Kubernetes equivalent:** Role/RoleBinding/ClusterRole and `oc auth can-i` are pure
> Kubernetes. `oc adm policy` and `oc adm policy who-can` are OpenShift convenience verbs.

## Talking points to open with

- A Role is a set of **rules** (apiGroups × resources × verbs); rules are **additive, no
  deny**.
- Prefer default **view/edit/admin** bound per-project; write a **custom Role** only for a
  real need.
- Always **prove** access with `oc auth can-i --as` — never assume.

---

## Step 1 — Author a custom Role (CDR log reader)

```bash
# read-only on pods + pod logs, nothing else
oc create role cdr-log-reader \
  --verb=get,list,watch --resource=pods,pods/log -n mod8-demos
oc get role cdr-log-reader -n mod8-demos -o yaml | sed -n '/rules:/,$p'
```

**Expected output** *(requires a cluster — representative of OCP 4.18):*

```
role.rbac.authorization.k8s.io/cdr-log-reader created
rules:
- apiGroups: [""]
  resources: ["pods","pods/log"]
  verbs: ["get","list","watch"]
```

> **Narrate:** `apiGroups: [""]` is the **core** group. The rule grants read on pods and
> their logs — no `create`/`delete`, no other resource. That's least privilege expressed
> as a Role.

---

## Step 2 — Bind it to a group

```bash
oc adm groups new billing-viewers 2>/dev/null || true          # (group creation needs admin; see Demo 3)
oc create rolebinding cdr-log-reader-b \
  --role=cdr-log-reader --group=billing-viewers -n mod8-demos
oc get rolebinding cdr-log-reader-b -n mod8-demos -o wide
```

**Expected output** *(requires a cluster — representative):*

```
rolebinding.rbac.authorization.k8s.io/cdr-log-reader-b created
NAME               ROLE                  AGE   USERS   GROUPS            SERVICEACCOUNTS
cdr-log-reader-b   Role/cdr-log-reader   2s            billing-viewers
```

> **Narrate:** We bound to a **group**, not a user — onboarding a new viewer is "add to
> `billing-viewers`", no binding churn. The RoleBinding references the namespaced Role and
> only works in *this* project.

---

## Step 3 — Bind default ClusterRoles per-project

```bash
# developers get 'edit'; the auditor gets 'view' — both scoped to this project
oc create rolebinding billing-devs-edit --clusterrole=edit --group=billing-devs -n mod8-demos
oc create rolebinding auditor-view --clusterrole=view --user=auditor -n mod8-demos
oc get rolebindings -n mod8-demos -o custom-columns=NAME:.metadata.name,ROLE:.roleRef.name,KIND:.roleRef.kind
```

**Expected output** *(requires a cluster — representative):*

```
rolebinding.rbac.authorization.k8s.io/billing-devs-edit created
rolebinding.rbac.authorization.k8s.io/auditor-view created
NAME                ROLE               KIND
auditor-view        view               ClusterRole
billing-devs-edit   edit               ClusterRole
cdr-log-reader-b    cdr-log-reader     Role
```

> **Narrate:** Note **`edit`/`view` are ClusterRoles bound with a RoleBinding** — that's
> how per-project access works. The `KIND` column shows ClusterRole vs our namespaced Role.

---

## Step 4 — Prove the boundaries with `can-i --as`

```bash
oc auth can-i create deployments -n mod8-demos --as=dev1 --as-group=billing-devs   # edit → yes
oc auth can-i delete pods       -n mod8-demos --as=viewer1 --as-group=billing-viewers  # log-reader → no
oc auth can-i get pods/log      -n mod8-demos --as=viewer1 --as-group=billing-viewers  # → yes
oc auth can-i create rolebindings -n mod8-demos --as=dev1 --as-group=billing-devs      # edit ≠ RBAC → no
oc adm policy who-can get pods/log -n mod8-demos
```

**Expected output** *(requires a cluster — representative):*

```
yes
no
yes
no
Namespace: mod8-demos
Verb:      get
Resource:  pods/log
Groups:    billing-viewers  system:cluster-admins ...
```

> **Narrate:** Exactly the design: devs deploy but can't touch RBAC (`edit` ≠ RBAC);
> viewers read logs but can't delete pods. `can-i --as` proves each boundary; `who-can` is
> the audit inverse. This is least privilege, demonstrated.

---

## Step 5 — Cleanup

```bash
oc delete rolebinding cdr-log-reader-b billing-devs-edit auditor-view -n mod8-demos
oc delete role cdr-log-reader -n mod8-demos
```

**Expected output** *(representative):*

```
rolebinding.rbac.authorization.k8s.io "cdr-log-reader-b" deleted
...
role.rbac.authorization.k8s.io "cdr-log-reader" deleted
```

---

## Wrap-up questions to pose

1. What three parts make up a Role rule, and what does `apiGroups: [""]` mean?
2. Why are `edit`/`view` bound with a **RoleBinding** and not a ClusterRoleBinding here?
3. A dev has `edit` but can't create a RoleBinding. Why?
4. What's the single best command to debug "user X can't do Y"?

---

> **◐ Partially verified:** `oc create role/rolebinding --help` confirmed with **oc 4.22**;
> the cluster steps **require a live OpenShift cluster** and were not run at authoring
> (cluster asleep). Output is **representative of OpenShift 4.18**. RBAC creation +
> `can-i --as` are runnable by a **normal user in their own project** (group *creation* in
> Step 2/3 needs admin — see Demo 3); the additive-no-deny model and `edit ≠ RBAC` are real
> behaviours. Validate live when the cluster is up.
