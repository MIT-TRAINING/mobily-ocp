# Demo 5 — StatefulSets, DaemonSets & Jobs

> **Scenario:** Not every workload is a stateless web tier. The **CDR store** is a
> clustered database where each replica needs a stable name and its own disk; a
> **node probe** must run on every machine; and the **nightly billing rollup** runs,
> finishes, and stops. We meet the three controllers that cover those shapes —
> **StatefulSet**, **DaemonSet**, and **Job/CronJob** — and see exactly how they
> differ from a Deployment.

| | |
|---|---|
| **Concepts reinforced** | StatefulSet (stable IDs, ordered, per-pod PVC) · headless DNS · DaemonSet (one per node, taints) · Job (completions/parallelism) · CronJob |
| **Maps to** | Guide §5–7 (StatefulSets, DaemonSets, Jobs) · Exercise 5 |
| **Time** | ~30 minutes |
| **Cluster** | Demos run on single node; **DaemonSet "one per node" needs ≥2 nodes** (`minikube start --nodes 3`) |

---

> **⎈ Same on OpenShift:** all four objects are standard Kubernetes and run as `oc`
> unchanged. OpenShift itself ships dozens of DaemonSets (SDN/OVN, monitoring,
> machine-config) — you'll see them in `oc get ds -A`.

## Talking points to open with

- A Deployment's pods are *cattle* — interchangeable, randomly named. Some workloads
  need *pets*: stable identity and their own storage. That's a **StatefulSet**.
- "One pod on every node" isn't a replica count you set — it's the **DaemonSet**'s
  whole contract.
- Most controllers keep pods running forever. **Jobs** run work that *finishes*.

---

## Step 1 — A StatefulSet with stable identity and per-pod storage

```bash
cat > cdr-store.yaml <<'EOF'
apiVersion: v1
kind: Service
metadata: { name: cdr-store }
spec:
  clusterIP: None              # headless: gives each pod a DNS name
  selector: { app: cdr-store }
  ports: [ { port: 80 } ]
---
apiVersion: apps/v1
kind: StatefulSet
metadata: { name: cdr-store }
spec:
  serviceName: cdr-store
  replicas: 3
  selector: { matchLabels: { app: cdr-store } }
  template:
    metadata: { labels: { app: cdr-store } }
    spec:
      containers:
        - name: store
          image: registry.access.redhat.com/ubi9/httpd-24:latest
          ports: [ { containerPort: 8080 } ]
          volumeMounts: [ { name: data, mountPath: /var/www/html } ]
  volumeClaimTemplates:
    - metadata: { name: data }
      spec:
        accessModes: ["ReadWriteOnce"]
        resources: { requests: { storage: 256Mi } }
EOF
kubectl apply -f cdr-store.yaml
kubectl rollout status statefulset/cdr-store
```

**Expected output:**

```
service/cdr-store created
statefulset.apps/cdr-store created
Waiting for 3 pods to be ready...
Waiting for 2 pods to be ready...
Waiting for 1 pods to be ready...
partitioned roll out complete: 3 new pods have been updated...
```

> **Narrate:** Watch the readiness count tick **3 → 2 → 1** — pods come up **one at
> a time, in order**, each waiting for the previous to be Ready. A Deployment would
> start all three at once. Ordered startup is a StatefulSet guarantee.

---

## Step 2 — Stable names and one PVC per pod

```bash
kubectl get pods -l app=cdr-store
kubectl get pvc -l app=cdr-store
```

**Expected output:**

```
NAME          READY   STATUS    RESTARTS   AGE
cdr-store-0   1/1     Running   0          28s
cdr-store-1   1/1     Running   0          22s
cdr-store-2   1/1     Running   0          16s

NAME               STATUS   VOLUME             CAPACITY   ACCESS MODES   STORAGECLASS
data-cdr-store-0   Bound    pvc-4a4dc761-...   256Mi      RWO            standard
data-cdr-store-1   Bound    pvc-d27f0617-...   256Mi      RWO            standard
data-cdr-store-2   Bound    pvc-4ccda487-...   256Mi      RWO            standard
```

