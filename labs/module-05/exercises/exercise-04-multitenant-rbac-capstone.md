# Exercise 4 — Multi-Tenant Onboarding + RBAC (Capstone)

> **Scenario:** The **CRM** team is joining the Mobily cluster. As platform admin,
> onboard them end-to-end: a constrained **Project**, a **group** with their users, a
> **least-privilege** RBAC grant, and a **read-only auditor** — then *prove* every
> boundary with `oc auth can-i`. This capstone ties together Projects, quotas, limits,
> users/groups, and RBAC.

| | |
|---|---|
| **Practice** | `new-project` · `ResourceQuota` + `LimitRange` · `oc adm groups` · `oc adm policy` (role-to-group) · `can-i`/`who-can` · least privilege |
| **Maps to** | Guide §7, §8, §9 · Visualization 04 (tenant) · Demo 4 |
| **Difficulty** | ⭐⭐⭐ Advanced (capstone) · ~30–35 min · **needs cluster-admin** |

> ⚠️ **Admin required** to create groups and cluster-scoped users. If you're not admin,
> do the **`oc auth can-i ... --as`** reasoning against an existing project and follow the
> instructor for the create steps.

---

## Tasks

1. Create a Project **`team-crm`** (display name "Mobily CRM").
2. Constrain it: a **ResourceQuota** (cpu=10, memory=20Gi, pods=30) **and** a
   **LimitRange** giving containers sensible default/request/max.
3. Create a group **`crm-devs`** and add users **carol** and **dave**.
4. Grant **`crm-devs`** the **`edit`** role in `team-crm` (least privilege — *not*
   `admin`, *not* cluster-wide).
5. Grant a separate user **`auditor`** **`view`** (read-only) in `team-crm`.
6. **Prove the boundaries** with `oc auth can-i --as`: carol can create deployments in
   `team-crm` but not in another project and **cannot** edit RBAC; auditor can read but
   not create; nobody but cluster-admin can delete the project.
7. Use **`oc adm policy who-can`** to list who can create deployments in `team-crm`.

> **Hint (Task 4):** `oc adm policy add-role-to-group edit crm-devs -n team-crm`.

> **Hint (Task 6):** `edit` allows workloads but **not** RBAC — test
> `oc auth can-i create rolebindings -n team-crm --as carol` (expect **no**).

---

## Validation

```bash
# Task 2 — quota present and counting
oc describe quota -n team-crm
oc get limitrange -n team-crm

# Task 3 — group membership
oc get group crm-devs

# Task 6 — boundaries
oc auth can-i create deployments  -n team-crm   --as carol     # yes
oc auth can-i create deployments  -n team-billing --as carol   # no  (other project)
oc auth can-i create rolebindings -n team-crm   --as carol     # no  (edit != RBAC)
oc auth can-i create deployments  -n team-crm   --as auditor   # no  (view only)
oc auth can-i get pods            -n team-crm   --as auditor   # yes
```

---

## Reflection

- Why bind to the **group** `crm-devs` instead of to carol and dave individually?
- Why `edit` for the devs and not `admin`? What does `admin` add that they don't need?
- How does `oc auth can-i --as` make RBAC debugging fast — and how does `who-can`
  complement it?

---

<details>
<summary><strong>✅ Solution</strong> (try the tasks first)</summary>

```bash
# 1. Project
oc new-project team-crm --display-name="Mobily CRM"

# 2. Quota + LimitRange
oc create quota crm-quota --hard=cpu=10,memory=20Gi,pods=30 -n team-crm
cat <<'EOF' | oc apply -n team-crm -f -
apiVersion: v1
kind: LimitRange
metadata: { name: crm-limits }
spec:
  limits:
    - type: Container
      default:        { cpu: "500m", memory: "512Mi" }
      defaultRequest: { cpu: "100m", memory: "128Mi" }
      max:            { cpu: "2",    memory: "2Gi" }
EOF

# 3. Group + users
oc adm groups new crm-devs
oc adm groups add-users crm-devs carol dave

# 4. Least-privilege: edit for the dev group, scoped to the project
oc adm policy add-role-to-group edit crm-devs -n team-crm

# 5. Read-only auditor
oc adm policy add-role-to-user view auditor -n team-crm

# 6. Prove the boundaries
oc auth can-i create deployments  -n team-crm     --as carol     # yes
oc auth can-i create deployments  -n team-billing --as carol     # no
oc auth can-i create rolebindings -n team-crm     --as carol     # no
oc auth can-i create deployments  -n team-crm     --as auditor   # no
oc auth can-i get pods            -n team-crm     --as auditor   # yes
oc auth can-i delete project team-crm             --as carol     # no

# 7. Who can?
oc adm policy who-can create deployments -n team-crm

# Cleanup
oc delete project team-crm
oc delete group crm-devs
```

**Representative output** *(requires cluster-admin — OCP 4.18):*

```
Name:       crm-quota
Namespace:  team-crm
Resource    Used   Hard
--------    ----   ----
cpu         0      10
memory      0      20Gi
pods        0      30

NAME             USERS
crm-devs         carol, dave

clusterrole.rbac.authorization.k8s.io/edit added: "crm-devs"
clusterrole.rbac.authorization.k8s.io/view added: "auditor"

yes
no
no
no
yes

Namespace: team-crm
Verb:      create
Resource:  deployments.apps
Groups:    crm-devs  system:cluster-admins
```

**Key point — least privilege, demonstrated:** access is granted to a **group**
(onboarding = add to group), at **project scope** (RoleBinding, not cluster-wide), with
the **smallest role** that works (`edit` for devs, `view` for the auditor — never
`cluster-admin` for routine work). `oc auth can-i --as` proves each boundary; `who-can`
lists holders of a permission. That's a clean, auditable tenant.
</details>

---

> **◐ Partially verified:** `oc adm policy`/`oc adm groups`/`oc create` **help** was
> confirmed client-side with **oc 4.22**; all object-creating and `can-i` commands
> **require a live OpenShift cluster with cluster-admin** and were not run here. Output is
> **representative of OpenShift 4.18** — run it live to capture your real bindings and
> `can-i` results. Nothing cluster-dependent is presented as independently verified.
