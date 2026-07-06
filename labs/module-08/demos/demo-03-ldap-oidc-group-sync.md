# Demo 3 — LDAP/OIDC Integration & Group Sync

> **Scenario:** Mobily wants staff to log in with their **corporate directory** account
> and have access follow their **AD groups**. We walk the **LDAP/AD** and **OIDC** config
> shape, run **`oc adm groups sync`** to mirror an AD group into an OpenShift Group, and
> bind a role to that group so the whole team gets access at once.

| | |
|---|---|
| **Concepts reinforced** | LDAP/AD IdP shape (sAMAccountName, ldaps://) · OIDC (issuer/claims/groups) · `oc adm groups sync` · bind role to group |
| **Maps to** | Guide §10, §11, §12 · Visualization 03 · Exercise 3 |
| **Time** | ~30 minutes |
| **Cluster** | Shared OCP 4.18 — IdP config + group sync + cluster bindings need **cluster-admin** |

---

> **⎈ Kubernetes equivalent:** the LDAP/OIDC IdPs, `User`/`Group`/`Identity`, and
> `oc adm groups sync` are OpenShift-specific.

> ⚠️ **Cluster-admin + a reachable directory** are required to *run* this for real. If no
> LDAP/OIDC endpoint is available, the instructor walks the config shape and the sync
> **dry-run** reasoning; the concepts are the goal.

## Talking points to open with

- **AD speaks LDAP** — no separate AD provider; use the LDAP IdP, match `sAMAccountName`.
- **OIDC** can carry **group claims in the token** (often no separate sync); LDAP needs a
  **group sync** step.
- Bind roles to **synced groups** so directory membership drives access.

---

## Step 1 — The LDAP/AD IdP config shape

```bash
# service-account bind password + directory CA (cluster-admin)
oc create secret generic ldap-bind-password \
  --from-literal=bindPassword='<svc-bind-pw>' -n openshift-config
oc create configmap ldap-ca --from-file=ca.crt=corp-ca.crt -n openshift-config

# add an LDAP identityProvider to the OAuth CR (AD: match sAMAccountName, use ldaps://)
oc apply -f - <<'EOF'
apiVersion: config.openshift.io/v1
kind: OAuth
metadata: { name: cluster }
spec:
  identityProviders:
    - name: mobily-ad
      mappingMethod: claim
      type: LDAP
      ldap:
        url: "ldaps://ad.mobily.example:636/OU=Users,DC=mobily,DC=example?sAMAccountName?sub?(objectClass=user)"
        bindDN: "CN=ocp-bind,OU=Svc,DC=mobily,DC=example"
        bindPassword: { name: ldap-bind-password }
        ca: { name: ldap-ca }
        attributes:
          id: ["sAMAccountName"]
          preferredUsername: ["sAMAccountName"]
          name: ["displayName"]
          email: ["mail"]
        insecure: false
EOF
```

**Expected output** *(requires cluster-admin — representative):*

```
secret/ldap-bind-password created
configmap/ldap-ca created
oauth.config.openshift.io/cluster configured
```

> **Narrate:** The **query URL** carries host, base DN, the **match attribute**
> (`sAMAccountName` for AD), scope and filter. `bindDN`/`bindPassword` is a search service
> account; `ca` + `ldaps://` keep it encrypted. This authenticates **users** — groups come
> next.

---

## Step 2 — (Alternative) the OIDC config shape

```bash
oc create secret generic entra-client-secret \
  --from-literal=clientSecret='<oidc-client-secret>' -n openshift-config
# add an openID identityProvider: issuer + clientID + claims (incl. groups)
#   spec.identityProviders[].type: OpenID
#   openID: { clientID, clientSecret{name}, issuer, claims:{preferredUsername,name,email,groups} }
```

**Expected output** *(requires cluster-admin — representative):*

```
secret/entra-client-secret created
```

> **Narrate:** OIDC registers OpenShift as an app in the provider (Entra ID/Okta/Keycloak).
> The **`groups` claim** means membership can arrive *in the token* — often no separate
> sync. That's the main LDAP-vs-OIDC difference.

---

## Step 3 — Sync an AD group into an OpenShift Group

```bash
# sync-config maps the directory schema; --confirm writes the Groups (cluster-admin)
oc adm groups sync --sync-config=ldap-group-sync.yaml --confirm
oc get groups
oc get group billing-devs -o jsonpath='{.users}{"\n"}'
```

**Expected output** *(requires cluster-admin + reachable LDAP — representative):*

```
group/billing-devs
group/noc-viewers
NAME           USERS
billing-devs   ["m.hassan","a.khan","s.ali"]
noc-viewers    ["r.nair","t.omar"]
["m.hassan","a.khan","s.ali"]
```

> **Narrate:** `oc adm groups sync` read membership from AD and created matching OpenShift
> **Groups**. Run this on a **CronJob** so joiners/leavers propagate automatically. A
> synced group has **no access yet** — bind a role next.

---

## Step 4 — Bind a role to the synced group

```bash
oc adm policy add-role-to-group edit billing-devs -n mod8-demos
oc auth can-i create deployments -n mod8-demos --as m.hassan --as-group billing-devs   # yes
oc adm policy who-can create deployments -n mod8-demos
```

**Expected output** *(requires a cluster — representative):*

```
clusterrole.rbac.authorization.k8s.io/edit added: "billing-devs"
yes
Namespace: mod8-demos
Verb:      create
Resource:  deployments.apps
Groups:    billing-devs  system:cluster-admins ...
```

> **Narrate:** One binding, whole team enabled. Add someone to `billing-devs` **in AD** →
> the next scheduled sync adds them to the OpenShift Group → they inherit `edit`. Directory
> membership *is* cluster access — one source of truth, fully auditable.

---

## Step 5 — Cleanup

```bash
oc adm policy remove-role-from-group edit billing-devs -n mod8-demos
oc delete group billing-devs noc-viewers      # if these were demo-only
```

**Expected output** *(representative):*

```
clusterrole.rbac.authorization.k8s.io/edit removed: "billing-devs"
group.user.openshift.io "billing-devs" deleted
group.user.openshift.io "noc-viewers" deleted
```

---

## Wrap-up questions to pose

1. Which IdP type does Active Directory use, and which attribute matches the username?
2. How do AD groups become OpenShift Groups — and how do you keep them current?
3. What can OIDC deliver that removes the separate group-sync step?
4. After syncing, how do you grant an entire team access in one step?

---

> **◐ Partially verified:** `oc adm groups sync --help` and `oc create secret/configmap
> --help` confirmed with **oc 4.22** client-side. All cluster steps **require a live
> OpenShift cluster with cluster-admin and a reachable LDAP/OIDC endpoint** and were not
> run at authoring (cluster asleep). Output is **representative of OpenShift 4.18**; the
> OAuth CR schemas, `sAMAccountName` matching, and group-sync→bind flow are documented,
> real behaviours. Validate live as an admin against a directory when available.
