# Demo 1 — Install an Operator via OLM

> **Scenario:** Mobily's **CDR datastore** needs a production PostgreSQL with backups and
> failover. Rather than hand-roll a StatefulSet, we install a **PostgreSQL Operator** from
> **OperatorHub**, watch OLM create the **Subscription → InstallPlan → CSV**, then deploy a
> database by creating a **Custom Resource**.

| | |
|---|---|
| **Concepts reinforced** | OperatorHub · Subscription (channel + approval) · InstallPlan · CSV · OperatorGroup scope · Custom Resource |
| **Maps to** | Guide §8, §9, §10, §11 · Visualization 01 · Exercise 1 |
| **Time** | ~30 minutes |
| **Cluster** | Shared OCP 4.18 — installing an Operator needs **cluster-admin** (instructor-led) |

---

> **⎈ Kubernetes equivalent:** OLM/OperatorHub/Subscription/CSV are OpenShift's packaging
> of the upstream Operator Framework. `oc get`/`describe`/`apply` are standard.

> ⚠️ **Cluster-admin required** to install a cluster-scoped Operator. Participants observe;
> the CR creation (Step 5) can be done by a project user once the Operator + CRDs exist.

## Talking points to open with

- For complex, stateful software, an **Operator** beats manifests/Helm — it operates the
  software day-2 (backup/failover/upgrade).
- **OLM** turns a **Subscription** into a running Operator; **OperatorHub** is its catalog.
- You then use the Operator by creating a **Custom Resource**, not raw objects.

---

## Step 1 — Find the Operator in the catalog

```bash
oc get packagemanifests -n openshift-marketplace | grep -i postgres | head
oc describe packagemanifest <postgres-operator> -n openshift-marketplace | sed -n '/Channels/,/Default Channel/p'
```

**Expected output** *(requires a cluster — representative of OCP 4.18):*

```
crunchy-postgres-operator   Certified Operators   40d
postgresql                  Community Operators   40d
...
Channels:
  Name:           stable
  Current CSV:    postgresoperator.v5.x.y
Default Channel:  stable
```

> **Narrate:** `packagemanifests` is the CLI view of OperatorHub. Each entry lists
> **channels** and **install modes** — the choices the console's Install form exposes.

---

## Step 2 — Subscribe (console or YAML)

```bash
# Console: Operators → OperatorHub → choose the operator → channel + install mode + approval → Install.
# CLI equivalent (cluster-admin): an OperatorGroup (scope) + a Subscription.
oc apply -f - <<'EOF'
apiVersion: operators.coreos.com/v1
kind: OperatorGroup
metadata: { name: mod9-og, namespace: mod9-demos }
spec: { targetNamespaces: [mod9-demos] }
---
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata: { name: postgres, namespace: mod9-demos }
spec:
  channel: stable
  name: <postgres-operator>
  source: certified-operators
  sourceNamespace: openshift-marketplace
  installPlanApproval: Automatic
EOF
```

**Expected output** *(requires cluster-admin — representative):*

```
operatorgroup.operators.coreos.com/mod9-og created
subscription.operators.coreos.com/postgres created
```

> **Narrate:** The **Subscription** is your request (package + channel + approval). The
> **OperatorGroup** scopes it to this namespace. In **Manual** approval you'd approve the
> InstallPlan next; **Automatic** proceeds.

---

## Step 3 — Watch OLM install it

```bash
oc get subscription postgres -n mod9-demos
oc get installplan -n mod9-demos
oc get csv -n mod9-demos                 # PHASE goes Installing → Succeeded
```

**Expected output** *(requires a cluster — representative):*

```
NAME       PACKAGE              SOURCE                CHANNEL
postgres   <postgres-operator>  certified-operators   stable

NAME            CSV                       APPROVAL    APPROVED
install-abcde   postgresoperator.v5.x.y   Automatic   true

NAME                      DISPLAY               VERSION   PHASE
postgresoperator.v5.x.y   Crunchy Postgres...   5.x.y     Succeeded
```

> **Narrate:** Subscription → **InstallPlan** → **CSV**. The CSV (`ClusterServiceVersion`)
> is the installed Operator — its version, deployment, CRDs and RBAC. **PHASE=Succeeded**
> means it's healthy and its pod is running.

---

## Step 4 — The Operator added CRDs

```bash
oc get crd | grep -i postgres
oc explain postgrescluster.spec | sed -n '1,8p'
```

**Expected output** *(requires a cluster — representative):*

```
postgresclusters.postgres-operator.crunchydata.com   2025-...
GROUP:      postgres-operator.crunchydata.com
KIND:       PostgresCluster
VERSION:    v1beta1
FIELDS:
  instances  <[]Object>
  backups    <Object>
  ...
```

> **Narrate:** Installing the Operator **extended the API** with a `PostgresCluster` kind.
> That CRD is how you'll declare a database — no StatefulSet by hand.

---

## Step 5 — Use it: create a Custom Resource

```bash
oc apply -f - <<'EOF'
apiVersion: postgres-operator.crunchydata.com/v1beta1
kind: PostgresCluster
metadata: { name: cdr-store, namespace: mod9-demos }
spec:
  postgresVersion: 16
  instances: [ { replicas: 3 } ]
  backups: { pgbackrest: { repos: [ { name: repo1 } ] } }
EOF
oc get postgrescluster -n mod9-demos
oc get pods -n mod9-demos -l postgres-operator.crunchydata.com/cluster=cdr-store
```

**Expected output** *(requires a cluster + installed Operator — representative):*

```
postgrescluster.postgres-operator.crunchydata.com/cdr-store created
NAME        AGE
cdr-store   30s
NAME                    READY   STATUS
cdr-store-instance1-0   4/4     Running
cdr-store-instance1-1   4/4     Running
cdr-store-instance1-2   4/4     Running
cdr-store-repo-host-0   2/2     Running
```

> **Narrate:** ~8 lines of CR became a **3-instance Postgres with backups** — StatefulSets,
> PVCs, Services, and a backup host, all managed by the Operator going forward. That's the
> payoff over manifests/Helm for stateful software.

---

## Step 6 — Cleanup

```bash
oc delete postgrescluster cdr-store -n mod9-demos
oc delete subscription postgres -n mod9-demos           # admin
oc delete csv -l operators.coreos.com/<pkg>.mod9-demos -n mod9-demos 2>/dev/null
oc delete operatorgroup mod9-og -n mod9-demos
```

**Expected output** *(representative):*

```
postgrescluster.../cdr-store deleted
subscription.../postgres deleted
operatorgroup.../mod9-og deleted
```

> **Narrate:** Delete the **CR** first (the Operator tears down the DB), then the
> Subscription/CSV/OperatorGroup to remove the Operator itself.

---

## Wrap-up questions to pose

1. What three OLM objects does a Subscription lead to, and what is the CSV?
2. What's the difference between Automatic and Manual approval?
3. After install, how do you actually create a database — and what did you *not* have to
   write?
4. Why an Operator here instead of a Helm chart?

---

> **◐ Partially verified:** `oc explain`/`oc get` **syntax** is standard `oc 4.22`, but
> every step **requires a live OpenShift cluster** (installing an Operator needs
> **cluster-admin**) and was not run at authoring (cluster asleep). Output is
> **representative of OpenShift 4.18** with a Crunchy/community Postgres Operator (exact
> names/versions vary by catalog). Validate live as an admin when the cluster is up.
