# Demo 5 — Services, Endpoints & DNS

> **Scenario:** The **self-care portal** must call the **subscriber-api**. Pods
> restart with new IPs constantly, so the portal must *never* hard-code one. We'll
> put a **Service** in front of the API, prove it load-balances across live pods,
> resolve it by **DNS name**, then kill a pod and watch the endpoint set self-heal —
> all without the caller changing a thing.

| | |
|---|---|
| **Concepts reinforced** | Labels/selectors · Service ClusterIP · Endpoints (match + Ready) · CoreDNS service discovery · load-balancing |
| **Maps to** | Visualization 05 (Services, Labels & DNS) · Guide §5.6, §6.3, §9 |
| **Time** | ~30 minutes |
| **Cluster** | minikube, single node is fine |

---

> **⎈ Same on OpenShift:** `kubectl create deployment / expose / get / scale / run`
> all work verbatim as `oc ...`. (`oc expose` and `oc debug` are OpenShift
> conveniences; the portable forms are `kubectl expose` and `kubectl run --rm -it`,
> used below.)

## Talking points to open with

- A Service does **not** store pod IPs. It stores a **selector**; the endpoints
  controller fills in the IPs that **match AND are Ready**.
- The Service's **ClusterIP** and **DNS name** are stable for its whole life; the
  pods behind it are disposable.
- DNS turns "find the subscriber API" from chasing IPs into a stable name lookup.

---

## Step 1 — Deploy the backend, then put a Service in front

```bash
kubectl create deployment subscriber-api \
  --image=registry.access.redhat.com/ubi9/httpd-24:latest --replicas=3
kubectl expose deployment subscriber-api --port=8080      # creates a ClusterIP Service
kubectl get svc subscriber-api
```

```
NAME             TYPE        CLUSTER-IP      PORT(S)    AGE
subscriber-api   ClusterIP   10.96.42.10     8080/TCP   5s
```

> **Narrate:** `kubectl expose` created a **Service** whose selector matches the
> Deployment's pod labels (`app=subscriber-api`). That `CLUSTER-IP` is now stable —
> it will outlive every pod behind it.

---

## Step 2 — See the selector and the endpoints it produced

```bash
kubectl get svc subscriber-api -o jsonpath='selector={.spec.selector}{"\n"}'
kubectl get endpoints subscriber-api          # the live pod IPs (match + Ready)
kubectl get pods -l app=subscriber-api -o wide   # cross-check: same 3 IPs
```

```
selector={"app":"subscriber-api"}
NAME             ENDPOINTS                                      AGE
subscriber-api   10.244.0.41:8080,10.244.0.12:8080,10.244.0.42:8080
```

> **Narrate:** The **endpoints controller** watched for pods matching the selector
> that are Ready, and listed exactly those 3 IPs. The Service never enumerated pods
> itself — it declared *intent* (a selector) and the controller filled in reality.

---

## Step 3 — Resolve and call the Service by DNS name

Launch a throwaway client pod inside the cluster and use the **name**, never an IP:

```bash
kubectl run tmp-client --rm -it --restart=Never \
  --image=registry.access.redhat.com/ubi9/ubi -- bash -c '
  getent hosts subscriber-api;                       # DNS → ClusterIP
  for i in 1 2 3 4; do curl -s -o /dev/null -w "%{http_code} via %{remote_ip}\n" \
    http://subscriber-api:8080/; done'
```

```
subscriber-api.mod2-demos.svc.cluster.local  10.96.42.10
200 via 10.96.42.10
200 via 10.96.42.10
...
```

> **Narrate:** `getent hosts` shows **CoreDNS** resolving the short name to the
> **stable ClusterIP** (FQDN: `<svc>.<namespace>.svc.cluster.local`). The portal
> connects to that one virtual IP, and **kube-proxy** node rules DNAT-balance each
> connection to one of the 3 backing pods. The caller used a *name* — no pod IP in
> sight.

---

## Step 4 — Scale the backend; endpoints follow automatically

```bash
kubectl scale deployment subscriber-api --replicas=5
kubectl get endpoints subscriber-api          # now lists 5 IPs — no Service edit needed
kubectl scale deployment subscriber-api --replicas=2
kubectl get endpoints subscriber-api          # now 2 IPs
```

> **Narrate:** We changed the *backend count* and the endpoint list tracked it
> instantly. The Service object — its name, ClusterIP, selector — never changed.
> Membership is computed continuously from labels + readiness.

---

## Step 5 — Kill a pod: the endpoint set self-heals

In a second terminal:

```bash
kubectl get endpoints subscriber-api -w
```

In the first terminal, delete a backing pod:

```bash
POD=$(kubectl get pods -l app=subscriber-api -o jsonpath='{.items[0].metadata.name}')
kubectl delete pod "$POD"
```

> **Narrate (watch the endpoints terminal):** The dead pod's IP **drops out** of the
> endpoints immediately (it's no longer Ready), then the ReplicaSet's replacement —
> with a **brand-new IP** — **appears** in the list once it passes readiness. The
> portal, still calling `http://subscriber-api:8080`, never noticed. *This* is why
> you never hard-code a pod IP.

Bonus — break readiness without deleting anything (label flip removes a pod from
the selector, just like Viz 05's toggle):

```bash
POD=$(kubectl get pods -l app=subscriber-api -o jsonpath='{.items[0].metadata.name}')
kubectl label pod "$POD" app=quarantined --overwrite     # no longer matches selector
kubectl get endpoints subscriber-api                      # that pod's IP is gone
kubectl get pods -l app=subscriber-api                    # ...and the ReplicaSet spun up a replacement!
```

> **Narrate:** Relabeling pulled the pod *out of the Service* **and** out of the
> ReplicaSet's ownership — so the ReplicaSet, seeing `actual < desired`, created a
> fresh one. Two reconciliation loops reacted to one label change. Labels are the glue.

---

## Step 6 — Cleanup

```bash
kubectl delete service subscriber-api
kubectl delete deployment subscriber-api
kubectl delete pod -l app=quarantined --ignore-not-found
kubectl get all -l app=subscriber-api      # confirm clean
```

---

## Wrap-up questions to pose

1. A pod is Running but failing its readiness probe — is it in the Service's
   endpoints? Why?
2. You scaled from 3 → 10 pods. What did you change on the Service object? (Trick
   question.)
3. What does `subscriber-api.mod2-demos.svc.cluster.local` resolve to, and what
   load-balances from there to a pod?
4. Why is hard-coding a pod IP in the portal a bug waiting to happen?
