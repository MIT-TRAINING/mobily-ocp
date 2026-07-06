# Exercise 3 — Stateful + Secure App (Capstone)

> **Scenario:** Bring up the Mobily **billing** app the production way: its own
> **ServiceAccount**, its DB password in a **Secret**, a **PVC** for durable data, and
> confirmation it runs **non-root** under `restricted-v2`. This capstone combines every
> piece of Module 7 into one deployable, secure, stateful workload.

| | |
|---|---|
| **Practice** | dedicated SA · Secret (env + mounted) · PVC · verify non-root SCC · least privilege |
| **Maps to** | Guide §8, §9, §10, §11 · Visualizations 01–03 · Demos 1 & 3 |
| **Difficulty** | ⭐⭐⭐ Advanced (capstone) · ~30–35 min · normal user OK (no SCC grant needed) |

---

## Tasks

1. Create a **ServiceAccount** `billing-app-sa`.
2. Create a **Secret** `db-creds` with `username=billing` and a placeholder `password`.
3. Create a **PVC** `billing-data` (1Gi, RWO).
4. Create deployment `billing-app` (`ubi9/httpd-24`), and wire it up: run as
   **billing-app-sa**, mount the **PVC** at `/data`, and inject **db-creds** as env vars.
5. **Verify the four properties:** it runs as `billing-app-sa`, under **restricted-v2** as
   a **non-root** UID, the password is present, and `/data` is a mounted PVC.
6. Prove **least privilege**: confirm the app's SCC is `restricted-v2` (no broad grant
   needed for a rootless image) and that the Secret is only base64 (protected by RBAC).

> **Hint (Task 4):** `oc set serviceaccount`, `oc set volume --add --type=pvc`, and
> `oc set env --from=secret/db-creds` each patch the deployment.

---

## Validation

```bash
P=$(oc get pods -l app=billing-app -o jsonpath='{.items[0].metadata.name}')
oc get pod "$P" -o jsonpath='sa={.spec.serviceAccountName} scc={.metadata.annotations.openshift\.io/scc}{"\n"}'
oc exec "$P" -- id                          # non-root UID
oc exec "$P" -- printenv password           # from the Secret
oc exec "$P" -- sh -c 'mount | grep /data'  # PVC mounted
oc get pvc billing-data                     # Bound
```

Expected: `sa=billing-app-sa scc=restricted-v2`, a non-root `uid=100075xxxx`, the password
prints, `/data` is mounted, PVC `Bound`.

---

## Reflection

- Which four Module 7 objects came together here, and what does each provide?
- Why did this app need **no** SCC grant, while Exercise 2's legacy image did?
- The Secret is only base64. What actually stops another tenant from reading it?

---

<details>
<summary><strong>✅ Solution</strong> (try the tasks first)</summary>

```bash
# 1. ServiceAccount
oc create serviceaccount billing-app-sa

# 2. Secret (placeholder values — never commit real ones)
oc create secret generic db-creds \
  --from-literal=username=billing --from-literal=password='<your-password>'

# 3. PVC
cat <<'EOF' | oc apply -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata: { name: billing-data }
spec:
  accessModes: [ReadWriteOnce]
  resources: { requests: { storage: 1Gi } }
EOF

# 4. Deploy + wire it all up
oc create deployment billing-app --image=registry.access.redhat.com/ubi9/httpd-24:latest
oc set serviceaccount deployment/billing-app billing-app-sa
oc set volume deploy/billing-app --add --name=data --type=pvc \
  --claim-name=billing-data --mount-path=/data
oc set env deployment/billing-app --from=secret/db-creds
oc rollout status deploy/billing-app

# 5. Verify the four properties
P=$(oc get pods -l app=billing-app -o jsonpath='{.items[0].metadata.name}')
oc get pod "$P" -o jsonpath='sa={.spec.serviceAccountName} scc={.metadata.annotations.openshift\.io/scc}{"\n"}'
oc exec "$P" -- id
oc exec "$P" -- printenv username password
oc exec "$P" -- sh -c 'mount | grep /data'
oc get pvc billing-data

# 6. Least privilege: SCC is restricted-v2 (no grant needed); Secret is base64+RBAC
oc get secret db-creds -o jsonpath='{.data.password}' | base64 -d; echo

# Cleanup
oc delete deployment billing-app ; oc delete pvc billing-data
oc delete secret db-creds ; oc delete sa billing-app-sa
```

**Representative output** *(requires a cluster — OCP 4.18):*

```
sa=billing-app-sa scc=restricted-v2
uid=1000750000 gid=0(root) groups=1000750000,0(root)
billing
<your-password>
tmpfs on /data type ...      # (PVC-backed mount at /data)
billing-data   Bound   pvc-...   1Gi   RWO   gp3-csi
```

**Key point:** a production workload = **PVC** (durable data) + **Secret** (credentials,
env or mounted) + dedicated **ServiceAccount** (scoped identity) + **restricted-v2 SCC**
(non-root by default). Because `ubi9/httpd-24` is rootless, it needs **no** SCC grant —
least privilege for free. The Secret is base64 only; **RBAC** (project isolation) is what
keeps other tenants from reading it.
</details>

---

> **◐ Partially verified:** client-side `oc set`/`oc create` help confirmed with **oc
> 4.22**; the cluster steps **require a live OpenShift cluster** (not runnable at
> authoring — cluster asleep). Output is **representative of OpenShift 4.18**. This whole
> capstone is runnable by a **normal user (learner25)** in their own project (no SCC grant
> needed) once the cluster is up — the same validation path used for Module 6.
