# Exercise 5 — Capstone: A Discoverable Service

> **Scenario:** The **Self-Care Portal** needs to call the **subscriber-api**, and
> the API's pods restart with new IPs all day. Put a Service in front of the API,
> prove the portal can reach it **by name**, then break and scale the backend and
> show the caller never has to change. This ties together every Module 2 idea.

| | |
|---|---|
| **Practice** | Service + selector, endpoints, CoreDNS, load-balancing, self-healing — combined |
| **Maps to** | Visualization 05 (Services, Labels & DNS) · Demo 5 |
| **Difficulty** | ⭐⭐⭐ Advanced · ~35 min · single-node minikube OK |

---

## Tasks

1. Deploy **`subscriber-api`** (image `ubi9/httpd-24`, **3 replicas**) and create a
   **ClusterIP Service** for it on port **8080** (`kubectl expose`, or a Service
   manifest). Record the ClusterIP.
2. Show the Service's **selector** and its **endpoints**, and cross-check that the
   endpoint IPs equal the Ready pods' IPs.
3. Acting as the portal, launch a throwaway client pod and:
   (a) **resolve** `subscriber-api` by DNS to confirm it returns the ClusterIP;
   (b) `curl` it several times.
4. **Scale** the backend to 5, then 2 — each time, confirm the **endpoints list
   tracks the change** without you touching the Service.
5. **Delete a backing pod** while watching `kubectl get endpoints subscriber-api -w`.
   Describe what happens to the dead IP and the replacement's IP.
6. **Relabel** one pod out of the selector (`app=quarantined`). Show it (a) leaves
   the endpoints **and** (b) triggers the ReplicaSet to create a replacement.
   Explain why *two* things happened from one label change.

> **Hint (Task 3):** `kubectl run tmp --rm -it --restart=Never \
> --image=registry.access.redhat.com/ubi9/ubi -- bash -c \
> 'getent hosts subscriber-api; curl -s -o /dev/null -w "%{http_code}\n" \
> http://subscriber-api:8080/'`.

---

## Validation

```bash
# Task 1 — a ClusterIP Service exists
kubectl get svc subscriber-api

# Task 2 — endpoints == Ready pod IPs (3 of them)
kubectl get endpoints subscriber-api
kubectl get pods -l app=subscriber-api -o wide

# Task 4 — after scaling to 5, endpoints lists 5 IPs
kubectl scale deployment subscriber-api --replicas=5
kubectl get endpoints subscriber-api

# Task 6 — relabeled pod is gone from endpoints, replacement exists
kubectl get pods -l app=subscriber-api          # still the desired count (replacement made)
kubectl get endpoints subscriber-api            # quarantined pod's IP absent
```

---

## Stretch goals

- Print the Service's **FQDN** and explain each segment:
  `subscriber-api.<namespace>.svc.cluster.local`.
- From the client pod, run the `curl` 20 times and tally which pod answered (read
  `kubectl logs` access logs per pod) to *see* load-balancing.
- Make **all** pods NotReady (e.g. scale to 0, or break readiness) and curl the
  Service — what HTTP status do you get and why? (Empty endpoints → no backend.)
- Create a second Service selecting `app=quarantined` and confirm your relabeled
  pod now appears there — labels are the only glue.

---

## Reflection

- You scaled 3→5→2 pods. What changed on the **Service** object each time?
- A pod is Running but fails readiness — is it an endpoint? Why is that protective?
- Why does relabeling a pod affect **both** the Service and the ReplicaSet?
- Justify, to a teammate, why hard-coding a pod IP in the portal is a bug.

---

<details>
<summary><strong>✅ Solution</strong> (try the tasks first)</summary>

```bash
# 1. Backend + Service
kubectl create deployment subscriber-api \
  --image=registry.access.redhat.com/ubi9/httpd-24:latest --replicas=3
kubectl expose deployment subscriber-api --port=8080
kubectl get svc subscriber-api                          # note CLUSTER-IP

# 2. Selector + endpoints
kubectl get svc subscriber-api -o jsonpath='selector={.spec.selector}{"\n"}'
kubectl get endpoints subscriber-api
kubectl get pods -l app=subscriber-api -o wide          # same IPs as endpoints

# 3. Be the portal — call by NAME
kubectl run tmp --rm -it --restart=Never \
  --image=registry.access.redhat.com/ubi9/ubi -- bash -c '
  getent hosts subscriber-api;
  for i in 1 2 3 4; do curl -s -o /dev/null -w "%{http_code}\n" http://subscriber-api:8080/; done'

# 4. Scale; endpoints follow automatically
kubectl scale deployment subscriber-api --replicas=5; kubectl get endpoints subscriber-api   # 5 IPs
kubectl scale deployment subscriber-api --replicas=2; kubectl get endpoints subscriber-api   # 2 IPs
kubectl scale deployment subscriber-api --replicas=3

# 5. Self-healing endpoints (watch in 2nd terminal: kubectl get endpoints subscriber-api -w)
POD=$(kubectl get pods -l app=subscriber-api -o jsonpath='{.items[0].metadata.name}')
kubectl delete pod "$POD"
# Dead pod's IP drops out immediately; the ReplicaSet's replacement (NEW IP) joins
# once Ready. The Service name/ClusterIP never changed — the caller noticed nothing.

# 6. Labels are the glue
POD=$(kubectl get pods -l app=subscriber-api -o jsonpath='{.items[0].metadata.name}')
kubectl label pod "$POD" app=quarantined --overwrite
kubectl get endpoints subscriber-api          # quarantined IP gone (no longer matches selector)
kubectl get pods -l app=subscriber-api        # ReplicaSet made a replacement (lost an owned pod)
# One label change hit TWO loops: the endpoints controller (Service membership) and
# the ReplicaSet controller (ownership/count).

# Cleanup
kubectl delete svc,deployment subscriber-api
kubectl delete pod -l app=quarantined --ignore-not-found
```

**Key point:** the portal targets a **stable name** (DNS → stable ClusterIP);
**labels + selectors** decide Service membership and **readiness** decides
eligibility, so the endpoint set self-adjusts through scaling, pod death, and
relabeling — with zero caller changes. That decoupling is what makes a dynamic,
self-healing cluster usable. Never hard-code a pod IP.
</details>
