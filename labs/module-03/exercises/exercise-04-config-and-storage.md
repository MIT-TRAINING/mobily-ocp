# Exercise 4 — Config & Storage

> **Scenario:** The **tariff-catalog** needs runtime settings and a DB credential
> injected (not baked into the image), and the **CDR archive** must retain call
> records even when the writing pod is destroyed. You'll wire a ConfigMap and Secret
> into a pod, then prove data survives a pod's death with a PersistentVolumeClaim.

| | |
|---|---|
| **Practice** | ConfigMap (env + files), Secret (base64), PVC, StorageClass, persistence across pods |
| **Maps to** | Guide §10–11 · Demo 4 |
| **Difficulty** | ⭐⭐ Intermediate · ~30 min · single-node OK |

---

## Tasks

1. Create a ConfigMap **`tariff-config`** with `PLAN_TIER=gold`, `DATA_QUOTA_GB=50`,
   `ROAMING=enabled`.
2. Create a Secret **`billing-secret`** with `DB_USER=mobily_app` and a placeholder
   `DB_PASSWORD`. Then **prove** the stored password is only base64 by decoding it.
3. Run a pod that consumes the ConfigMap **both** as environment variables (`envFrom`)
   **and** as mounted files, plus the Secret's `DB_USER` via `secretKeyRef`. Confirm
   from the pod's logs that all values arrived.
4. Create a **1Gi PVC** named `cdr-archive` and observe it sits **Pending** (the
   default StorageClass is `WaitForFirstConsumer`).
5. Run a **writer** pod that appends a CDR line to the PVC, then **delete that pod**.
6. Run a **new reader** pod mounting the **same PVC** and confirm the CDR line is
   still there.

> **Hint (Task 2):** `kubectl get secret billing-secret -o jsonpath='{.data.DB_PASSWORD}' | base64 -d`.

> **Hint (Task 3):** combine `envFrom: [configMapRef]`, a `secretKeyRef` env, and a
> `configMap` volume mounted at a path — see the solution if stuck.

---

## Validation

```bash
# Task 2 — base64 decodes straight back to your placeholder
kubectl get secret billing-secret -o jsonpath='{.data.DB_PASSWORD}' | base64 -d; echo

# Task 3 — the pod's logs show env values, mounted file names, and DB_USER
kubectl logs tariff-consumer

# Task 4 — PVC Pending until consumed
kubectl get pvc cdr-archive       # STATUS Pending

# Task 6 — reader pod prints the line the writer left behind
kubectl logs cdr-reader
```

---

## Reflection

- What actually protects a Secret, given base64 is not encryption?
- Why did the PVC stay **Pending** until a pod used it?
- The reader pod read what the writer wrote, after the writer was deleted. Which
  object made that possible, and what is *its* lifecycle tied to?

---

<details>
<summary><strong>✅ Solution</strong> (try the tasks first)</summary>

