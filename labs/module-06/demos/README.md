# Module 6 — Guided Demos (Instructor-Led)

These are **instructor-led, narrated walkthroughs**. The instructor runs each step live
against the real **OpenShift 4.18** cluster while explaining *what* each networking
object does and *why*. Participants watch and follow along, then practice in the
[`../exercises`](../exercises).

Module 6 — **"OpenShift Networking, Routes and Multi-Tenancy"** — is about making apps
**reachable** and keeping that reachability **safe**: Services & DNS inside the cluster,
**Routes** with TLS to the outside, and **NetworkPolicies** for tenant isolation.
Commands are **`oc`**; Services/DNS/NetworkPolicy are standard Kubernetes, **Routes** are
OpenShift-specific.

All scenarios use a **telecom domain** framing (self-care portal, subscriber-api,
subscriber-db, SMS gateway, `team-billing`/`team-crm` tenants). Data is fictional.

## Demos in this module

| # | Demo | Concepts reinforced | Telecom scenario | Time |
|---|------|---------------------|------------------|------|
| 1 | [Services & DNS](demo-01-services-and-dns.md) | `oc expose` · ClusterIP · CoreDNS names · EndpointSlices | Wire **self-care → subscriber-api** | ~25 min |
| 2 | [Routes & TLS termination](demo-02-routes-and-tls.md) | `oc expose`/`oc create route` · edge/passthrough/re-encrypt · Ingress→Route | Publish the **self-care portal** | ~30 min |
| 3 | [NetworkPolicies & tenant isolation](demo-03-network-policies-tenant-isolation.md) | default-deny · allow-same-ns · allow-from-ingress · cross-tenant block | Isolate **billing from CRM** | ~30 min |

## Conventions

- Commands use **`oc`**. Services, DNS, and NetworkPolicy are pure `kubectl` (an **⎈**
  note flags this); **Routes** and `oc expose svc` → Route are OpenShift-specific.
- **Podman-first images:** demos use Red Hat **UBI** images (`ubi9/httpd-24` serves HTTP
  on **8080**, doc-root `/var/www/html`; run its default command — do *not* override with
  `httpd -DFOREGROUND`). `ubi9/ubi-minimal` is the throwaway client for `curl`.
- **Permissions.** A normal project user can do Demos 1–3 **inside their own project**.
  Cross-namespace NetworkPolicy tests (Demo 3) need a **second project** — the instructor
  uses two. Creating custom-hostname/secured Routes may need cluster config for real
  certs; the auto-hostname edge case works for everyone.
- Replace placeholders (`<domain>`, `<cluster-domain>`) with your cluster's values.
  **Never commit real certs/keys** — TLS material is placeholder (`tls.crt`, `tls.key`).
- Each demo ends with a **Cleanup** section (delete the demo project).
- Companion material: the
  [concept guide](../../../guides/module-06-networking-routes-multitenancy.md), the
  interactive [visualizations](../index.html), and the
  [exercises](../exercises/README.md).

## Pre-flight check (run once before Demo 1)

```bash
oc login https://api.<cluster-domain>:6443 -u <user> -p "$OCP_PASSWORD"   # or token
oc whoami
oc new-project mod6-demos --display-name="Module 6 Demos" 2>/dev/null || oc project mod6-demos
# Find your *.apps domain WITHOUT cluster-admin: create any route and read its HOST.
# (oc get ingresses.config/cluster is Forbidden for a normal user.)
oc create deployment probe --image=registry.access.redhat.com/ubi9/httpd-24:latest
oc expose deployment probe --port=8080 && oc expose service probe
oc get route probe -o jsonpath='{.spec.host}{"\n"}'   # domain = everything after the 1st dot
oc delete all -l app=probe
```

> **Instructor tip:** keep the **web console** open beside the terminal — the
> **Networking → Routes** and **Networking → NetworkPolicies** views mirror the CLI. For
> Demo 3, pre-create a second project (`mod6-crm`) so the cross-tenant block is visible.
> Pre-pull `ubi9/httpd-24` and `ubi9/ubi-minimal` so the first pod starts fast.

---

> **✅ Verified on cluster (2026-07-05, as learner25).** All three demos were run live on
> OpenShift 4.18 (k8s v1.31.14) as **learner25**, a normal developer/self-provisioner —
> Services & DNS, Routes & edge TLS, and NetworkPolicy tenant isolation all reproduce the
> output shown. Two corrections applied from that run: use **`oc create deployment`** (not
> `oc new-app`, which pre-creates a Service), and NetworkPolicy selectors use **`app=`**
> labels. Passthrough/re-encrypt Routes (Demo 2, Step 3) remain **representative** — they
> need an HTTPS backend + real certs.
