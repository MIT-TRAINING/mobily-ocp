# Demo 2 — htpasswd Identity Provider

> **Scenario:** The shared Mobily cluster only has the break-glass `kubeadmin`. We add a
> real login path: an **htpasswd** identity provider with users **alice** and **bob**,
> wire it into the **OAuth** resource, log in as a new user, and show that authentication
> alone grants **no** access until RBAC is bound.

| | |
|---|---|
| **Concepts reinforced** | OAuth CR · htpasswd Secret · IdP rollout · first login → User/Identity · authn ≠ authz · removing kubeadmin |
| **Maps to** | Guide §8, §9 · Visualization 02 · Exercise 2 |
| **Time** | ~30 minutes |
| **Cluster** | Shared OCP 4.18 — editing the OAuth CR / Secrets in `openshift-config` needs **cluster-admin** |

---

> **⎈ Kubernetes equivalent:** none — the OAuth server + htpasswd IdP is OpenShift's login
> layer. Vanilla Kubernetes has no built-in login server.

> ⚠️ **Cluster-admin required** for all steps that touch `openshift-config` and the OAuth
> CR. Instructor-led; participants observe.

## Talking points to open with

- OpenShift stores no human passwords — the OAuth server delegates to an IdP.
- htpasswd = a bcrypt file in a Secret; perfect for labs and **break-glass**.
- A new user can log in but can do **nothing** until a Role is bound (authn ≠ authz).

---

## Step 1 — Build the htpasswd file (bcrypt)

```bash
htpasswd -c -B -b users.htpasswd alice '<alice-pw>'
htpasswd    -B -b users.htpasswd bob   '<bob-pw>'
cat users.htpasswd
```

**Expected output** *(local — representative; values are placeholders):*

```
Adding password for user alice
Adding password for user bob
alice:$2y$05$Xb…(bcrypt hash)…
bob:$2y$05$Qm…(bcrypt hash)…
```

> **Narrate:** `-B` = bcrypt (required), `-c` = create the file (first user only). Never
> commit this file or real passwords — the hashes are still sensitive.

---

## Step 2 — Store it as a Secret in `openshift-config`

```bash
oc create secret generic mobily-htpasswd \
  --from-file=htpasswd=users.htpasswd -n openshift-config
```

**Expected output** *(requires cluster-admin — representative):*

```
secret/mobily-htpasswd created
```

> **Narrate:** The IdP reads its user file from this Secret in the special
> `openshift-config` namespace — the cluster-wide config home.

---

## Step 3 — Wire the IdP into the OAuth CR

```bash
oc apply -f - <<'EOF'
apiVersion: config.openshift.io/v1
kind: OAuth
metadata: { name: cluster }
spec:
  identityProviders:
    - name: mobily-htpasswd
      mappingMethod: claim
      type: HTPasswd
      htpasswd:
        fileData: { name: mobily-htpasswd }
EOF
oc get oauth cluster -o jsonpath='{.spec.identityProviders[*].name}{"\n"}'
```

**Expected output** *(requires cluster-admin — representative):*

```
oauth.config.openshift.io/cluster configured
mobily-htpasswd
```

> **Narrate:** One cluster-wide `OAuth` object named `cluster` lists all IdPs. The
> **authentication** Cluster Operator now rolls out new OAuth pods — give it a minute or
> two (`oc get co authentication` shows `PROGRESSING`).

---

## Step 4 — Log in as a new user; see User/Identity created

```bash
oc login -u alice -p '<alice-pw>'
oc whoami
oc get users; oc get identities        # (as admin) alice now exists
```

**Expected output** *(requires a cluster — representative):*

```
Login successful.
You don't have any projects. ...
alice

NAME    UID   FULL NAME   IDENTITIES
alice   ...               mobily-htpasswd:alice
NAME                    IDP NAME          IDP USER NAME   USER NAME
mobily-htpasswd:alice   mobily-htpasswd   alice           alice
```

> **Narrate:** First login created a **User** and an **Identity** (the `idp:username`
> link). "You don't have any projects" is the point — **authenticated but unauthorized**.

---

## Step 5 — authn ≠ authz: grant access

```bash
oc auth can-i create deployments -n mod8-demos --as alice     # no (nothing bound yet)
oc adm policy add-role-to-user edit alice -n mod8-demos        # admin grants access
oc auth can-i create deployments -n mod8-demos --as alice     # now yes
```

**Expected output** *(requires a cluster — representative):*

```
no
clusterrole.rbac.authorization.k8s.io/edit added: "alice"
yes
```

> **Narrate:** Logging in changed nothing about permissions. Only after binding `edit`
> can alice deploy. Keep authentication and authorization firmly separate in your head.

---

## Step 6 — Cleanup (and the real-world next step)

```bash
oc adm policy remove-role-from-user edit alice -n mod8-demos
# In production, once a real admin login exists, remove the break-glass kubeadmin:
#   oc delete secret kubeadmin -n kube-system      # (do NOT run on the shared class cluster)
```

**Expected output** *(representative):*

```
clusterrole.rbac.authorization.k8s.io/edit removed: "alice"
```

> **Narrate:** The final hardening step in a real cluster is removing **kubeadmin** once
> an htpasswd/LDAP admin exists — but never on a shared class cluster others rely on.

---

## Wrap-up questions to pose

1. Where are human passwords stored in OpenShift?
2. What two objects appear on a user's first successful login?
3. alice logged in but "has no projects" — why, and how do you fix it?
4. What's the final hardening step after a real admin login exists?

---

> **◐ Partially verified:** `htpasswd` and `oc create secret --help` confirmed with **oc
> 4.22** client-side. All cluster steps **require a live OpenShift cluster with
> cluster-admin** (editing the OAuth CR / `openshift-config`) and were not run at authoring
> (cluster asleep). Output is **representative of OpenShift 4.18**; the OAuth CR schema and
> User/Identity-on-first-login behaviour are real. Validate live as an admin when the
> cluster is up.