```bash
# 1. ConfigMap
kubectl create configmap tariff-config \
  --from-literal=PLAN_TIER=gold --from-literal=DATA_QUOTA_GB=50 --from-literal=ROAMING=enabled

# 2. Secret + prove it's only base64 (password is a fictional placeholder)
kubectl create secret generic billing-secret \
  --from-literal=DB_USER=mobily_app --from-literal=DB_PASSWORD='S3cr3t-Pa55'
kubectl get secret billing-secret -o jsonpath='{.data.DB_PASSWORD}' | base64 -d; echo   # S3cr3t-Pa55

# 3. Pod consuming both
cat > tariff-consumer.yaml <<'EOF'
apiVersion: v1
kind: Pod
metadata: { name: tariff-consumer, labels: { app: tariff-consumer } }
spec:
  containers:
    - name: app
      image: registry.access.redhat.com/ubi9/ubi-minimal:latest
      command: ["sh","-c","echo PLAN_TIER=$PLAN_TIER QUOTA=$DATA_QUOTA_GB ROAMING=$ROAMING; echo DB_USER=$DB_USER; echo '--- mounted files ---'; ls /etc/tariff; sleep 60"]
      envFrom: [ { configMapRef: { name: tariff-config } } ]
      env:
        - name: DB_USER
          valueFrom: { secretKeyRef: { name: billing-secret, key: DB_USER } }
      volumeMounts: [ { name: cfg, mountPath: /etc/tariff } ]
  volumes:
    - name: cfg
      configMap: { name: tariff-config }
  restartPolicy: Never
EOF
kubectl apply -f tariff-consumer.yaml
kubectl wait --for=condition=Ready pod/tariff-consumer --timeout=60s
kubectl logs tariff-consumer
kubectl delete pod tariff-consumer --force --grace-period=0

# 4. PVC (stays Pending — WaitForFirstConsumer)
kubectl apply -f - <<'EOF'
apiVersion: v1
kind: PersistentVolumeClaim
metadata: { name: cdr-archive }
spec: { accessModes: ["ReadWriteOnce"], resources: { requests: { storage: 1Gi } } }
EOF
kubectl get pvc cdr-archive       # Pending

# 5. Writer pod, then delete it
kubectl apply -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata: { name: cdr-writer }
spec:
  containers:
    - name: w
      image: registry.access.redhat.com/ubi9/ubi-minimal:latest
      command: ["sh","-c","echo '8821001234,8821005678,2026-06-25T10:00:00,180,VOICE' >> /data/cdr.log; cat /data/cdr.log; sleep 300"]
      volumeMounts: [ { name: d, mountPath: /data } ]
  volumes: [ { name: d, persistentVolumeClaim: { claimName: cdr-archive } } ]
  restartPolicy: Never
EOF
kubectl wait --for=condition=Ready pod/cdr-writer --timeout=70s
kubectl get pvc cdr-archive       # now Bound
kubectl delete pod cdr-writer --force --grace-period=0

# 6. New reader pod, same PVC
kubectl apply -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata: { name: cdr-reader }
spec:
  containers:
    - name: r
      image: registry.access.redhat.com/ubi9/ubi-minimal:latest
      command: ["sh","-c","echo 'DATA SURVIVED POD DELETION:'; cat /data/cdr.log; sleep 300"]
      volumeMounts: [ { name: d, mountPath: /data } ]
  volumes: [ { name: d, persistentVolumeClaim: { claimName: cdr-archive } } ]
  restartPolicy: Never
EOF
kubectl wait --for=condition=Ready pod/cdr-reader --timeout=70s
kubectl logs cdr-reader

# Cleanup
kubectl delete pod cdr-reader --force --grace-period=0
kubectl delete pvc cdr-archive
kubectl delete configmap tariff-config
kubectl delete secret billing-secret
```

**Verified output (key lines):**

```
S3cr3t-Pa55                                    # base64 decodes right back
PLAN_TIER=gold QUOTA=50 ROAMING=enabled
DB_USER=mobily_app
--- mounted files ---
DATA_QUOTA_GB
PLAN_TIER
ROAMING
cdr-archive   Pending   ...   standard         # before a consumer
cdr-archive   Bound     ...   standard         # after the writer mounts it
DATA SURVIVED POD DELETION:
8821001234,8821005678,2026-06-25T10:00:00,180,VOICE
```

**Key point:** config and secrets decouple behaviour from the image (build once,
promote everywhere); the PVC decouples *data* from the pod — its lifecycle is
independent, so data outlives any pod that mounts it.
</details>

---

> **✅ Verified:** kubectl 1.34 · Kubernetes 1.33 (3-node kind, equivalent plain
> Kubernetes) · image `ubi9/ubi-minimal`. ConfigMap (env + files), Secret base64
> round-trip, the consumer pod logs, PVC Pending→Bound, and the
> writer→delete→reader persistence proof were all run live (the identical flow as
> Demo 4).
