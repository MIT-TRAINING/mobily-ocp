# Demo 4 — Projects, Users, Groups & RBAC

> **Scenario:** The **Billing** team is coming onto the Mobily cluster. We onboard them
> end-to-end the way a platform admin does it: a **Project** with a **quota** and
> **limit range**, a **group** with their users, and a least-privilege **RBAC** binding
> — then we *prove* the access with `oc auth can-i`.

| | |
|---|---|
| **Concepts reinforced** | `new-project` · `ResourceQuota`/`LimitRange` · users/groups/identities · `oc adm policy` · RoleBindings · `can-i`/`who-can` |
| **Maps to** | Guide §7, §8, §9 · Visualization 04 (tenant) · Exercise 4 |
| **Time** | ~30 minutes |
| **Cluster** | Shared OCP 4.18 — creating groups/RBAC needs **cluster-admin** |

---

> **⎈ Kubernetes equivalent:** RBAC (`Role`/`RoleBinding`/`ClusterRole`) is standard
> Kubernetes. **`Project`**, **`User`/`Group`/`Identity`**, and **`oc adm policy`** /
> **`oc adm groups`** are **OpenShift-only** — vanilla Kubernetes has no user/group API
> or project self-service.

> ⚠️ **Admin-only.** Creating groups and cluster-scoped users needs cluster-admin.
> Sandbox participants follow the instructor; the `oc auth can-i ... --as` checks (Step
> 5) are the part everyone can reason about.

## Talking points to open with

- A **Project** is the unit of multi-tenancy: a Namespace + self-service + quota.
- Identity is **external** (an IdP via OAuth); you manage **groups** and grant access to
  the *group*, not each user.
- **Least privilege:** `edit`/`view` over `admin`, project-scoped RoleBindings over
  cluster-wide, and `cluster-admin` only as break-glass.

---

## Step 1 — Create the tenant Project

```bash
oc new-project team-billing --display-name="Mobily Billing"
oc get project team-billing
```

**Expected output** *(requires a cluster — representative):*

```
Now using project "team-billing" on server "https://api.ocp4.example.com:6443".
NAME           DISPLAY NAME      STATUS
team-billing   Mobily Billing    Active
```

> **Narrate:** `new-project` both creates and switches. The creator automatically gets an
> `admin` RoleBinding *in this project*. Everything Billing makes is isolated here.

---

## Step 2 — Constrain it: quota + limit range

```bash
oc create quota billing-quota --hard=cpu=20,memory=40Gi,pods=50 -n team-billing
cat <<'EOF' | oc apply -n team-billing -f -
apiVersion: v1
kind: LimitRange
metadata: { name: billing-limits }
spec:
  limits:
    - type: Container
      default:        { cpu: "500m", memory: "512Mi" }
      defaultRequest: { cpu: "100m", memory: "128Mi" }
      max:            { cpu: "2",    memory: "2Gi" }
EOF
oc describe quota billing-quota -n team-billing
```

**Expected output** *(requires a cluster — representative):*

```
resourcequota/billing-quota created
limitrange/billing-limits created
Name:       billing-quota
Namespace:  team-billing
Resource    Used   Hard
--------    ----   ----
cpu         0      20
memory      0      40Gi
pods        0      50
```

> **Narrate:** **ResourceQuota** caps the team's *total* footprint; **LimitRange** gives
> every container sane defaults/max so a pod with no requests still behaves. Now Billing
> can self-serve safely *inside* these guardrails.

---

## Step 3 — Create a group and add users

```bash
oc adm groups new billing-admins
oc adm groups add-users billing-admins alice bob
oc get groups
```

**Expected output** *(requires a cluster — representative):*

```
group.user.openshift.io/billing-admins created
group.user.openshift.io/billing-admins added: "alice", "bob"
NAME             USERS
billing-admins   alice, bob
```

> **Narrate:** Users come from the IdP on first login (here we reference them by name).
> We manage the **group** — so onboarding the next dev is one `add-users`, not editing a
> dozen bindings.

---

## Step 4 — Grant least-privilege RBAC (to the group)

```bash
oc adm policy add-role-to-group admin billing-admins -n team-billing
oc get rolebinding -n team-billing | grep billing-admins
```

**Expected output** *(requires a cluster — representative):*

```
clusterrole.rbac.authorization.k8s.io/admin added: "billing-admins"
admin-0   ClusterRole/admin   ...   Group/billing-admins
```

> **Narrate:** We bound the **`admin`** ClusterRole to the **group**, scoped to
> **team-billing** via a RoleBinding — full control *in their project*, none outside it.
> Note it's `admin`, **not** `cluster-admin`: least privilege.

---

## Step 5 — Prove the access (and the boundaries)

```bash
oc auth can-i create deployments -n team-billing --as alice         # expect: yes
oc auth can-i create deployments -n team-crm     --as alice         # expect: no (other project)
oc auth can-i delete project team-billing        --as alice         # expect: no
oc adm policy who-can create deployments -n team-billing
```

**Expected output** *(requires a cluster — representative):*

```
yes
no
no
Namespace: team-billing
Verb:      create
Resource:  deployments.apps

Users:  ...
Groups: billing-admins  system:cluster-admins
```

> **Narrate:** `oc auth can-i --as` is the **single best RBAC debugging tool** — it
> answers "can this subject do this here?" directly. alice can build in *her* project,
> nowhere else, and can't delete the project. `who-can` is the inverse: who holds a
> permission. This is least privilege, demonstrated.

---

## Step 6 — Cleanup

```bash
oc delete project team-billing
oc delete group billing-admins
```

**Expected output** *(requires a cluster — representative):*

```
project.project.openshift.io "team-billing" deleted
group.user.openshift.io "billing-admins" deleted
```

> **Narrate:** Deleting the Project cascades every object inside (quota, limits,
> bindings, workloads). The group is cluster-scoped, so we remove it separately.

---

## Wrap-up questions to pose

1. What's the difference between a **ResourceQuota** and a **LimitRange**?
2. Why grant RBAC to a **group** rather than to each user?
3. Which is correct least privilege here — `admin` in the project or `cluster-admin`?
4. How would you debug "alice says she can't deploy" in one command?

---

> **◐ Partially verified:** `oc adm policy` / `oc create role` / `oc adm groups` **help**
> was confirmed with **oc 4.22** client-side; every command that **creates or queries
> cluster state** (Steps 1–6) **requires a live OpenShift cluster with cluster-admin**
> and was not run here. Output is **representative of OpenShift 4.18** — run it live for
> your own values. Nothing cluster-dependent is presented as independently verified.

> **◐ Validated (2026-07-05, as learner25):** live findings on OpenShift 4.18 for a normal
> user. **Works for a project self-provisioner:** `oc new-project` and — inside your *own*
> project — `oc adm policy add-role-to-user <role> <user>` (a project-admin can bind roles;
> `clusterrole/... added` succeeded). **Requires cluster-admin (returned `Forbidden`):**
> `oc create resourcequota`, `oc adm groups new`, and `oc auth can-i ... --as <user>`
> (impersonation). So the quota, group-creation, and `--as` verification steps are
> instructor/admin-led; the project + role-binding steps a learner can run directly.
