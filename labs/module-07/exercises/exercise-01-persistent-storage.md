# Exercise 1 — Persistent Storage

> **Scenario:** Give the **CDR archive** durable storage. Create a PVC, let a StorageClass
> provision it, mount it in a pod, write a record, and prove the data survives the pod.

| | |
|---|---|
| **Practice** | PVC, dynamic provisioning, `oc set volume`, persistence across pods, access mode / reclaim policy |
| **Maps to** | Guide §3, §4, §5 · Visualization 01 · Demo 1 |
| **Difficulty** | ⭐ Beginner · ~20 min · normal user OK (needs a default StorageClass) |

---

## Tasks

1. List StorageClasses and note which is **(default)**.
2. Create a **PVC** `cdr-archive` (1Gi, ReadWriteOnce, default class). Observe its
   initial **STATUS**.
3. Create a deployment `cdr-writer` (`ubi9/httpd-24`) and **mount** the PVC at `/data`.
   Confirm the PVC becomes **Bound** and a PV was auto-created.
4. **Write** a CDR into `/data`, then **delete the pod** and confirm the data is still
   there on the replacement pod.
5. Show the PVC's **access mode** and the PV's **reclaim policy**, and explain what each
   means for the CDR archive.

> **Hint (Task 2):** with a `WaitForFirstConsumer` class the PVC stays **Pending** until a
> pod uses it — that's expected.

> **Hint (Task 3):** `oc set volume deploy/cdr-writer --add --type=pvc --claim-name=cdr-archive --mount-path=/data`.

---

## Validation

```bash
# Task 3 — Bound + PV exists
oc get pvc cdr-archive        # STATUS Bound
oc get pv | grep cdr-archive

# Task 4 — data survives (should print the same line after pod deletion)
NEWPOD=$(oc get pods -l app=cdr-writer -o jsonpath='{.items[0].metadata.name}')
oc exec "$NEWPOD" -- cat /data/cdr.log

# Task 5 — access mode + reclaim policy
oc get pvc cdr-archive -o jsonpath='{.spec.accessModes}{"\n"}'
oc get pv $(oc get pvc cdr-archive -o jsonpath='{.spec.volumeName}') -o jsonpath='{.spec.persistentVolumeReclaimPolicy}{"\n"}'
```

---

## Reflection

- Who created the PV, and did you ever write one?
- Why did the CDR file survive deleting the pod?
- With reclaim policy `Delete`, what happens to the data if you delete the PVC — and how
  would you protect it?

---

<details>
<summary><strong>✅ Solution</strong> (try the tasks first)</summary>

```bash
# 1. StorageClasses
oc get storageclass

# 2. PVC (Pending until consumed, if WaitForFirstConsumer)
cat <<'EOF' | oc apply -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata: { name: cdr-archive }
spec:
  accessModes: [ReadWriteOnce]
  resources: { requests: { storage: 1Gi } }
EOF
oc get pvc cdr-archive

# 3. Deploy + mount → binds
oc create deployment cdr-writer --image=registry.access.redhat.com/ubi9/httpd-24:latest
oc set volume deploy/cdr-writer --add --name=archive --type=pvc \
  --claim-name=cdr-archive --mount-path=/data
oc rollout status deploy/cdr-writer
oc get pvc cdr-archive        # Bound
oc get pv | grep cdr-archive

# 4. Write, delete pod, re-read
POD=$(oc get pods -l app=cdr-writer -o jsonpath='{.items[0].metadata.name}')
oc exec "$POD" -- bash -c 'echo "cdr-001,+9665...,120s" > /data/cdr.log'
oc delete pod "$POD"; oc rollout status deploy/cdr-writer
NEWPOD=$(oc get pods -l app=cdr-writer -o jsonpath='{.items[0].metadata.name}')
oc exec "$NEWPOD" -- cat /data/cdr.log        # same data

# 5. Access mode + reclaim policy
oc get pvc cdr-archive -o jsonpath='{.spec.accessModes}{"\n"}'
oc get pv $(oc get pvc cdr-archive -o jsonpath='{.spec.volumeName}') \
  -o jsonpath='{.spec.persistentVolumeReclaimPolicy}{"\n"}'

# Cleanup
oc delete deployment cdr-writer ; oc delete pvc cdr-archive
```

**Representative output** *(requires a cluster — OCP 4.18):*

```
cdr-archive   Bound    pvc-4f1c9a20-...   1Gi   RWO   gp3-csi
cdr-001,+9665...,120s          # survives the pod
["ReadWriteOnce"]
Delete
```

**Key point:** you wrote only a **PVC**; a **StorageClass** dynamically provisioned the
**PV** and bound it. The volume's lifecycle is independent of the pod, so the CDR survived
deletion. **RWO** = one node; **reclaim=Delete** means deleting the PVC destroys the data —
use `Retain` for anything you can't afford to lose.
</details>

---

> **◐ Partially verified:** `oc set volume --help` confirmed with **oc 4.22**; PVC/PV
> commands **require a live OpenShift cluster** (not runnable at authoring — cluster
> asleep). Output is **representative of OpenShift 4.18**; a **normal user (learner25) can
> run all of this** in their own project once the cluster is up. Persistence and
> `WaitForFirstConsumer` `Pending→Bound` are real behaviours.
