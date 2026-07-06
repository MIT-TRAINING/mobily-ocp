# Module 8 — Exercises (Hands-On Practice)

These are **participant-driven** tasks. You drive the **`oc`** CLI on the shared
**OpenShift 4.18** cluster, then verify with the provided **validation** commands. Each
exercise has a fully worked **solution** — try the tasks first, then check.

Module 8 — **"Authentication, RBAC and Identity Integration"** — covers **RBAC** (custom
Roles, least privilege), **authentication** (OAuth + identity providers), and **enterprise
identity** (LDAP/AD/OIDC + group sync). RBAC objects are standard Kubernetes; the OAuth CR,
IdPs, and `oc adm groups sync` are OpenShift-specific.

## Where to run these

| Target | What you can do | Notes |
|---|---|---|
| **Shared OpenShift 4.18 cluster** (preferred) | Roles/RoleBindings + `can-i` in your project | IdP config (Ex 2) & group sync (Ex 3) need **cluster-admin** |
| **[Developer Sandbox](https://developers.redhat.com/developer-sandbox)** | Custom Roles + `can-i` in your one project | No cluster-admin → IdP/group-sync are instructor-demoed |

> **`oc` == `kubectl`** for Role/ClusterRole/RoleBinding/ClusterRoleBinding and
> `oc auth can-i`. The **OAuth** CR, identity providers, `oc adm policy`, and
> `oc adm groups sync` are OpenShift-specific (IdP/sync are admin-gated).

## Exercises in this module

| # | Exercise | What you'll practice | Telecom scenario | Difficulty |
|---|----------|----------------------|------------------|------------|
| 1 | [Custom Roles & bindings](exercise-01-custom-roles.md) | author a Role, bind default + custom roles, `can-i --as`, `who-can` | Scoped **billing** access | ⭐ Beginner |
| 2 | [htpasswd identity provider](exercise-02-htpasswd-idp.md) | build htpasswd, wire the OAuth CR, first login, authn ≠ authz | Onboard a **new engineer** | ⭐⭐ Intermediate (admin) |
| 3 | [Least-privilege access model (capstone)](exercise-03-access-model-capstone.md) | design personas → groups → roles → bindings; group sync; verify | Full **Mobily** access model | ⭐⭐⭐ Advanced |

## Before you start

```bash
oc login https://api.<cluster-domain>:6443 -u <user> -p "$OCP_PASSWORD"   # or token
oc whoami
oc auth can-i '*' '*' --all-namespaces      # 'yes' => cluster-admin (needed for Ex 2 & parts of Ex 3)
oc new-project mod8-ex --display-name="Module 8 Exercises" 2>/dev/null || oc project mod8-ex
```

- Replace placeholders (`<cluster-domain>`, `<pw>`). **Never commit real passwords/bind
  credentials** — all values are fictional.
- **Admin-gated steps** (IdP config, group creation/sync, cluster bindings) are flagged; a
  normal user does the RBAC/`can-i` parts and follows the instructor for the rest.
- Cleanup: `oc delete project mod8-ex` (plus any groups/roles created cluster-wide).

## How to self-assess

Each exercise's **Validation** section gives commands whose output confirms success. If
your output matches the *shape* shown, you've done it. `oc auth can-i --as` is the fastest
self-check for any access model. Stuck? The **Solution** walks one correct approach.

Companion material: the guided [demos](../demos/README.md), the interactive
[visualizations](../index.html), and the
[concept guide](../../../guides/module-08-authentication-rbac-identity.md).

---

> **◐ Partially verified (cluster asleep at authoring).** Client-side `oc` help
> (`oc create role|clusterrole|rolebinding`, `oc adm groups sync`, `oc adm policy`)
> confirmed with **oc 4.22**. Cluster-dependent output is **representative of OpenShift
> 4.18** and can be validated when the cluster is up — RBAC + `can-i` as a normal user in
> your own project; IdP config and group sync as cluster-admin — the same way Module 6 was
> validated.
