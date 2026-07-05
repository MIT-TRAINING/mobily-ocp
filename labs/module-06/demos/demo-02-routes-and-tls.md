# Demo 2 — Routes & TLS Termination

> **Scenario:** The **self-care portal** must be reachable by subscribers on the
> internet over HTTPS. We publish it with a **Route**, then walk the three TLS modes —
> **edge**, **passthrough**, **re-encrypt** — so the class sees *where the lock opens*
> for each, and how a Kubernetes **Ingress** becomes a Route on OpenShift.

| | |
|---|---|
| **Concepts reinforced** | `oc expose` (HTTP Route) · `oc create route edge/passthrough/reencrypt` · router · Ingress→Route |
| **Maps to** | Guide §5, §6, §7 · Visualization 02 · Exercise 2 |
| **Time** | ~30 minutes |
| **Cluster** | Shared OCP 4.18 — auto-hostname edge Route works for any user |

---

> **⎈ Kubernetes equivalent:** **Routes are OpenShift-specific.** The nearest standard is
> **Ingress** (Step 5) — which OpenShift fulfils by generating a Route. `oc expose` and
> `oc create route` have no `kubectl` equivalent.

## Talking points to open with

- A Route publishes a Service at a hostname under the cluster's `*.apps.<domain>`.
- The **one decision** is TLS termination: **edge** (router decrypts → HTTP to pod),
  **passthrough** (pod owns TLS), **re-encrypt** (decrypt then re-encrypt).
- The **HAProxy Router** (the `ingress` operator) does the work — "app down externally"
  is often a Route/router question.

---

## Step 0 — Backend ready

```bash
oc create deployment self-care --image=registry.access.redhat.com/ubi9/httpd-24:latest
oc rollout status deploy/self-care
oc expose deployment self-care --port=8080        # ClusterIP Service (from Demo 1)
```

**Verified output** *(learner25 · OCP 4.18):*

```
deployment.apps/self-care created
deployment "self-care" successfully rolled out
service/self-care exposed
```

> **⚠️ Use `oc create deployment`, not `oc new-app`** — `oc new-app` auto-creates a
> Service, making the next `oc expose deployment` fail with `already exists`.

---

## Step 1 — Expose an unsecured (HTTP) Route

```bash
oc expose service self-care                        # HTTP Route, auto hostname
oc get route self-care -o wide
```

**Verified output** *(learner25 · OCP 4.18):*

```
NAME        HOST/PORT                                                            PATH   SERVICES    PORT       TERMINATION   WILDCARD
self-care   self-care-l25-m6d1.apps.mobily-ocp-training.ocp.supercloudlabs.com          self-care   8080-tcp                 None
```

> **Narrate:** `oc expose service` created a **Route** with an auto hostname under
> `*.apps.<domain>` and **no TERMINATION** (plain HTTP). Good for a quick internal test,
> never for real subscriber traffic. Note: `oc expose` on a *deployment* makes a Service;
> on a *service* it makes a Route.
>
> **💡 Finding the apps domain as a normal user.** A developer *cannot* run
> `oc get ingresses.config/cluster` (cluster-scope, Forbidden for learner25). Just read
> the domain off the Route's **HOST** — everything after the first dot
> (`apps.mobily-ocp-training.ocp.supercloudlabs.com`) is the wildcard apps domain.

```bash
HOST=$(oc get route self-care -o jsonpath='{.spec.host}')
curl -s -o /dev/null -w "%{http_code}\n" "http://$HOST/"
```

**Verified output:** `403`  *(httpd-24 has no index.html — 403 proves the router reached the pod).*

---

## Step 2 — Edge: HTTPS at the router, HTTP to the pod

```bash
oc delete route self-care
oc create route edge self-care --service=self-care --port=8080 \
  --insecure-policy=Redirect          # http auto-redirects to https
sleep 15                              # give the router time to admit the new route
oc get route self-care -o jsonpath='TERMINATION={.spec.tls.termination}{"\n"}'
EHOST=$(oc get route self-care -o jsonpath='{.spec.host}')
curl -sk -o /dev/null -w "https: %{http_code}\n" "https://$EHOST/"     # edge → pod
curl -s  -o /dev/null -w "http:  %{http_code}\n" "http://$EHOST/"      # redirect
```

**Verified output** *(learner25 · OCP 4.18):*

```
route.route.openshift.io/self-care created
TERMINATION=edge
https: 403
http:  302
```

