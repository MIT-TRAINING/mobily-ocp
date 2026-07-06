# Exercise 3 — Least-Privilege Access Model (Capstone)

> **Scenario:** Design and implement Mobily's **whole access model** on one cluster:
> billing developers, a billing owner, NOC viewers, an auditor, and a platform SRE — each
> mapped to a **group**, the **smallest role that works**, and the **narrowest scope**.
> Then prove it end-to-end with `oc auth can-i --as`. This capstone ties together custom
> roles, default roles, group-based binding, scope, and verification.

| | |
|---|---|
| **Practice** | persona→group→role→binding design · project vs cluster scope · group binding · `can-i --as` matrix |
| **Maps to** | Guide §3–§7, §12 · Visualizations 01 & 03 · Demos 1 & 3 |
| **Difficulty** | ⭐⭐⭐ Advanced (capstone) · ~30–35 min · group creation/cluster bindings need **cluster-admin** |

> ⚠️ Creating **Groups** and **ClusterRoleBindings** needs cluster-admin. A normal user
> can do the project-scoped RoleBindings + all the `can-i --as` verification.

---

## The model to implement

| Persona | Group | Role | Bound with | Scope |
|---|---|---|---|---|
| Billing developer | `billing-devs` | `edit` | RoleBinding | `team-billing` |
| Billing owner | `billing-admins` | `admin` | RoleBinding | `team-billing` |
| NOC viewer | `noc-viewers` | `view` | RoleBinding | `team-billing` (+ other app ns) |
| Security auditor | `auditors` | `cluster-reader` | ClusterRoleBinding | cluster-wide (read) |
| Platform SRE | `platform-sre` | `cluster-admin` | ClusterRoleBinding | cluster-wide |

## Tasks

1. Create the two projects `team-billing` and `team-crm` (or reuse existing).
2. Create the five **groups** and add a test user to each.
3. Bind each group to its role at the **correct scope** per the table (RoleBinding for
   project personas; ClusterRoleBinding for auditor/SRE).
4. **Verify the whole model** with a `can-i --as` matrix — at minimum:
   - dev can deploy in `team-billing` but **not** in `team-crm`, and **not** read nodes
   - NOC viewer can read pods in `team-billing` but **not** create
   - auditor can read pods in **any** namespace but **not** delete anything
   - only the SRE can delete a project
5. Explain why each grant is the **minimum** needed (least privilege).

> **Hint (Task 3):** `oc adm policy add-role-to-group <role> <group> -n <ns>` for project
> scope; `oc adm policy add-cluster-role-to-group <role> <group>` for cluster scope.

---

## Validation

```bash
# dev: scoped to team-billing only
oc auth can-i create deployments -n team-billing --as d1 --as-group billing-devs   # yes
oc auth can-i create deployments -n team-crm     --as d1 --as-group billing-devs   # no
oc auth can-i get nodes                          --as d1 --as-group billing-devs   # no

# noc viewer: read, not write
oc auth can-i get pods    -n team-billing --as v1 --as-group noc-viewers           # yes
oc auth can-i create pods -n team-billing --as v1 --as-group noc-viewers           # no

# auditor: cluster-wide read, no writes
oc auth can-i get pods -A       --as a1 --as-group auditors                        # yes
oc auth can-i delete pods -A    --as a1 --as-group auditors                        # no

# only SRE can delete a project
oc auth can-i delete project team-billing --as s1 --as-group platform-sre         # yes
oc auth can-i delete project team-billing --as d1 --as-group billing-devs         # no
```

---

## Reflection

- Which personas justified **cluster** scope, and why do the rest use project scope?
- Why bind to **groups** rather than the individual test users?
- The auditor is cluster-wide — why is that acceptable but a cluster-wide `edit` would not
  be?

---

<details>
<summary><strong>✅ Solution</strong> (try the tasks first — group/cluster steps need admin)</summary>

```bash
# 1. Projects
oc new-project team-billing 2>/dev/null || true
oc new-project team-crm 2>/dev/null || true

# 2. Groups + a test member each (cluster-admin)
for g in billing-devs billing-admins noc-viewers auditors platform-sre; do oc adm groups new "$g" 2>/dev/null; done
oc adm groups add-users billing-devs d1
oc adm groups add-users billing-admins o1
oc adm groups add-users noc-viewers v1
oc adm groups add-users auditors a1
oc adm groups add-users platform-sre s1

# 3. Bind at the correct scope
oc adm policy add-role-to-group edit  billing-devs   -n team-billing
oc adm policy add-role-to-group admin billing-admins -n team-billing
oc adm policy add-role-to-group view  noc-viewers    -n team-billing
oc adm policy add-cluster-role-to-group cluster-reader auditors
oc adm policy add-cluster-role-to-group cluster-admin  platform-sre

# 4. Verify the model (see Validation block) — spot checks:
oc auth can-i create deployments -n team-billing --as d1 --as-group billing-devs   # yes
oc auth can-i create deployments -n team-crm     --as d1 --as-group billing-devs   # no
oc auth can-i get pods -A                        --as a1 --as-group auditors       # yes
oc auth can-i delete pods -A                     --as a1 --as-group auditors       # no
oc auth can-i delete project team-billing        --as s1 --as-group platform-sre   # yes

# Cleanup (admin)
oc adm policy remove-cluster-role-from-group cluster-reader auditors
oc adm policy remove-cluster-role-from-group cluster-admin  platform-sre
for g in billing-devs billing-admins noc-viewers auditors platform-sre; do oc delete group "$g"; done
oc delete project team-billing team-crm      # if throwaway
```

**Representative output** *(requires a cluster; groups/cluster bindings need admin — OCP 4.18):*

```
yes
no
yes
no
yes
```

**Key point — least privilege by design:** map **personas → groups → smallest role →
narrowest scope**. Project personas use **RoleBindings** (blast radius = one project);
only genuinely cluster-wide personas use **ClusterRoleBindings** — and the auditor's is
**read-only** (`cluster-reader`), which is safe cluster-wide where a cluster-wide `edit`
never would be. Binding to **groups** means AD/HR membership changes (Module 8 §12) drive
access with no OpenShift edits.
</details>

---

> **◐ Partially verified:** `oc adm policy` / `oc adm groups` help confirmed with **oc
> 4.22** client-side. Cluster steps **require a live OpenShift cluster** (group creation +
> cluster bindings need **cluster-admin**) and were not run at authoring (cluster asleep).
> Output is **representative of OpenShift 4.18**; the scoping and `can-i --as` semantics are
> real. Verify live when the cluster is up — the `can-i --as` matrix is fully runnable by an
> admin, and the project-scoped checks by a normal user in their own project.
