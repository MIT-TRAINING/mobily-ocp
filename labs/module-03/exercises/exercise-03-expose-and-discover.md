# Exercise 3 — Expose & Discover Services

> **Scenario:** The **self-care portal** must reach the `subscriber-api` by a stable
> name regardless of which pods are alive, and you need to expose it for an external
> smoke test. You'll create a ClusterIP Service, inspect its live endpoints, resolve
> and call it by DNS, then add a NodePort for outside access.

| | |
|---|---|
| **Practice** | `expose`, ClusterIP vs NodePort, EndpointSlices, CoreDNS resolution (short/FQDN/cross-ns) |
| **Maps to** | Guide §8–9 · Demo 3 |
| **Difficulty** | ⭐⭐ Intermediate · ~25 min · single-node OK |

---

## Setup

Create the backend first (or reuse it from Exercise 1):

```bash
kubectl create deployment subscriber-api \
  --image=registry.access.redhat.com/ubi9/httpd-24:latest --replicas=3
```

## Tasks

1. Expose `subscriber-api` as a **ClusterIP** Service on port **80** targeting the
   pods' port **8080**.
2. Show the Service's **EndpointSlice** and confirm it lists **3 pod IPs** on port
   8080.
3. From a throwaway client pod, resolve the Service **three ways**: short name,
   fully-qualified name, and a service in **another namespace** (e.g.
   `kube-dns.kube-system`). Confirm short name and FQDN return the **same** IP.
4. Add a **NodePort** Service for the same Deployment and read the assigned node port
   (30000–32767).
5. Delete one backend pod and re-check the EndpointSlice — confirm it still lists 3
   ready endpoints (one with a new IP).

> **Hint (Task 3):** run a client with
> `kubectl run dnstest --image=registry.access.redhat.com/ubi9/ubi-minimal:latest --restart=Never --command -- sleep 120`,
> then `kubectl exec dnstest -- getent hosts <name>`.

> **Hint (Task 4):** `kubectl expose deployment subscriber-api --type=NodePort ...`
> — read the `PORT(S)` column, e.g. `80:30294/TCP`.

---

## Validation

```bash
# Task 2 / 5 — EndpointSlice lists the ready backends
kubectl get endpointslices -l kubernetes.io/service-name=subscriber-api

# Task 3 — short name and FQDN resolve to the same ClusterIP
kubectl exec dnstest -- getent hosts subscriber-api
kubectl exec dnstest -- getent hosts subscriber-api.mod3-ex.svc.cluster.local

# Task 4 — NodePort assigned in the 30000-32767 range
kubectl get svc subscriber-api-np
```

---

## Reflection

- A Service exists and looks healthy but every request fails. What's the first thing
  to check, and why?
- How does a pod resolve a Service in a *different* namespace?
- When you deleted a pod, what kept the Service routing correctly without any action
  from you?

---

<details>
<summary><strong>✅ Solution</strong> (try the tasks first)</summary>

```bash
# 1. ClusterIP service
kubectl expose deployment subscriber-api --port=80 --target-port=8080 --name=subscriber-api
kubectl get svc subscriber-api

# 2. EndpointSlice — 3 pod IPs on 8080
kubectl get endpointslices -l kubernetes.io/service-name=subscriber-api

# 3. DNS from a client pod
kubectl run dnstest --image=registry.access.redhat.com/ubi9/ubi-minimal:latest \
  --restart=Never --command -- sleep 120
kubectl wait --for=condition=Ready pod/dnstest --timeout=60s
kubectl exec dnstest -- getent hosts subscriber-api                                  # short
kubectl exec dnstest -- getent hosts subscriber-api.mod3-ex.svc.cluster.local        # FQDN
kubectl exec dnstest -- getent hosts kube-dns.kube-system.svc.cluster.local          # cross-ns

# 4. NodePort
kubectl expose deployment subscriber-api --type=NodePort \
  --port=80 --target-port=8080 --name=subscriber-api-np
kubectl get svc subscriber-api-np

# 5. Self-healing endpoints
POD=$(kubectl get pods -l app=subscriber-api -o jsonpath='{.items[0].metadata.name}')
kubectl delete pod "$POD"
kubectl get endpointslices -l kubernetes.io/service-name=subscriber-api   # still 3 ready

# Cleanup
kubectl delete pod dnstest --force --grace-period=0
kubectl delete svc subscriber-api subscriber-api-np
kubectl delete deployment subscriber-api
```

**Verified output (key lines):**

```
NAME                   ADDRESSTYPE   PORTS   ENDPOINTS
subscriber-api-nthlr   IPv4          8080    10.244.2.52,10.244.1.42,10.244.2.50

10.96.48.169    subscriber-api.mod3-verify.svc.cluster.local      # short name
10.96.48.169    subscriber-api.mod3-verify.svc.cluster.local      # FQDN (same IP)
10.96.0.10      kube-dns.kube-system.svc.cluster.local            # cross-namespace

NAME                TYPE       CLUSTER-IP    PORT(S)
subscriber-api-np   NodePort   10.96.97.71   80:30294/TCP
```

**Key point:** the Service's stable ClusterIP and DNS name hide the churn of pods
behind it. The EndpointSlice is the *live* selector result — recomputed
automatically as pods come and go, which is why deleting a pod never breaks routing.
</details>

---

> **✅ Verified:** kubectl 1.34 · Kubernetes 1.33 (3-node kind, equivalent plain
> Kubernetes) · images `ubi9/httpd-24`, `ubi9/ubi-minimal`. ClusterIP exposure, the
> EndpointSlice listing, DNS (short/FQDN/cross-ns to the same/expected IPs), and
> NodePort assignment were all run live (the identical flow as Demo 3). FQDN shown
> uses the verification namespace `mod3-verify`; substitute your own namespace.
