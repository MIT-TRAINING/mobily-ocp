# Exercise 1 — Services & DNS

> **Scenario:** You're wiring the **self-care portal** to its backend **subscriber-api**.
> Expose the backend as a Service, confirm callers can find it by **DNS**, and prove the
> Service name stays stable while pods churn.

| | |
|---|---|
| **Practice** | `oc expose` (ClusterIP), CoreDNS names, EndpointSlices, readiness gating, stable ClusterIP |
| **Maps to** | Guide §3, §4 · Visualization 01 · Demo 1 |
| **Difficulty** | ⭐ Beginner · ~20 min · works in one project (Sandbox OK) |

---

## Tasks

1. Create a deployment **`subscriber-api`** from `ubi9/httpd-24` and **expose** it as a
   **ClusterIP** Service on port **8080**.
2. Show the Service's **ClusterIP** and confirm it has **no external IP**.
3. From a throwaway pod, resolve the Service **by DNS** and confirm you reach it (expect
   **403** from `httpd-24`).
4. Show the **EndpointSlice** and confirm the pod IP(s) backing the Service.
5. Scale to **3**, then delete one pod, and prove the **ClusterIP and DNS name are
   unchanged** while a new endpoint appears.
6. State the **fully-qualified** DNS name a pod in *another* project would use.

> **Hint (Task 3):** `oc run tmp --rm -it --image=registry.access.redhat.com/ubi9/ubi-minimal -- curl -s -o /dev/null -w "%{http_code}\n" subscriber-api:8080/`.

---

## Validation

```bash
# Task 2 — ClusterIP, no external IP
oc get svc subscriber-api

# Task 3 — DNS + reachability (403 = reached httpd)
oc run tmp --rm -it --restart=Never --image=registry.access.redhat.com/ubi9/ubi-minimal -- \
  bash -c 'getent hosts subscriber-api; curl -s -o /dev/null -w "%{http_code}\n" subscriber-api:8080/'

# Task 4 — endpoints
oc get endpointslices -l kubernetes.io/service-name=subscriber-api

# Task 5 — ClusterIP stable after churn
oc get svc subscriber-api -o jsonpath='{.spec.clusterIP}{"\n"}'
```

---

## Reflection

- Does DNS hand back a pod IP or the ClusterIP — and why does that choice give you
  stability?
- What single condition puts a pod into (or out of) the EndpointSlice?
- Why is **403** (not 200) the *success* signal for a bare `httpd-24` Service?

---

<details>
<summary><strong>✅ Solution</strong> (try the tasks first)</summary>

```bash
# 1. Deploy + expose (ClusterIP)
oc new-app --name=subscriber-api registry.access.redhat.com/ubi9/httpd-24:latest
oc expose deployment subscriber-api --port=8080

# 2. ClusterIP, no external IP
oc get svc subscriber-api      # TYPE=ClusterIP, EXTERNAL-IP=<none>, 8080/TCP

# 3. DNS + reach
oc run tmp --rm -it --restart=Never --image=registry.access.redhat.com/ubi9/ubi-minimal -- \
  bash -c 'getent hosts subscriber-api; curl -s -o /dev/null -w "%{http_code}\n" subscriber-api:8080/'

# 4. Endpoints
oc get endpointslices -l kubernetes.io/service-name=subscriber-api

# 5. Scale + churn; ClusterIP unchanged
oc scale deployment subscriber-api --replicas=3
CIP=$(oc get svc subscriber-api -o jsonpath='{.spec.clusterIP}')
POD=$(oc get pods -l deployment=subscriber-api -o jsonpath='{.items[0].metadata.name}')
oc delete pod "$POD"
test "$CIP" = "$(oc get svc subscriber-api -o jsonpath='{.spec.clusterIP}')" && echo "ClusterIP stable: $CIP"

# 6. Cross-project FQDN: subscriber-api.<this-namespace>.svc.cluster.local

# Cleanup
oc delete all -l app=subscriber-api
```

**Representative output** *(requires a cluster — OCP 4.18):*

```
NAME             TYPE        CLUSTER-IP     EXTERNAL-IP   PORT(S)    AGE
subscriber-api   ClusterIP   172.30.42.10   <none>        8080/TCP   6s

172.30.42.10   subscriber-api.mod6-ex.svc.cluster.local
403
ClusterIP stable: 172.30.42.10
```

**Key point:** DNS returns the **ClusterIP** — a stable virtual IP that outlives any pod.
Only **Ready** pods join the EndpointSlice, and the Service load-balances across them. A
**403** from `httpd-24` (no index.html) still proves the connection reached Apache.
Cross-project, use `subscriber-api.<namespace>.svc.cluster.local`.
</details>

---

> **◐ Partially verified:** every command **requires a live OpenShift cluster** and was
> not runnable here (no cluster). Output is **representative of OpenShift 4.18**; the
> `httpd-24` **403-on-/** and `svc.cluster.local` naming are real, documented behaviours.
> Run live for your ClusterIP/pod IPs. Nothing is presented as independently verified.
