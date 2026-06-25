# Demo 4 — Configuration & Storage

> **Scenario:** The **tariff-catalog** needs runtime settings (plan tier, data
> quota, roaming flag) and a database credential — none of which belong baked into
> the image. Separately, the **CDR archive** must keep call records even when the
> pod writing them is destroyed. We inject config with a **ConfigMap** and a
> **Secret**, then prove data **survives pod deletion** with a
> **PersistentVolumeClaim**.

| | |
|---|---|
| **Concepts reinforced** | ConfigMap (env + mounted files) · Secret (base64 ≠ encryption) · PVC · StorageClass · `WaitForFirstConsumer` · persistence |
| **Maps to** | Guide §10 (Config) & §11 (Storage) · Exercise 4 |
| **Time** | ~30 minutes |
| **Cluster** | minikube; single node is fine |

---

> **⎈ Same on OpenShift:** identical ConfigMap / Secret / PVC objects. OpenShift
> adds tighter default RBAC and SCCs around Secrets and bundles storage (OpenShift
> Data Foundation) with default StorageClasses — but the YAML here is unchanged.

## Talking points to open with

- A good image is **immutable and environment-agnostic** — the same image runs in
  dev and prod; only the injected config differs.
- **ConfigMap** = non-sensitive config; **Secret** = sensitive — but a Secret is
  **base64-encoded, not encrypted**.
- A container's filesystem is ephemeral. A **PVC** is the thing that *remembers*,
  and its lifecycle is independent of any pod.

---

## Step 1 — Create a ConfigMap from literals

```bash
kubectl create configmap tariff-config \
  --from-literal=PLAN_TIER=gold \
  --from-literal=DATA_QUOTA_GB=50 \
  --from-literal=ROAMING=enabled
kubectl get configmap tariff-config -o yaml | sed -n '1,12p'
```

**Expected output:**

```
configmap/tariff-config created
apiVersion: v1
data:
  DATA_QUOTA_GB: "50"
  PLAN_TIER: gold
  ROAMING: enabled
kind: ConfigMap
metadata:
  creationTimestamp: "2026-06-25T04:46:03Z"
  name: tariff-config
  namespace: mod3-demos
```

> **Narrate:** Three key/value pairs, stored in the cluster as plain text under
> `data`. Nothing is consuming it yet — a ConfigMap is just a bag of settings until
> a pod asks for it.

---

## Step 2 — Create a Secret (and see it's only base64)

```bash
kubectl create secret generic billing-secret \
  --from-literal=DB_USER=mobily_app \
  --from-literal=DB_PASSWORD='S3cr3t-Pa55'
kubectl get secret billing-secret -o jsonpath='{.data.DB_PASSWORD}'; echo
kubectl get secret billing-secret -o jsonpath='{.data.DB_PASSWORD}' | base64 -d; echo
```

**Expected output:**

```
secret/billing-secret created
UzNjcjN0LVBhNTU=
S3cr3t-Pa55
```

> **Narrate:** The stored value `UzNjcjN0LVBhNTU=` *looks* protected — but one
> `base64 -d` reveals `S3cr3t-Pa55`. **Secrets are encoded, not encrypted.** Real
> protection comes from RBAC (who can read them), etcd encryption-at-rest, and
> keeping them out of Git. The password here is a **fictional placeholder** — never
> commit a real one.

---

## Step 3 — Inject both into a pod (env + mounted files + secretKeyRef)

```bash
cat > tariff-consumer.yaml <<'EOF'
apiVersion: v1
kind: Pod
metadata: { name: tariff-consumer, labels: { app: tariff-consumer } }
spec:
  containers:
    - name: app
      image: registry.access.redhat.com/ubi9/ubi-minimal:latest
      command: ["sh","-c","echo PLAN_TIER=$PLAN_TIER QUOTA=$DATA_QUOTA_GB ROAMING=$ROAMING; echo DB_USER=$DB_USER; echo '--- mounted files ---'; ls /etc/tariff; echo '--- ROAMING file ---'; cat /etc/tariff/ROAMING; echo; sleep 60"]
      envFrom:
        - configMapRef: { name: tariff-config }
      env:
        - name: DB_USER
          valueFrom:
            secretKeyRef: { name: billing-secret, key: DB_USER }
      volumeMounts:
        - { name: cfg, mountPath: /etc/tariff }
  volumes:
    - name: cfg
      configMap: { name: tariff-config }
  restartPolicy: Never
EOF
kubectl apply -f tariff-consumer.yaml
kubectl wait --for=condition=Ready pod/tariff-consumer --timeout=60s
kubectl logs tariff-consumer
```

**Expected output:**

```
pod/tariff-consumer created
pod/tariff-consumer condition met
PLAN_TIER=gold QUOTA=50 ROAMING=enabled
DB_USER=mobily_app
--- mounted files ---
DATA_QUOTA_GB
PLAN_TIER
ROAMING
--- ROAMING file ---
enabled
```

> **Narrate:** One ConfigMap delivered **two ways at once** — `envFrom` turned every
> key into an environment variable, and the **volume mount** turned every key into a
> *file* under `/etc/tariff/`. The Secret's `DB_USER` came in via `secretKeyRef`
> (one specific key). Env vars suit simple flags; mounted files suit whole config
> files an app reads from disk (`nginx.conf`, `application.yaml`).

```bash
kubectl delete pod tariff-consumer --force --grace-period=0
```

---

## Step 4 — A PersistentVolumeClaim starts Pending

First, look at the StorageClass the cluster provisions from:

