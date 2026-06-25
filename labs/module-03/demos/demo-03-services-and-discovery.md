# Demo 3 — Services & Service Discovery

> **Scenario:** The **self-care portal** needs to reach two backends —
> `subscriber-api` and `tariff-catalog` — by a stable name, even though their pods
> come and go. We put a **Service** in front of each, watch the **EndpointSlice**
> track the live pods, resolve them through **CoreDNS**, expose one to the outside
> with a **NodePort**, and finally draft an **Ingress** that routes by path — seeing
> first-hand why an Ingress object does nothing without a controller.

| | |
|---|---|
| **Concepts reinforced** | ClusterIP · NodePort · headless · EndpointSlices · CoreDNS (short/FQDN/cross-ns) · Ingress object vs controller |
| **Maps to** | Guide §8–9 (Services, DNS & Ingress) · Exercise 3 |
| **Time** | ~30 minutes |
| **Cluster** | minikube; single node is fine (Ingress step is object-only) |

---

> **⎈ Same on OpenShift — with a twist:** ClusterIP/NodePort all work as `oc`. But
> the *idiomatic* way to expose HTTP on OpenShift is a **Route** (`oc expose
> svc/...`), not a NodePort — OpenShift ships an ingress controller (the Router) out
> of the box, so the "no controller" gap in Step 6 never happens there.

## Talking points to open with

- Pod IPs are disposable; a **Service** is the stable name + virtual IP in front of
  them.
- A Service finds its pods by **label selector**, and stores the result as an
  **EndpointSlice** — its live backend list.
- DNS is what makes a Service *usable*: `<svc>.<ns>.svc.cluster.local`.

> **Setup:** this demo assumes `subscriber-api` (httpd, 3 replicas) and
> `tariff-catalog` (nginx, 3 replicas) Deployments exist. Recreate them from Demo 1
> / Demo 2 Step 1 if you've cleaned up.

---

## Step 1 — Put a ClusterIP Service in front of subscriber-api

```bash
kubectl expose deployment subscriber-api --port=80 --target-port=8080 --name=subscriber-api
kubectl get svc subscriber-api
```

**Expected output:**

```
service/subscriber-api exposed
NAME             TYPE        CLUSTER-IP     EXTERNAL-IP   PORT(S)   AGE
subscriber-api   ClusterIP   10.96.48.169   <none>        80/TCP    0s
```