> **Narrate:** **Ordinal names** (`-0`, `-1`, `-2`), and the ages (28s/22s/16s)
> confirm the ordered creation. The `volumeClaimTemplates` minted **one PVC per
> pod** — `data-cdr-store-0` belongs to `cdr-store-0` *forever*. Delete and
> reschedule `cdr-store-1` and it comes back as `cdr-store-1` re-attached to
> `data-cdr-store-1`. That's identity + storage stability you cannot get from a
> Deployment.

---

## Step 3 — Stable per-pod DNS via the headless Service

```bash
kubectl run dnstest --image=registry.access.redhat.com/ubi9/ubi-minimal:latest \
  --restart=Never --command -- sleep 60
kubectl wait --for=condition=Ready pod/dnstest --timeout=60s
kubectl exec dnstest -- getent hosts cdr-store-0.cdr-store
kubectl exec dnstest -- getent hosts cdr-store-1.cdr-store
kubectl delete pod dnstest --force --grace-period=0
```

**Expected output:**

```
10.244.2.73     cdr-store-0.cdr-store.mod3-verify.svc.cluster.local
10.244.1.58     cdr-store-1.cdr-store.mod3-verify.svc.cluster.local
```

> **Narrate:** Because the Service is **headless** (`clusterIP: None`), each pod gets
> its *own* DNS name `<pod>.<service>`. This is how clustered apps find their peers —
> a replica contacting `cdr-store-0.cdr-store` to reach the primary. A normal
> Service would hand back one load-balanced IP; here we address pods individually.

---

## Step 4 — A DaemonSet: one pod per node

> **Needs ≥2 nodes to be meaningful.** On a single-node minikube you'll see exactly
> one pod; start `minikube start --nodes 3` to see the per-node behaviour below.

```bash
cat > node-probe.yaml <<'EOF'
apiVersion: apps/v1
kind: DaemonSet
metadata: { name: node-probe }
spec:
  selector: { matchLabels: { app: node-probe } }
  template:
    metadata: { labels: { app: node-probe } }
    spec:
      containers:
        - name: probe
          image: registry.access.redhat.com/ubi9/ubi-minimal:latest
          command: ["sh","-c","while true; do sleep 30; done"]
EOF
kubectl apply -f node-probe.yaml
kubectl get daemonset node-probe
kubectl get pods -l app=node-probe -o wide
```

**Expected output:**

```
daemonset.apps/node-probe created
NAME         DESIRED   CURRENT   READY   UP-TO-DATE   AVAILABLE   NODE SELECTOR   AGE
node-probe   2         2         2       2            2           <none>          12s

NAME               READY   STATUS    NODE                  ...
node-probe-jjv85   1/1     Running   mod2-verify-worker
node-probe-t788b   1/1     Running   mod2-verify-worker2
```

> **Narrate:** `DESIRED 2` — but this cluster has **three** nodes. You never set
> that number; it's the count of nodes the pod is *allowed* on. One pod landed on
> each **worker**, and none on the control-plane.

Why only the workers? The control-plane node is **tainted**:

```bash
kubectl get nodes
kubectl get node <control-plane-node> -o jsonpath='{.spec.taints}{"\n"}'
```

**Expected output:**

```
NAME                        STATUS   ROLES           AGE   VERSION
mod2-verify-control-plane   Ready    control-plane   86m   v1.33.1
mod2-verify-worker          Ready    <none>          86m   v1.33.1
mod2-verify-worker2         Ready    <none>          86m   v1.33.1

[{"effect":"NoSchedule","key":"node-role.kubernetes.io/control-plane"}]
```

> **Narrate:** The control-plane carries a `NoSchedule` **taint**, and our DaemonSet
> has no matching toleration, so no probe runs there. "One per node" really means
> "one per node the pod can tolerate." System DaemonSets (the CNI, etc.) *do* add
> that toleration so they cover control-plane nodes too.

---

## Step 5 — A Job: run-to-completion work

