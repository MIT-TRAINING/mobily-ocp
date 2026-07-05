# Demo 1 — Services & DNS in OpenShift

> **Scenario:** The **self-care portal** calls the **subscriber-api**, which must be
> reachable by a stable name even as its pods restart and reschedule. We create a
> **Service**, prove **CoreDNS** resolves it to a stable **ClusterIP**, and watch the
> **EndpointSlice** track healthy pods — the internal plumbing every OpenShift app
> depends on.

| | |
|---|---|
| **Concepts reinforced** | `oc expose` (ClusterIP) · CoreDNS names · `svc.cluster.local` · EndpointSlices · readiness gating |
| **Maps to** | Guide §3, §4 · Visualization 01 · Exercise 1 |
| **Time** | ~25 minutes |
| **Cluster** | Shared OCP 4.18 — works in a normal project |

---

> **⎈ Kubernetes equivalent:** everything here is standard Kubernetes — `oc expose`,
> Service, DNS, and EndpointSlices are identical to `kubectl`. OpenShift only *adds*
> Routes on top (Demo 2).

## Talking points to open with

- Pods are mortal and their IPs churn; a **Service** is the stable front door.
- DNS returns the **ClusterIP** (a virtual IP), *not* a pod IP — that's why the name
  survives pod restarts.
- Only **Ready** pods are in the EndpointSlice — readiness *is* the load-balancer's
  membership test.

---

## Step 1 — Deploy the backend and expose it

```bash
oc create deployment subscriber-api \
  --image=registry.access.redhat.com/ubi9/httpd-24:latest
oc rollout status deploy/subscriber-api
oc expose deployment subscriber-api --port=8080     # creates a ClusterIP Service
oc get svc subscriber-api
```

**Verified output** *(learner25 · OCP 4.18 / k8s v1.31.14):*

```
deployment.apps/subscriber-api created
deployment "subscriber-api" successfully rolled out
service/subscriber-api exposed
NAME             TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)             AGE
subscriber-api   ClusterIP   172.30.90.157   <none>        8080/TCP,8443/TCP   17s
```

> **Narrate:** `TYPE=ClusterIP`, `EXTERNAL-IP=<none>` — internal only. On OpenShift this
> is the norm: internal callers use the Service, external users get a **Route** (Demo 2).
> The `172.30.x.x` address is on the **service network**.
>
> **⚠️ Why `oc create deployment`, not `oc new-app`?** `oc new-app` *auto-creates a
> Service*, so a following `oc expose deployment` fails with `services … already exists`.
> `oc create deployment` makes only the Deployment, so `oc expose` teaches the Service
> step cleanly. (The `ubi9/httpd-24` image declares both 8080 and 8443, so the Service
> lists `8080/TCP,8443/TCP` — we route to 8080.)

---

## Step 2 — See the endpoints (which pods back it)

```bash
oc get endpointslices -l kubernetes.io/service-name=subscriber-api
oc get pods -l app=subscriber-api -o wide
```

**Verified output** *(learner25 · OCP 4.18):*

```
NAME                   ADDRESSTYPE   PORTS       ENDPOINTS     AGE
subscriber-api-8cgqn   IPv4          8443,8080   10.131.0.12   39s

NAME                              READY   STATUS    IP            NODE
subscriber-api-7cd8989678-cnvlm   1/1     Running   10.131.0.12   worker-...
```

> **Note:** `oc create deployment` labels pods **`app=subscriber-api`** (use that
> selector; `oc new-app` would use `deployment=`). The endpoint IP is on the pod
> network (`10.131.x.x`).

> **Narrate:** The EndpointSlice lists the **pod IPs** (pod network `10.128/14`) currently
> backing the Service. Compare the endpoint IP to the pod's IP — they match. Scale the
> deployment and this list grows automatically.

---

## Step 3 — Resolve the Service by DNS from another pod

```bash
oc run tmp --rm -it --restart=Never \
  --image=registry.access.redhat.com/ubi9/ubi-minimal -- \
  bash -c 'curl -s -o /dev/null -w "%{http_code}\n" subscriber-api:8080/ ; \
           getent hosts subscriber-api'
```

**Verified output** *(learner25 · project `l25-m6d1`):*

```
172.30.90.157   subscriber-api.l25-m6d1.svc.cluster.local
---
403
```

> **Narrate:** From a pod in the *same* project, the short name `subscriber-api` resolves
> — CoreDNS returns the **ClusterIP** `172.30.90.157` and the full name
> `subscriber-api.l25-m6d1.svc.cluster.local`. The **403** is expected: `httpd-24` has
> no `index.html`, so a 403 *proves connectivity* (we reached Apache). From another
> project you'd need `subscriber-api.l25-m6d1`.

---

## Step 4 — Prove the name is stable across pod churn

```bash
oc scale deployment subscriber-api --replicas=3
oc rollout status deploy/subscriber-api
oc get endpointslices -l kubernetes.io/service-name=subscriber-api \
  -o jsonpath='{.items[0].endpoints[*].addresses[0]}{"\n"}'
POD=$(oc get pods -l app=subscriber-api -o jsonpath='{.items[0].metadata.name}')
oc delete pod "$POD"      # kill one; ClusterIP + name are unchanged
oc get svc subscriber-api -o jsonpath='ClusterIP still {.spec.clusterIP}{"\n"}'
```

**Verified output** *(learner25 · OCP 4.18):*

```
10.131.0.12 10.131.0.19 10.128.2.19
pod "subscriber-api-7cd8989678-cnvlm" deleted from l25-m6d1 namespace
ClusterIP still 172.30.90.157
```

> **Narrate:** Three endpoints now. Delete a pod and a replacement joins with a **new
> IP** — but the **ClusterIP and DNS name never change**. Callers are insulated from pod
> churn entirely. *This* is why you never hard-code pod IPs.

---

## Step 5 — Cleanup

```bash
oc delete all -l app=subscriber-api
```

**Expected output** *(requires a cluster — representative):*

```
deployment.apps "subscriber-api" deleted
service "subscriber-api" deleted
...
```

> **Narrate:** `oc delete all -l` removes the Deployment, Service, and pods in one shot by
> label — the same selector glue that wires Services to pods.

---

## Wrap-up questions to pose

1. Does DNS return a pod IP or the ClusterIP — and why does that matter for stability?
2. What decides whether a pod appears in the EndpointSlice?
3. Why did `curl` to `httpd-24` return **403** rather than 200 — and what does that still
   prove?
4. From a pod in a *different* project, what name would reach this Service?

---

> **✅ Verified:** oc 4.22 · OpenShift 4.18 (k8s v1.31.14) · 2026-07-05 · logged in as
> **learner25** (a normal developer/self-provisioner). Every command and output above is
> from a real run in project `l25-m6d1`. Confirmed: `oc create deployment`+`oc expose`
> works (unlike `oc new-app`, which pre-creates the Service), `httpd-24` returns **403**
> on `/`, DNS resolves to the stable ClusterIP, endpoints scale, and the ClusterIP
> survives pod deletion.