> **Narrate:** `ClusterIP` is the default — an **internal-only** virtual IP. Clients
> hit port **80** on the Service; it forwards to **8080** on the pods (httpd's port).
> That virtual IP is stable for the life of the Service, no matter how many times
> the backing pods are replaced.

---

## Step 2 — The EndpointSlice: the live backend list

```bash
kubectl get endpointslices -l kubernetes.io/service-name=subscriber-api
```

**Expected output:**

```
NAME                   ADDRESSTYPE   PORTS   ENDPOINTS
subscriber-api-nthlr   IPv4          8080    10.244.2.52,10.244.1.42,10.244.2.50
```

> **Narrate:** Three pod IPs on port 8080 — the Service's current backends. This
> list is rebuilt automatically as pods come and go (it's the selector's live
> result). If it were ever **empty**, the Service would have nothing to route to —
> that's the #1 cause of "connection refused" from a Service that looks healthy.

---

## Step 3 — Resolve and reach the Service by DNS

Spin up a throwaway client pod and look the Service up three ways:

```bash
kubectl run dnstest --image=registry.access.redhat.com/ubi9/ubi-minimal:latest \
  --restart=Never --command -- sleep 120
kubectl wait --for=condition=Ready pod/dnstest --timeout=60s
kubectl exec dnstest -- getent hosts subscriber-api
kubectl exec dnstest -- getent hosts subscriber-api.mod3-demos.svc.cluster.local
kubectl exec dnstest -- getent hosts kube-dns.kube-system.svc.cluster.local
```

**Expected output (namespace shown is the verification namespace `mod3-verify`):**

```
10.96.48.169    subscriber-api.mod3-verify.svc.cluster.local      # short name
10.96.48.169    subscriber-api.mod3-verify.svc.cluster.local      # FQDN
10.96.0.10      kube-dns.kube-system.svc.cluster.local            # cross-namespace
```

> **Narrate:** Three lookups, one lesson. The **short name** works because the
> pod's `/etc/resolv.conf` has a search domain for its own namespace — both it and
> the **FQDN** resolve to the same ClusterIP. The **third** lookup reaches a service
> in a *different* namespace (`kube-system`) by FQDN. The pattern
> `<svc>.<ns>.svc.cluster.local` is how anything addresses anything in the cluster.

Now actually *use* it — curl the nginx `tariff-catalog` Service by name (expose it
first if you haven't):

```bash
kubectl expose deployment tariff-catalog --port=80 --target-port=80 --name=tariff-catalog
kubectl exec dnstest -- curl -s -o /dev/null -w "HTTP %{http_code}\n" http://tariff-catalog/
kubectl delete pod dnstest --force --grace-period=0
```

**Expected output:**

```
HTTP 200
```

> **Narrate:** A real request, resolved by name, load-balanced to one of the three
> nginx pods, answered **200**. That's the whole point of a Service — the client
> never knew or cared which pod served it.

---

## Step 4 — Expose externally with a NodePort

```bash
kubectl expose deployment subscriber-api --type=NodePort \
  --port=80 --target-port=8080 --name=subscriber-api-np
kubectl get svc subscriber-api-np
```

**Expected output:**

```
service/subscriber-api-np exposed
NAME                TYPE       CLUSTER-IP    EXTERNAL-IP   PORT(S)        AGE
subscriber-api-np   NodePort   10.96.97.71   <none>        80:30294/TCP   0s
```

> **Narrate:** `80:30294/TCP` reads "the Service's port 80 is also reachable on port
> **30294** of *every node*." From outside, `http://<any-node-IP>:30294` reaches the
> pods. Great for dev/demo; in production you'd front this with a LoadBalancer or
> (on OpenShift) a Route, because handing out high ports per service doesn't scale.

---

## Step 5 — A headless Service (no virtual IP)

```bash
kubectl create service clusterip subscriber-api-headless --clusterip=None --tcp=80:8080
kubectl get svc subscriber-api-headless
```

**Expected output:**

```
service/subscriber-api-headless created
NAME                      TYPE        CLUSTER-IP   EXTERNAL-IP   PORT(S)   AGE
subscriber-api-headless   ClusterIP   None         <none>        80/TCP    0s
```

> **Narrate:** `CLUSTER-IP: None` — there is *no* virtual IP. DNS for a headless
> Service returns the **pod IPs directly** instead of one load-balanced address.
> That's exactly what StatefulSets need so each pod is individually addressable
> (Demo 5). Different tool for a different job.

---

## Step 6 — An Ingress: routing rules that need a controller

Draft an Ingress that routes by path to both backends:

```bash
cat > selfcare-ingress.yaml <<'EOF'
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: selfcare
spec:
  rules:
    - host: selfcare.mobily.example
      http:
        paths:
          - path: /api
            pathType: Prefix
            backend: { service: { name: subscriber-api, port: { number: 80 } } }
          - path: /tariffs
            pathType: Prefix
            backend: { service: { name: tariff-catalog, port: { number: 80 } } }
EOF
kubectl apply -f selfcare-ingress.yaml
kubectl get ingress selfcare
```

**Expected output:**

```
ingress.networking.k8s.io/selfcare created
NAME       CLASS    HOSTS                     ADDRESS   PORTS   AGE
selfcare   <none>   selfcare.mobily.example             80      70m
```

> **◐ Note — requires an ingress controller.** This cluster has **no ingress
> controller installed**, so the `ADDRESS` column stays **empty** — the object is
> valid but nothing is enforcing it yet. On minikube, enable one with
> `minikube addons enable ingress`; on OpenShift the Router is already running, so an
> Address appears immediately. The output below is representative of the
> controller-less state.

`describe` proves the rules and the resolved backends are correct regardless:

```bash
kubectl describe ingress selfcare
```

**Expected output (excerpt):**

```
Rules:
  Host                     Path       Backends
  selfcare.mobily.example  /api       subscriber-api:80 (10.244.2.52:8080,10.244.1.42:8080,10.244.2.50:8080)
                           /tariffs   tariff-catalog:80 (10.244.2.63:80,10.244.1.53:80,10.244.2.64:80)
Address:
```

> **Narrate:** The Ingress already knows where `/api` and `/tariffs` should go — it
> even resolved the live endpoints. What it *lacks* is a running proxy to act on the
> rules. **Ingress object = the rules; Ingress controller = the thing that enforces
> them.** That distinction trips up everyone once.

---

## Step 7 — Cleanup

```bash
kubectl delete ingress selfcare
kubectl delete svc subscriber-api subscriber-api-np subscriber-api-headless tariff-catalog
kubectl delete deployment subscriber-api tariff-catalog
```

**Expected output:**

```
ingress.networking.k8s.io "selfcare" deleted
service "subscriber-api" deleted
service "subscriber-api-np" deleted
service "subscriber-api-headless" deleted
service "tariff-catalog" deleted
deployment.apps "subscriber-api" deleted
deployment.apps "tariff-catalog" deleted
```

---

## Wrap-up questions to pose

1. A Service "works" but every request fails. What's the first thing to check, and
   why?
2. How does a pod resolve a Service in *another* namespace?
3. What does `CLUSTER-IP: None` change about how DNS answers?
4. You applied an Ingress and `ADDRESS` is blank. What's missing?

---

> **✅ Verified:** kubectl 1.34 · Kubernetes 1.33 (3-node kind, equivalent plain
> Kubernetes) · images `ubi9/httpd-24`, `nginx:1.x-alpine`, `ubi9/ubi-minimal`.
> ClusterIP, EndpointSlice, DNS (short/FQDN/cross-ns), a real `HTTP 200` curl by
> name, NodePort, headless Service, and the Ingress object+describe were all run
> live. The **Ingress step is marked ◐** because no controller was installed — the
> `ADDRESS`-empty output is the real, representative result of that state.