```bash
cat > cdr-roundup.yaml <<'EOF'
apiVersion: batch/v1
kind: Job
metadata: { name: cdr-roundup }
spec:
  completions: 3
  parallelism: 2
  template:
    spec:
      containers:
        - name: roundup
          image: registry.access.redhat.com/ubi9/ubi-minimal:latest
          command: ["sh","-c","echo aggregating CDR batch on $(hostname); sleep 3; echo done"]
      restartPolicy: Never
EOF
kubectl apply -f cdr-roundup.yaml
kubectl wait --for=condition=Complete job/cdr-roundup --timeout=90s
kubectl get job cdr-roundup
kubectl get pods -l job-name=cdr-roundup
```

**Expected output:**

```
job.batch/cdr-roundup created
job.batch/cdr-roundup condition met
NAME          STATUS     COMPLETIONS   DURATION   AGE
cdr-roundup   Complete   3/3           15s        24s

NAME                READY   STATUS      RESTARTS   AGE
cdr-roundup-4fbng   0/1     Completed   0          16s
cdr-roundup-7rcqs   0/1     Completed   0          24s
cdr-roundup-w2x7f   0/1     Completed   0          24s
```

> **Narrate:** `completions: 3, parallelism: 2` means "I need 3 successful runs,
> two at a time." The Job reached **3/3 Complete** and stopped. The pods stay in
> **Completed** (`0/1` ready) — they are *not* restarted, so you can still read
> their logs. A Job's `restartPolicy` is `Never`/`OnFailure`, never `Always`.

---

## Step 6 — A CronJob: a Job on a schedule

```bash
kubectl create cronjob nightly-billing \
  --image=registry.access.redhat.com/ubi9/ubi-minimal:latest \
  --schedule="0 2 * * *" -- sh -c "echo running nightly billing rollup"
kubectl get cronjob nightly-billing
```

**Expected output:**

```
cronjob.batch/nightly-billing created
NAME              SCHEDULE    TIMEZONE   SUSPEND   ACTIVE   LAST SCHEDULE   AGE
nightly-billing   0 2 * * *   <none>     False     0        <none>          0s
```

> **Narrate:** `0 2 * * *` = "02:00 every day." Each firing creates a fresh **Job**
> (and pods). `SUSPEND=False` means it's active; flip it to `True` to pause the
> schedule without deleting the object. This is the cluster-native replacement for
> cron-on-a-VM — with logs, retries, and history as first-class objects.

---

## Step 7 — Cleanup

```bash
kubectl delete statefulset cdr-store
kubectl delete pvc -l app=cdr-store
kubectl delete service cdr-store
kubectl delete daemonset node-probe
kubectl delete job cdr-roundup
kubectl delete cronjob nightly-billing
```

**Expected output:**

```
statefulset.apps "cdr-store" deleted
persistentvolumeclaim "data-cdr-store-0" deleted
persistentvolumeclaim "data-cdr-store-1" deleted
persistentvolumeclaim "data-cdr-store-2" deleted
service "cdr-store" deleted
daemonset.apps "node-probe" deleted
job.batch "cdr-roundup" deleted
cronjob.batch "nightly-billing" deleted
```

> **Note:** deleting a StatefulSet does **not** delete its PVCs automatically — you
> remove them explicitly (above). That's deliberate: it protects a database's data
> from an accidental `delete statefulset`.

---

## Wrap-up questions to pose

1. Two things a StatefulSet gives you that a Deployment cannot — name them.
2. The DaemonSet says `DESIRED 2` on a 3-node cluster. Why not 3?
3. Why do a Job's pods stay `Completed` instead of being cleaned up or restarted?
4. After `kubectl delete statefulset cdr-store`, is the data gone? Why or why not?

---

> **✅ Verified:** kubectl 1.34 · Kubernetes 1.33 (3-node kind, equivalent plain
> Kubernetes) · images `ubi9/httpd-24`, `ubi9/ubi-minimal`. StatefulSet ordered
> startup + ordinal pods + per-pod PVCs + headless per-pod DNS, the DaemonSet
> landing only on the 2 workers (control-plane `NoSchedule` taint shown), the Job
> reaching 3/3 Complete, and the CronJob creation were all run live and the output
> above is from that run.
