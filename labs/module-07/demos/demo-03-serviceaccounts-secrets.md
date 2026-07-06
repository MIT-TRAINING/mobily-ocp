# Demo 3 — ServiceAccounts & Secrets

> **Scenario:** The Mobily **billing** app needs its own **identity** (not the shared
> `default` SA) and a safe way to receive its **database password**. We create a
> dedicated **ServiceAccount**, a **Secret**, prove that a Secret is **base64, not
> encryption**, and wire the credentials into the app as **env vars** and as **mounted
> files**.

| | |
|---|---|
| **Concepts reinforced** | dedicated ServiceAccount · `-z` role grants · Secret types · base64≠encryption · env vs mounted consumption |
| **Maps to** | Guide §9, §10 · Visualization 03 · Exercise 3 |
| **Time** | ~30 minutes |
| **Cluster** | Shared OCP 4.18 — a normal project user can do all of this |

---

> **⎈ Kubernetes equivalent:** ServiceAccounts and Secrets are standard Kubernetes.
> OpenShift adds the SCC linkage (Demo 2) and bound/projected SA tokens by default.

## Talking points to open with

- Every pod runs as a **ServiceAccount**; give each app its **own** so RBAC/SCC stay
  scoped.
- A Secret keeps credentials out of the image — but **base64 is encoding, not
  encryption**.
- Mounted Secrets **update in place**; env-var Secrets are a snapshot at start.

---

## Step 1 — A dedicated ServiceAccount for the app

```bash
oc create serviceaccount billing-app-sa
oc create deployment billing-app --image=registry.access.redhat.com/ubi9/httpd-24:latest
oc set serviceaccount deployment/billing-app billing-app-sa
oc rollout status deploy/billing-app
oc get pod -l app=billing-app -o jsonpath='runs-as-SA={.items[0].spec.serviceAccountName}{"\n"}'
```

**Expected output** *(requires a cluster — representative):*

```
serviceaccount/billing-app-sa created
deployment.apps/billing-app created
deployment.apps/billing-app serviceaccount updated
deployment "billing-app" successfully rolled out
runs-as-SA=billing-app-sa
```

> **Narrate:** The pod now runs as **billing-app-sa**, not the shared `default`. Any RBAC
> or SCC we grant with `-z billing-app-sa` applies to *only* this app — clean scope, clean
> audit.

---

## Step 2 — Create a Secret (values are placeholders)

```bash
oc create secret generic db-creds \
  --from-literal=username=billing \
  --from-literal=password='S3cr3t-billing-pw'
oc get secret db-creds
```

**Expected output** *(requires a cluster — representative):*

```
secret/db-creds created
NAME       TYPE     DATA   AGE
db-creds   Opaque   2      5s
```

> **Narrate:** An `Opaque` Secret with two keys. Nothing about it is encrypted yet — let's
> prove that.

---

## Step 3 — base64 is NOT encryption

```bash
oc get secret db-creds -o jsonpath='{.data.password}'; echo
oc get secret db-creds -o jsonpath='{.data.password}' | base64 -d; echo
```

**Expected output** *(requires a cluster — representative):*

```
UzNjcjN0LWJpbGxpbmctcHc=
S3cr3t-billing-pw
```

> **Narrate:** One command decodes it. **Anyone who can `oc get secret` reads the
> plaintext.** Secrets are protected by **RBAC** (who may read them) and optional **etcd
> encryption at rest** — *not* by the base64 encoding. Never commit real secret values to
> Git.

---

## Step 4 — Consume as environment variables

```bash
oc set env deployment/billing-app --from=secret/db-creds
oc rollout status deploy/billing-app
POD=$(oc get pods -l app=billing-app -o jsonpath='{.items[0].metadata.name}')
oc exec "$POD" -- printenv username password
```

**Expected output** *(requires a cluster — representative):*

```
deployment.apps/billing-app updated
deployment "billing-app" successfully rolled out
billing
S3cr3t-billing-pw
```

> **Narrate:** The keys arrive as env vars. **Caveat:** env vars are a snapshot at pod
> start — rotate the Secret and the running pod keeps the old value until it restarts.

---

## Step 5 — Consume as a mounted file (updates in place)

```bash
oc set volume deployment/billing-app --add --name=creds --type=secret \
  --secret-name=db-creds --mount-path=/etc/creds --read-only=true
oc rollout status deploy/billing-app
POD=$(oc get pods -l app=billing-app -o jsonpath='{.items[0].metadata.name}')
oc exec "$POD" -- cat /etc/creds/password; echo
```

**Expected output** *(requires a cluster — representative):*

```
info: ... volume updated
deployment "billing-app" successfully rolled out
S3cr3t-billing-pw
```

> **Narrate:** Now the same values are files under `/etc/creds`. **Mounted Secrets update
> in place** when the Secret changes — a watching app can reload without a restart. Choose
> env vars for simplicity, mounted files for rotation or for TLS certs (Module 6 Routes).

---

## Step 6 — Cleanup

```bash
oc delete deployment billing-app
oc delete secret db-creds
oc delete serviceaccount billing-app-sa
```

**Expected output** *(representative):*

```
deployment.apps "billing-app" deleted
secret "db-creds" deleted
serviceaccount "billing-app-sa" deleted
```

---

## Wrap-up questions to pose

1. Why give the app its own ServiceAccount instead of using `default`?
2. Is a Secret encrypted? What actually protects it?
3. You rotate a Secret. Which consumption method picks up the new value without a
   restart — env vars or a mounted volume?
4. Where would a TLS cert+key Secret be used (recall Module 6)?

---

> **◐ Partially verified:** `oc create secret generic --help`, `oc create serviceaccount
> --help`, and `oc set volume/env/serviceaccount --help` were confirmed with **oc 4.22**
> (client-side). The cluster steps **require a live OpenShift cluster** and were not run at
> authoring time (cluster asleep). Output is **representative of OpenShift 4.18**; the
> base64 round-trip is real. A **normal user (learner25) can validate all of Demo 3** in
> their own project once the cluster is up.
