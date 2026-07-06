# Exercise 2 — htpasswd Identity Provider

> **Scenario:** Add a real login path to the cluster. Create an **htpasswd** identity
> provider for a new engineer, wire it into the **OAuth** resource, log in as the new user,
> and confirm they have **no** access until you bind a Role.

| | |
|---|---|
| **Practice** | build an htpasswd Secret, edit the OAuth CR, first login → User/Identity, authn ≠ authz |
| **Maps to** | Guide §8, §9 · Visualization 02 · Demo 2 |
| **Difficulty** | ⭐⭐ Intermediate · ~25 min · **needs cluster-admin** |

> ⚠️ **Cluster-admin required** (Secrets in `openshift-config`, editing `oauth cluster`).
> If you're a normal user, read the steps, predict outcomes, and follow the instructor.

---

## Tasks

1. Build an htpasswd file (bcrypt) with a user `neweng`.
2. Store it as a Secret named `mobily-htpasswd` in `openshift-config`.
3. Add an **HTPasswd** identity provider named `mobily-htpasswd` to the `OAuth` CR.
4. After the OAuth Operator rolls out, **log in** as `neweng` and confirm the **User** and
   **Identity** objects exist.
5. Show `neweng` can do **nothing** yet, then **grant** `edit` in a project and re-check.

> **Hint (Task 1):** `htpasswd -c -B -b users.htpasswd neweng '<pw>'` (`-B` bcrypt, `-c`
> create).

> **Hint (Task 3):** `spec.identityProviders[]` with `type: HTPasswd` and
> `htpasswd.fileData.name: mobily-htpasswd`.

---

## Validation

```bash
oc get oauth cluster -o jsonpath='{.spec.identityProviders[*].name}{"\n"}'   # mobily-htpasswd
oc get co authentication                                                     # AVAILABLE True (after rollout)
# after login:
oc get user neweng ; oc get identity | grep neweng
oc auth can-i create deployments -n mod8-ex --as neweng                      # no → (bind) → yes
```

---

## Reflection

- Where is the htpasswd user file actually stored, and in which namespace?
- What two objects are created the first time `neweng` logs in?
- Why does a freshly-created user see "no projects"?

---

<details>
<summary><strong>✅ Solution</strong> (try the tasks first — needs cluster-admin)</summary>

```bash
# 1. htpasswd file (bcrypt)
htpasswd -c -B -b users.htpasswd neweng '<neweng-pw>'

# 2. Secret in openshift-config
oc create secret generic mobily-htpasswd \
  --from-file=htpasswd=users.htpasswd -n openshift-config

# 3. Add the IdP to the OAuth CR
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

# 4. Wait for rollout, then log in (a minute or two)
oc get co authentication          # wait for PROGRESSING=False
oc login -u neweng -p '<neweng-pw>'
oc whoami                         # neweng
oc get user neweng                # (as admin) exists
oc get identity | grep neweng     # mobily-htpasswd:neweng

# 5. authn != authz
oc auth can-i create deployments -n mod8-ex --as neweng     # no
oc adm policy add-role-to-user edit neweng -n mod8-ex
oc auth can-i create deployments -n mod8-ex --as neweng     # yes

# Cleanup (do NOT delete kubeadmin on the shared class cluster)
oc adm policy remove-role-from-user edit neweng -n mod8-ex
```

**Representative output** *(requires cluster-admin — OCP 4.18):*

```
mobily-htpasswd
secret/mobily-htpasswd created
oauth.config.openshift.io/cluster configured
Login successful.
You don't have any projects. ...
neweng
mobily-htpasswd:neweng   mobily-htpasswd   neweng   neweng
no
clusterrole.rbac.authorization.k8s.io/edit added: "neweng"
yes
```

**Key point:** OpenShift stores no human passwords — the htpasswd **Secret** in
`openshift-config` feeds the OAuth server. First login creates **User** + **Identity**, but
grants **zero** access ("no projects") until RBAC binds a Role. Keep one htpasswd admin as
break-glass, then remove `kubeadmin` (never on a shared class cluster).
</details>

---

> **◐ Partially verified:** `htpasswd` / `oc create secret --help` confirmed with **oc
> 4.22** client-side. All cluster steps **require a live OpenShift cluster with
> cluster-admin** and were not run at authoring (cluster asleep). Output is
> **representative of OpenShift 4.18**; the OAuth CR schema and User/Identity-on-first-login
> are real behaviours. Validate live as an admin when the cluster is up.