```bash
kubectl get storageclass
```

**Expected output:**

```
NAME                 PROVISIONER             RECLAIMPOLICY   VOLUMEBINDINGMODE      ALLOWVOLUMEEXPANSION   AGE
standard (default)   rancher.io/local-path   Delete          WaitForFirstConsumer   false                  84m
```

Now request storage:

```bash
cat > cdr-archive-pvc.yaml <<'EOF'
apiVersion: v1
kind: PersistentVolumeClaim
metadata: { name: cdr-archive }
spec:
  accessModes: ["ReadWriteOnce"]
  resources: { requests: { storage: 1Gi } }
EOF
kubectl apply -f cdr-archive-pvc.yaml
kubectl get pvc cdr-archive
```

**Expected output:**

```
persistentvolumeclaim/cdr-archive created
NAME          STATUS    VOLUME   CAPACITY   ACCESS MODES   STORAGECLASS   AGE
cdr-archive   Pending                                      standard       0s
```

> **Narrate:** The claim is **Pending** on purpose. The StorageClass uses
> `WaitForFirstConsumer` — it won't provision the disk until a pod actually mounts
> the claim, so the volume lands on the same node as the pod. No admin
> pre-provisioned anything; this is **dynamic provisioning**.

---

## Step 5 — Write data, then destroy the pod

```bash
cat > cdr-writer.yaml <<'EOF'
apiVersion: v1
kind: Pod
metadata: { name: cdr-writer }
spec:
  containers:
    - name: w
      image: registry.access.redhat.com/ubi9/ubi-minimal:latest
      command: ["sh","-c","echo '8821001234,8821005678,2026-06-25T10:00:00,180,VOICE' >> /data/cdr.log; echo WROTE:; cat /data/cdr.log; sleep 300"]
      volumeMounts: [ { name: d, mountPath: /data } ]
  volumes:
    - name: d
      persistentVolumeClaim: { claimName: cdr-archive }
  restartPolicy: Never
EOF
kubectl apply -f cdr-writer.yaml
kubectl wait --for=condition=Ready pod/cdr-writer --timeout=70s
kubectl logs cdr-writer
kubectl get pvc cdr-archive
kubectl delete pod cdr-writer --force --grace-period=0
```

**Expected output:**

```
pod/cdr-writer created
pod/cdr-writer condition met
WROTE:
8821001234,8821005678,2026-06-25T10:00:00,180,VOICE
NAME          STATUS   VOLUME              CAPACITY   ACCESS MODES   STORAGECLASS
cdr-archive   Bound    pvc-6b9b5044-...    1Gi        RWO            standard
pod "cdr-writer" force deleted
```

> **Narrate:** The moment the writer mounted the claim, the provisioner created a PV
> and the PVC flipped **Pending → Bound**. The pod wrote one CDR, then we
> **destroyed the pod entirely**. A container's own filesystem would be gone now —
> but the data lives on the PV, which is independent of the pod.

---

## Step 6 — Prove the data survived

A brand-new pod mounts the **same PVC**:

```bash
cat > cdr-reader.yaml <<'EOF'
apiVersion: v1
kind: Pod
metadata: { name: cdr-reader }
spec:
  containers:
    - name: r
      image: registry.access.redhat.com/ubi9/ubi-minimal:latest
      command: ["sh","-c","echo 'DATA SURVIVED POD DELETION:'; cat /data/cdr.log; sleep 300"]
      volumeMounts: [ { name: d, mountPath: /data } ]
  volumes:
    - name: d
      persistentVolumeClaim: { claimName: cdr-archive }
  restartPolicy: Never
EOF
kubectl apply -f cdr-reader.yaml
kubectl wait --for=condition=Ready pod/cdr-reader --timeout=70s
kubectl logs cdr-reader
```

**Expected output:**

```
pod/cdr-reader created
pod/cdr-reader condition met
DATA SURVIVED POD DELETION:
8821001234,8821005678,2026-06-25T10:00:00,180,VOICE
```

> **Narrate:** A *different* pod, same PVC, and the CDR is right there. This is the
> dividing line between stateless and stateful: **pods are cattle; the PVC is the
> thing that remembers.** Bind your database, queue, or archive to a PVC and it
> outlives any pod that mounts it.

---

## Step 7 — Cleanup

```bash
kubectl delete pod cdr-reader --force --grace-period=0
kubectl delete pvc cdr-archive
kubectl delete configmap tariff-config
kubectl delete secret billing-secret
```

**Expected output:**

```
pod "cdr-reader" force deleted
persistentvolumeclaim "cdr-archive" deleted
configmap "tariff-config" deleted
secret "billing-secret" deleted
```

> **Note:** because the StorageClass reclaim policy is `Delete`, deleting the PVC
> also removes the underlying PV and its data. Keep that in mind for real archives.

---

## Wrap-up questions to pose

1. Name the two ways a ConfigMap can be delivered into a pod, and when you'd choose
   each.
2. Is a Secret encrypted? What actually protects it?
3. Why did the PVC sit **Pending** until a pod used it?
4. The reader pod read data the writer pod left behind. What object made that
   possible, and what is its lifecycle tied to?

---

> **✅ Verified:** kubectl 1.34 · Kubernetes 1.33 (3-node kind, equivalent plain
> Kubernetes) · images `ubi9/ubi-minimal`. ConfigMap (env + mounted files), Secret
> (base64 round-trip), the consumer pod logs, the StorageClass, PVC Pending→Bound,
> and the writer→delete→reader persistence proof were all run live and the output
> above is from that run.
