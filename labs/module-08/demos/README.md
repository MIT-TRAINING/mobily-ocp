# Module 8 — Guided Demos (Instructor-Led)

These are **instructor-led, narrated walkthroughs**. The instructor runs each step live
against the real **OpenShift 4.18** cluster while explaining *what* each object does and
*why*. Participants watch and follow along, then practice in the
[`../exercises`](../exercises).

Module 8 — **"Authentication, RBAC and Identity Integration"** — covers **RBAC** (custom
Roles, least privilege), **authentication** (the OAuth server + identity providers), and
**enterprise identity** (LDAP/AD/OIDC + group sync). RBAC objects are standard Kubernetes;
the OAuth resource, IdPs, `User`/`Group`/`Identity`, and `oc adm groups sync` are
OpenShift-specific.

All scenarios use a **telecom domain** framing (projects `team-billing`/`team-crm`, NOC
viewers, auditors, SREs; corporate AD groups `billing-devs`, `noc-viewers`). All users and
directories are fictional.

## Demos in this module

| # | Demo | Concepts reinforced | Telecom scenario | Time |
|---|------|---------------------|------------------|------|
| 1 | [Custom RBAC & least privilege](demo-01-rbac-least-privilege.md) | custom Role rule · `oc create role/rolebinding` · default roles · `can-i`/`who-can`/`--as` | Scoped access for **billing** roles | ~30 min |
| 2 | [htpasswd identity provider](demo-02-htpasswd-idp.md) | OAuth CR · htpasswd Secret · first login · authn ≠ authz · remove kubeadmin | Onboard **alice/bob** logins | ~30 min |
| 3 | [LDAP/OIDC & group sync](demo-03-ldap-oidc-group-sync.md) | LDAP/AD/OIDC config shape · `oc adm groups sync` · bind role to group | Map **AD groups** to access | ~30 min |

## Conventions

- Commands use **`oc`**. Role/ClusterRole/RoleBinding/ClusterRoleBinding are pure
  `kubectl` (an **⎈** note flags this); the **OAuth** CR, IdP config, `oc adm policy`,
  `oc adm groups` are OpenShift-specific.
- **Permissions.** A normal project user can create Roles/RoleBindings and run `can-i`
  **in their own project**. **Configuring an IdP** (Demo 2) and **cluster group sync +
  cluster bindings** (Demo 3) need **cluster-admin** — those are instructor-led. Each demo
  marks which steps need admin.
- Replace placeholders (`<cluster-domain>`, `<pw>`, `<bindPassword>`). **Never commit real
  passwords/bind credentials** — all values are fictional placeholders; secrets live in
  `openshift-config`.
- Each demo ends with a **Cleanup** section.
- Companion material: the
  [concept guide](../../../guides/module-08-authentication-rbac-identity.md), the
  interactive [visualizations](../index.html), and the [exercises](../exercises/README.md).

## Pre-flight check (run once before Demo 1)

```bash
oc login https://api.<cluster-domain>:6443 -u <user> -p "$OCP_PASSWORD"   # or token
oc whoami
oc auth can-i '*' '*' --all-namespaces      # 'yes' => cluster-admin (needed for Demos 2-3)
oc new-project mod8-demos --display-name="Module 8 Demos" 2>/dev/null || oc project mod8-demos
```

> **Instructor tip:** keep the **web console** open — **User Management → Roles /
> RoleBindings** and **Administration → Cluster Settings → Configuration → OAuth** mirror
> the CLI. For Demo 2 have a **cluster-admin** session ready (editing `oauth cluster`); for
> Demo 3, if no real LDAP is available, walk the config shape and demo `oc adm groups sync
> --type=... --dry-run` reasoning.

---

> **◐ Partially verified (cluster asleep at authoring time).** Client-side help
> (`oc create role|clusterrole|rolebinding`, `oc adm groups sync`, `oc adm policy`) was run
> live with **oc 4.22**. Every command that needs a **live OpenShift cluster** (creating
> roles/bindings, editing the OAuth CR, group sync, `can-i --as`) is labelled
> **"requires a cluster — output is representative of OpenShift 4.18"**. These can be
> validated when the cluster is up — RBAC/`can-i` in a normal user's own project; IdP and
> group sync require cluster-admin — the same way Module 6 was validated.
