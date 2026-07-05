# Module 6 — Exercises (Hands-On Practice)

These are **participant-driven** tasks. You drive the **`oc`** CLI on the shared
**OpenShift 4.18** cluster, then verify with the provided **validation** commands. Each
exercise has a fully worked **solution** — try the tasks first, then check.

Module 6 — **"OpenShift Networking, Routes and Multi-Tenancy"** — is about reachability
and safety: **Services & DNS** inside the cluster, **Routes** with TLS to the outside,
and **NetworkPolicies** for tenant isolation. Services/DNS/NetworkPolicy are standard
Kubernetes; **Routes** are OpenShift-specific.

## Where to run these

| Target | What you can do | Notes |
|---|---|---|
| **Shared OpenShift 4.18 cluster** (preferred) | Everything in your own project(s) | The capstone (Ex 3) needs a **second project** for cross-tenant tests |
| **[Developer Sandbox](https://developers.redhat.com/developer-sandbox)** | Services, DNS, Routes, single-project NetworkPolicies | Only **one** project → the cross-tenant block is instructor-demoed |

> **`oc` == `kubectl`** for Services, DNS, and NetworkPolicies. Only **Routes**
> (`oc expose service`, `oc create route`) are OpenShift-specific.

## Exercises in this module

| # | Exercise | What you'll practice | Telecom scenario | Difficulty |
|---|----------|----------------------|------------------|------------|
| 1 | [Services & DNS](exercise-01-services-and-dns.md) | `oc expose`, ClusterIP, CoreDNS names, EndpointSlices | Wire **self-care → subscriber-api** | ⭐ Beginner |
| 2 | [Routes & TLS](exercise-02-routes-and-tls.md) | HTTP/edge Routes, TLS modes, `curl` via router, Ingress→Route | Publish the **self-care portal** | ⭐⭐ Intermediate |
| 3 | [NetworkPolicy + multi-tenant capstone](exercise-03-networkpolicy-multitenant-capstone.md) | default-deny + allows, cross-tenant block, isolation baseline | Isolate **billing from CRM** | ⭐⭐⭐ Advanced |

## Before you start

```bash
oc login https://api.<cluster-domain>:6443 -u <user> -p "$OCP_PASSWORD"   # or token
oc whoami
oc new-project mod6-ex --display-name="Module 6 Exercises" 2>/dev/null || oc project mod6-ex
# Your *.apps domain (a normal user cannot read ingresses.config/cluster) — read it off a
# Route's HOST once you create one: everything after the first dot is the apps domain.
```

- Images: **`ubi9/httpd-24`** serves HTTP on **8080** (doc-root `/var/www/html`; run its
  default command — don't override with `httpd -DFOREGROUND`). A bare `GET /` returns
  **403** (no index) — a 403 *proves connectivity*. `ubi9/ubi-minimal` is the throwaway
  `curl` client.
- Replace placeholders (`<cluster-domain>`, `<domain>`). **Never commit real certs/keys**
  — TLS material is placeholder.
- The capstone (Ex 3) needs a **second project**; on the Sandbox (one project) do the
  single-namespace parts and follow the instructor for the cross-tenant block.
- Cleanup: `oc delete project mod6-ex` (and any second project) removes everything.

## How to self-assess

Each exercise's **Validation** section gives commands whose output confirms success. If
your output matches the *shape* shown, you've done it. Stuck? The **Solution** walks one
correct approach.

Companion material: the guided [demos](../demos/README.md), the interactive
[visualizations](../index.html), and the
[concept guide](../../../guides/module-06-networking-routes-multitenancy.md).

---

> **✅ Verified on cluster (2026-07-05, as learner25).** Exercises 1–3 were validated live
> on OpenShift 4.18 (k8s v1.31.14) as **learner25**, a normal developer/self-provisioner —
> Services & DNS, Routes & edge TLS, and NetworkPolicy tenant isolation all reproduce the
> output shown. Two corrections applied from that run: use **`oc create deployment`** (not
> `oc new-app`, which pre-creates a Service), and NetworkPolicy selectors use **`app=`**
> labels. Passthrough/re-encrypt Routes remain representative (need HTTPS backend + certs).
