# Exercise 1 — Install & Use an Operator

> **Scenario:** Provide the Mobily **CDR datastore** with a real PostgreSQL by installing an
> Operator via OLM, confirming it's healthy, and deploying a database with a **Custom
> Resource** — no StatefulSet by hand.

| | |
|---|---|
| **Practice** | find a package, Subscription → CSV, inspect an installed Operator, create a CR |
| **Maps to** | Guide §8, §9, §10, §11 · Visualization 01 · Demo 1 |
| **Difficulty** | ⭐ Beginner · ~20 min · **installing needs cluster-admin**; inspecting/CR can be a normal user |

> ⚠️ Installing a cluster-scoped Operator needs **cluster-admin**. If you're a normal user,
> do Tasks 3–5 against an Operator the instructor pre-installed.

---

## Tasks

1. Find a PostgreSQL Operator in the catalog and list its **channels**.
2. **(admin)** Subscribe to it (channel `stable`, Automatic approval) in your namespace
   (with an OperatorGroup).
3. Confirm install: the **Subscription**, the **InstallPlan**, and the **CSV** at
   `PHASE=Succeeded`.
4. Show the **CRD** the Operator added and read its `spec` with `oc explain`.
5. Create a **Custom Resource** (a small Postgres cluster) and confirm the Operator
   provisions pods.

> **Hint (Task 1):** `oc get packagemanifests -n openshift-marketplace | grep -i postgres`.

> **Hint (Task 3):** `oc get csv` — look for `PHASE: Succeeded`.

---

## Validation

```bash
oc get csv -n mod9-ex                                   # PHASE Succeeded
oc get crd | grep -i postgres                            # the CRD exists
oc get postgrescluster -n mod9-ex                        # your CR
oc get pods -n mod9-ex -l postgres-operator.crunchydata.com/cluster=cdr-store
```

---

## Reflection

- What three objects did your Subscription produce, and which one is the installed Operator?
- What did creating the CR save you from writing by hand?
- When is an Operator the right choice over a Helm chart?

---

<details>
<summary><strong>✅ Solution</strong> (try the tasks first — install needs cluster-admin)</summary>

```bash
# 1. Find it
oc get packagemanifests -n openshift-marketplace | grep -i postgres
oc describe packagemanifest <postgres-operator> -n openshift-marketplace | sed -n '/Channels/,/Default/p'

# 2. (admin) OperatorGroup + Subscription
oc apply -f - <<'EOF'
apiVersion: operators.coreos.com/v1
kind: OperatorGroup
metadata: { name: mod9-og, namespace: mod9-ex }
spec: { targetNamespaces: [mod9-ex] }
---
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata: { name: postgres, namespace: mod9-ex }
spec:
  channel: stable
  name: <postgres-operator>
  source: certified-operators
  sourceNamespace: openshift-marketplace
  installPlanApproval: Automatic
EOF

# 3. Confirm
oc get subscription,installplan -n mod9-ex
oc get csv -n mod9-ex                     # PHASE Succeeded

# 4. CRD + explain
oc get crd | grep -i postgres
oc explain postgrescluster.spec | sed -n '1,8p'

# 5. Create a CR
oc apply -f - <<'EOF'
apiVersion: postgres-operator.crunchydata.com/v1beta1
kind: PostgresCluster
metadata: { name: cdr-store, namespace: mod9-ex }
spec:
  postgresVersion: 16
  instances: [ { replicas: 3 } ]
  backups: { pgbackrest: { repos: [ { name: repo1 } ] } }
EOF
oc get postgrescluster,pods -n mod9-ex

# Cleanup
oc delete postgrescluster cdr-store -n mod9-ex
oc delete subscription postgres -n mod9-ex ; oc delete operatorgroup mod9-og -n mod9-ex
```

**Representative output** *(requires a cluster; install needs admin — OCP 4.18):*

```
NAME                      DISPLAY            VERSION   PHASE
postgresoperator.v5.x.y   Crunchy Postgres   5.x.y     Succeeded
postgresclusters.postgres-operator.crunchydata.com   ...
postgrescluster.../cdr-store created
cdr-store-instance1-0   4/4   Running
cdr-store-instance1-1   4/4   Running
cdr-store-instance1-2   4/4   Running
```

**Key point:** a **Subscription** → **InstallPlan** → **CSV** (the installed Operator, at
`PHASE=Succeeded`) which adds a **CRD**. You then declare a small **CR** and the Operator
builds and operates a full 3-instance database — the win over hand-written manifests/Helm
for stateful software.
</details>

---

> **◐ Partially verified:** `oc` syntax is standard 4.22, but every step **requires a live
> OpenShift cluster** (install needs **cluster-admin**) and was not run at authoring
> (cluster asleep). Output is **representative of OpenShift 4.18** with a Postgres Operator
> (names/versions vary by catalog). Validate live as an admin when the cluster is up.