> **Narrate:** Now **edge** — HTTPS to the user (using the router's default wildcard cert
> since we supplied none), cleartext HTTP router→pod. The **403** over HTTPS proves the
> router terminated TLS and reached Apache; the **302** on HTTP is
> `--insecure-policy=Redirect` bumping callers to HTTPS. Go-to for a public portal on a
> trusted pod network.
>
> **⏱️ Router propagation gotcha (verified):** immediately after `oc create route`, a curl
> can return **503** for a few seconds while the HAProxy router reloads. Wait ~10–15s (or
> check `oc get route self-care -o jsonpath='{.status.ingress[0].conditions[0].status}'`
> is `True`) — then it serves **403/302**. A 503 right after creating a route is normal,
> not a failure.

---

## Step 3 — Passthrough & re-encrypt (the other two modes)

```bash
# Passthrough — the POD terminates TLS; router just forwards bytes (needs an HTTPS app on 8443)
oc create route passthrough sms-gw --service=sms-gateway --port=8443

# Re-encrypt — router decrypts (to route L7) then re-encrypts to the pod
oc create route reencrypt billing --service=billing-api \
  --cert=tls.crt --key=tls.key --dest-ca-cert=service-ca.crt
```

**Expected output** *(requires a cluster + HTTPS-capable backends — representative):*

```
route.route.openshift.io/sms-gw created
route.route.openshift.io/billing created
```

> **Narrate:** **Passthrough** is the only mode where the router never sees plaintext —
> mandatory for the SMS gateway's mutual TLS with a carrier (but no L7 path routing).
> **Re-encrypt** gives end-to-end encryption *and* lets the router route by host/path —
> the `--dest-ca-cert` tells the router to trust the pod's internal cert. *(The certs here
> are placeholders; supply real ones on a live cluster.)*

---

## Step 4 — Verify each Route's termination at a glance

```bash
oc get routes -o custom-columns=NAME:.metadata.name,HOST:.spec.host,TLS:.spec.tls.termination
```

**Expected output** *(requires a cluster — representative):*

```
NAME        HOST                                          TLS
self-care   self-care-mod6-demos.apps.<domain>            edge
sms-gw      sms-gw-mod6-demos.apps.<domain>               passthrough
billing     billing-mod6-demos.apps.<domain>              reencrypt
```

> **Narrate:** One column tells you the security posture of every exposed app. In an
> audit, `TLS=<none>` on a public Route is a red flag.

---

## Step 5 — Ingress becomes a Route

```bash
oc create ingress selfcare-ing --rule="selfcare.apps.<domain>/*=self-care:8080"
oc get route -l 'openshift.io/ingress.name=selfcare-ing' 2>/dev/null || oc get route
```

**Expected output** *(requires a cluster — representative):*

```
ingress.networking.k8s.io/selfcare-ing created
# a Route is auto-generated by the Ingress Operator to fulfil the Ingress
NAME                  HOST                              SERVICES    TLS
selfcare-ing-xxxxx    selfcare.apps.<domain>            self-care
```

> **Narrate:** Create a **Kubernetes Ingress** and OpenShift's Ingress Operator
> **generates a Route** to satisfy it, served by the same HAProxy router. Ingress =
> portable; Route = OpenShift power (passthrough/re-encrypt/sharding).

---

## Step 6 — Cleanup

```bash
oc delete route --all
oc delete all -l app=self-care
oc delete ingress selfcare-ing 2>/dev/null
```

**Expected output** *(requires a cluster — representative):*

```
route.route.openshift.io "self-care" deleted
...
```

---

## Wrap-up questions to pose

1. What's the difference between `oc expose deployment` and `oc expose service`?
2. In **edge**, is router→pod traffic encrypted? In **passthrough**? In **re-encrypt**?
3. Which mode is required for an app doing mutual TLS, and what capability do you lose?
4. You create an Ingress on OpenShift — what object actually gets created to serve it?

---

> **◐ Verified (edge + HTTP + Ingress path) / representative (passthrough & re-encrypt):**
> oc 4.22 · OpenShift 4.18 · 2026-07-05 · **learner25**. Steps 0–2 and 4 were run live in
> project `l25-m6d1`: the HTTP Route (**403**), the **edge** Route (`TERMINATION=edge`,
> **https 403 / http 302**), the router-admit **503→403** propagation, and the TLS-column
> overview are all real output. **Passthrough** and **re-encrypt** (Step 3) need an
> HTTPS-terminating backend on 8443 and real certs — those remain **representative of
> OpenShift 4.18** (the `oc create route passthrough|reencrypt` syntax is client-verified).
