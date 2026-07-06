# Module 7 — Exercises (Hands-On Practice)

These are **participant-driven** tasks. You drive the **`oc`** CLI on the shared
**OpenShift 4.18** cluster, then verify with the provided **validation** commands. Each
exercise has a fully worked **solution** — try the tasks first, then check.

Module 7 — **"Storage and Security Fundamentals"** — covers durable **storage** (PV, PVC,
StorageClass) and core **security** (SCC, ServiceAccounts, Secrets). PV/PVC/SA/Secret are
standard Kubernetes; **SCC** is OpenShift-specific.

## Where to run these

| Target | What you can do | Notes |
|---|---|---|
| **Shared OpenShift 4.18 cluster** (preferred) | PVCs, ServiceAccounts, Secrets in your project | Needs a **default StorageClass** for Ex 1 |
| **[Developer Sandbox](https://developers.redhat.com/developer-sandbox)** | Same (usually has a default StorageClass) | SCC *grants* (Ex 2) need cluster-admin → instructor-led |

> **`oc` == `kubectl`** for PV/PVC, StorageClass, ServiceAccount, Secret. Only **SCC**
> and `oc adm policy add-scc-to-user` are OpenShift-specific (and admin-gated).

## Exercises in this module

| # | Exercise | What you'll practice | Telecom scenario | Difficulty |
|---|----------|----------------------|------------------|------------|
| 1 | [Persistent storage](exercise-01-persistent-storage.md) | PVC, dynamic provisioning, mount, persistence, access modes | **CDR archive** survives pods | ⭐ Beginner |
| 2 | [Security Context Constraints](exercise-02-scc.md) | observe SCC/UID, read denial, (admin) grant SCC to an SA | Run a **root-requiring** image | ⭐⭐ Intermediate |
| 3 | [Stateful + secure app (capstone)](exercise-03-sa-secrets-capstone.md) | SA + Secret + PVC + SCC together | **billing** app, durable & secure | ⭐⭐⭐ Advanced |

## Before you start

```bash
oc login https://api.<cluster-domain>:6443 -u <user> -p "$OCP_PASSWORD"   # or token
oc whoami
oc new-project mod7-ex --display-name="Module 7 Exercises" 2>/dev/null || oc project mod7-ex
oc get storageclass          # confirm a (default) class exists (Ex 1)
```

- Images: **`ubi9/httpd-24`** serves HTTP on **8080** and runs **rootless** (a bare
  `GET /` returns **403** — proof of connectivity). `ubi9/ubi-minimal` is the throwaway
  client.
- Use **`oc create deployment`** (not `oc new-app`) so `oc set volume`/`oc expose` behave
  predictably; it labels pods `app=<name>`.
- Replace placeholders (`<cluster-domain>`, `<your-password>`). **Never commit real
  secrets** — all credential values are fictional.
- **SCC grants** (Ex 2) need **cluster-admin**; if you're a normal user, do the *observe
  and reason* parts and follow the instructor for the grant.
- Cleanup: `oc delete project mod7-ex` removes everything.

## How to self-assess

Each exercise's **Validation** section gives commands whose output confirms success. If
your output matches the *shape* shown, you've done it. Stuck? The **Solution** walks one
correct approach.

Companion material: the guided [demos](../demos/README.md), the interactive
[visualizations](../index.html), and the
[concept guide](../../../guides/module-07-storage-security.md).

---

> **◐ Partially verified (cluster asleep at authoring).** Client-side `oc` help
> (`oc create secret|serviceaccount`, `oc set volume`, `oc adm policy add-scc-to-user`)
> confirmed with **oc 4.22**. Cluster-dependent output is **representative of OpenShift
> 4.18** and can be validated as **learner25** when the cluster is up (storage/SA/Secret
> as a normal user; SCC grant as an admin) — the same way Module 6 was validated.
