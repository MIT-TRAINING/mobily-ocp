# Exercise 1 — Custom Roles & Bindings

> **Scenario:** Give the Mobily **billing** project scoped access: a bespoke read-only
> "config reader", developers with `edit`, and an auditor with `view` — then prove every
> boundary with `oc auth can-i --as`.

| | |
|---|---|
| **Practice** | author a Role (apiGroups/resources/verbs), bind default + custom roles, `can-i --as`, `who-can` |
| **Maps to** | Guide §3, §4, §6, §7 · Visualization 01 · Demo 1 |
| **Difficulty** | ⭐ Beginner · ~20 min · normal user OK in your own project |

---

## Tasks

1. Create a custom **Role** `config-reader` that can `get`/`list`/`watch` **configmaps**
   only (core API group).
2. **Bind** it to a group `billing-viewers` with a RoleBinding.
3. Bind the default **`edit`** ClusterRole to group `billing-devs`, and **`view`** to user
   `auditor` — both scoped to your project.
4. Prove with `can-i --as`: a dev can create deployments but **not** rolebindings; a viewer
   can read configmaps but **not** secrets; the auditor can read pods but **not** delete.
5. Use `who-can` to list who can `get configmaps` in the project.

> **Hint (Task 1):** `oc create role config-reader --verb=get,list,watch --resource=configmaps`.

> **Hint (Task 4):** impersonate a group with `--as=<user> --as-group=<group>`.

---

## Validation

```bash
oc get role config-reader -o jsonpath='{.rules}{"\n"}'
oc auth can-i create deployments --as=dev1 --as-group=billing-devs        # yes
oc auth can-i create rolebindings --as=dev1 --as-group=billing-devs       # no  (edit != RBAC)
oc auth can-i get configmaps --as=v1 --as-group=billing-viewers           # yes
oc auth can-i get secrets   --as=v1 --as-group=billing-viewers            # no
oc adm policy who-can get configmaps
```

---

## Reflection

- Why does a user with `edit` fail to create a RoleBinding?
- What does `apiGroups: [""]` select, and why did `config-reader` use it?
- How is binding the `edit` **ClusterRole** with a RoleBinding different from a
  ClusterRoleBinding?

---

<details>
<summary><strong>✅ Solution</strong> (try the tasks first)</summary>

```bash
# 1. Custom Role — configmaps read-only (core group)
oc create role config-reader --verb=get,list,watch --resource=configmaps

# 2. Bind to a group
oc create rolebinding config-reader-b --role=config-reader --group=billing-viewers

# 3. Default ClusterRoles, scoped to this project
oc create rolebinding billing-devs-edit --clusterrole=edit --group=billing-devs
oc create rolebinding auditor-view --clusterrole=view --user=auditor

# 4. Prove boundaries
oc auth can-i create deployments  --as=dev1 --as-group=billing-devs        # yes
oc auth can-i create rolebindings --as=dev1 --as-group=billing-devs        # no
oc auth can-i get configmaps      --as=v1   --as-group=billing-viewers      # yes
oc auth can-i get secrets         --as=v1   --as-group=billing-viewers      # no
oc auth can-i delete pods         --as=auditor                              # no
oc auth can-i get pods            --as=auditor                              # (needs auditor-view bound) yes

# 5. Who can?
oc adm policy who-can get configmaps

# Cleanup
oc delete rolebinding config-reader-b billing-devs-edit auditor-view
oc delete role config-reader
```

**Representative output** *(requires a cluster — OCP 4.18):*

```
[{"apiGroups":[""],"resources":["configmaps"],"verbs":["get","list","watch"]}]
yes
no
yes
no
Namespace: mod8-ex
Verb:      get
Resource:  configmaps
Groups:    billing-viewers  system:cluster-admins ...
```

**Key point:** a Role is `apiGroups × resources × verbs`; `""` is the core group. `edit`
lets devs manage workloads but **not RBAC** (that's `admin`/cluster-admin). Binding a
**ClusterRole with a RoleBinding** scopes it to one project — a ClusterRoleBinding would
grant it everywhere. Prove every boundary with `can-i --as`.
</details>

---

> **◐ Partially verified:** `oc create role/rolebinding --help` confirmed with **oc 4.22**;
> cluster steps **require a live OpenShift cluster** (not run at authoring — cluster
> asleep). Output is **representative of OpenShift 4.18**. RBAC creation + `can-i --as` are
> runnable by a **normal user in their own project**; the additive/no-deny model and
> `edit ≠ RBAC` are real behaviours. Validate live when the cluster is up.
