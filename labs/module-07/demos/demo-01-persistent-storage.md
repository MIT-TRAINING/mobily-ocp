# Demo 1 — Persistent Storage (PVC, StorageClass, Persistence)

> **Scenario:** Mobily's **CDR archive** must survive pod restarts, node drains, and
> upgrades. We create a **PVC**, watch a **StorageClass** dynamically provision and bind
> a **PV**, mount it, write CDRs, then **delete the pod** and prove the data is still
> there. Finally we look at **access modes** and **reclaim policy** — the two settings
> that bite in production.

| | |
|---|---|
| **Concepts reinforced** | PVC → StorageClass → PV binding · dynamic provisioning · persistence across pods · access modes · reclaim policy |
| **Maps to** | Guide §3, §4, §5 · Visualization 01 · Exercise 1 |
| **Time** | ~30 minutes |
| **Cluster** | Shared OCP 4.18 — a normal project user can do all of this (needs a **default StorageClass**) |

---

> **⎈ Kubernetes equivalent:** PV/PVC/StorageClass are pure Kubernetes — identical to
> `kubectl`. OpenShift adds no new object here.

## Talking points to open with

- A pod's filesystem is disposable; a **PVC** gives it durable storage with an
  independent lifecycle.
- You write only the **PVC**; a **StorageClass** provisions the **PV** automatically.
- The two settings that surprise people: **access mode** (RWO = one node) and **reclaim
  policy** (Delete = deleting the PVC destroys the data).

---

## Step 1 — See the available StorageClasses

```bash
oc get storageclass
```

**Expected output** *(requires a cluster — representative of OCP 4.18 on AWS):*

```
NAME            PROVISIONER             RECLAIMPOLICY   VOLUMEBINDINGMODE      ALLOWVOLUMEEXPANSION   AGE
gp3-csi (default)  ebs.csi.aws.com      Delete          WaitForFirstConsumer   true                   40d
gp2-csi         ebs.csi.aws.com         Delete          WaitForFirstConsumer   true                   40d
```

> **Narrate:** The `(default)` class is used when a PVC names no class. `RECLAIMPOLICY
> Delete` means deleting a PVC destroys its disk; `WaitForFirstConsumer` means the disk
> is created only once a pod is scheduled — in the pod's zone.

---

## Step 2 — Create a PVC and watch it bind

```bash
cat <<'EOF' | oc apply -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata: { name: cdr-archive }
spec:
  accessModes: [ReadWriteOnce]
  resources: { requests: { storage: 1Gi } }
EOF
oc get pvc cdr-archive
```

**Expected output** *(requires a cluster — representative):*

```
persistentvolumeclaim/cdr-archive created
NAME          STATUS    VOLUME   CAPACITY   ACCESS MODES   STORAGECLASS   AGE
cdr-archive   Pending                                      gp3-csi        3s
```

> **Narrate:** `Pending` — with `WaitForFirstConsumer`, the PV isn't provisioned until a
> pod uses the PVC. On an `Immediate` class it would bind right away. No pod yet, so it
> waits. That's expected, not an error.

---

## Step 3 — Mount it in a pod; provisioning completes

```bash
oc create deployment cdr-writer --image=registry.access.redhat.com/ubi9/httpd-24:latest
oc set volume deployment/cdr-writer --add --name=archive \
  --type=pvc --claim-name=cdr-archive --mount-path=/data
oc rollout status deploy/cdr-writer
oc get pvc cdr-archive      # now Bound
oc get pv                   # the auto-provisioned PV
```

**Expected output** *(requires a cluster — representative):*

```
deployment.apps/cdr-writer created
info: ... volume updated
deployment "cdr-writer" successfully rolled out
NAME          STATUS   VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS
cdr-archive   Bound    pvc-4f1c9a20-...                           1Gi        RWO            gp3-csi
NAME                                       CAPACITY   RECLAIM POLICY   STATUS   CLAIM
pvc-4f1c9a20-...                           1Gi        Delete           Bound    mod7-demos/cdr-archive
```

> **Narrate:** The moment a pod consumed the PVC, the CSI provisioner made a real disk,
> wrapped it as a **PV**, and **bound** it — status `Bound`. We never wrote a PV; that's
> dynamic provisioning. The PV is cluster-scoped and names its `CLAIM`.

---

## Step 4 — Write data, then delete the pod

```bash
POD=$(oc get pods -l app=cdr-writer -o jsonpath='{.items[0].metadata.name}')
oc exec "$POD" -- bash -c 'echo "cdr-001,+9665...,120s" > /data/cdr.log; cat /data/cdr.log'
oc delete pod "$POD"                       # the ReplicaSet makes a new pod
oc rollout status deploy/cdr-writer
NEWPOD=$(oc get pods -l app=cdr-writer -o jsonpath='{.items[0].metadata.name}')
oc exec "$NEWPOD" -- cat /data/cdr.log     # data is STILL there
```

**Expected output** *(requires a cluster — representative):*

```
cdr-001,+9665...,120s
pod "cdr-writer-...-abcde" deleted
deployment "cdr-writer" successfully rolled out
cdr-001,+9665...,120s        <- same data on a brand-new pod
```

> **Narrate:** New pod, new name — **same file**. The PVC re-attached to the new pod and
> the CDRs are intact. Had we used `emptyDir` or the container filesystem, they'd be
> gone. *This* is persistence.

---

## Step 5 — Access modes & reclaim policy (discuss + inspect)

```bash
oc get pvc cdr-archive -o jsonpath='accessModes={.spec.accessModes} SC={.spec.storageClassName}{"\n"}'
oc get pv $(oc get pvc cdr-archive -o jsonpath='{.spec.volumeName}') \
  -o jsonpath='reclaimPolicy={.spec.persistentVolumeReclaimPolicy}{"\n"}'
```

**Expected output** *(requires a cluster — representative):*

```
accessModes=[ReadWriteOnce] SC=gp3-csi
reclaimPolicy=Delete
```

> **Narrate:** **RWO** = read-write by one *node* (fine for a single writer; use **RWX**
> file storage for multi-node writers). **reclaimPolicy=Delete** = deleting this PVC
> **destroys the disk and the CDRs**. For data you can't lose by accident, use a
> StorageClass/PV with **Retain**, or protect the PVC.

---

## Step 6 — Cleanup

```bash
oc delete deployment cdr-writer
oc delete pvc cdr-archive      # with Delete policy, the PV + disk are destroyed too
```

**Expected output** *(requires a cluster — representative):*

```
deployment.apps "cdr-writer" deleted
persistentvolumeclaim "cdr-archive" deleted
```

> **Narrate:** Deleting the PVC (Delete policy) cascades to the PV and the backing disk —
> a clean teardown, but a reminder that an accidental `oc delete pvc` is an accidental
> data loss. Guard important claims.

---

## Wrap-up questions to pose

1. Why did the PVC sit `Pending` until a pod used it?
2. Who created the PV — and did you ever write one?
3. After deleting the pod, why was the CDR file still there?
4. With reclaim policy `Delete`, what happens to the data when you delete the PVC — and
   how would you prevent that?

---

> **◐ Partially verified:** the `oc set volume --help` syntax was confirmed with **oc
> 4.22**; the PVC/PV/StorageClass commands **require a live OpenShift cluster** and were
> not runnable at authoring time (cluster asleep). Output is **representative of OpenShift
> 4.18**; run as **learner25** (a normal user can do all of Demo 1) to capture real
> Cluster/PV names. `WaitForFirstConsumer`-driven `Pending→Bound` and PVC persistence are
> real, documented behaviours.
