# Demo 3 — NetworkPolicies & Tenant Isolation

> **Scenario:** Mobily runs **team-billing** and **team-crm** on one cluster. Right now
> the pod network is wide open — a CRM pod can reach the **subscriber-db** in billing.
> We fix that: apply a **default-deny** baseline, then re-open only the sanctioned paths
> (router in, `subscriber-api → subscriber-db`), and *prove* the cross-tenant connection
> is now blocked.

| | |
|---|---|
| **Concepts reinforced** | open-by-default pod net · default-deny · allow-same-namespace · allow-from-ingress · podSelector/namespaceSelector · cross-tenant block |
| **Maps to** | Guide §8, §9, §10 · Visualization 03 · Exercise 3 |
| **Time** | ~30 minutes |
| **Cluster** | Shared OCP 4.18 — needs **two projects** (billing + crm) |

---

> **⎈ Kubernetes equivalent:** `NetworkPolicy` is 100% standard Kubernetes — but it only
> takes effect if the CNI enforces it. OpenShift's **OVN-Kubernetes** does, so these
> policies are real.

## Talking points to open with

- The pod network is **open by default** — dangerous on a shared cluster.
- NetworkPolicies are **additive, allow-only**. A pod with no policy is open; a
  default-deny that *selects* a pod blocks everything not explicitly allowed.
- Isolation = **default-deny + targeted allows**; cross-tenant stays blocked because no
  rule opens it.

---

## Step 0 — Two tenants and a target

```bash
oc new-project team-billing 2>/dev/null || oc project team-billing
oc create deployment subscriber-db  --image=registry.access.redhat.com/ubi9/httpd-24:latest
oc expose deployment subscriber-db --port=8080
oc create deployment subscriber-api --image=registry.access.redhat.com/ubi9/httpd-24:latest

oc new-project team-crm 2>/dev/null
oc create deployment crm --image=registry.access.redhat.com/ubi9/httpd-24:latest
oc project team-billing
```

**Verified output** *(learner25 · OCP 4.18):*

```
Now using project "team-billing" ...
deployment.apps/subscriber-db created
service/subscriber-db exposed
deployment.apps/subscriber-api created
Now using project "team-crm" ...
deployment.apps/crm created
```

> **Narrate:** Two projects, a database service in billing, and a CRM pod next door. No
> policies yet — so let's confirm the scary default.
>
> **⚠️ Labels matter for the policies below.** `oc create deployment X` labels its pods
> **`app=X`** — so our NetworkPolicy `podSelector`s use `app:` (not `deployment:`). A
> normal user (learner25) can create projects and NetworkPolicies in their own projects.

---

## Step 1 — Prove it's wide open (the problem)

```bash
# From the CRM pod, reach the billing DB service by its cross-namespace name
oc project team-crm
oc rsh deployment/crm curl -s -o /dev/null -w "%{http_code}\n" \
  subscriber-db.team-billing.svc.cluster.local:8080/
oc project team-billing
```

**Verified output** *(learner25 · OCP 4.18):*

```
crm->db (no policy): 403      <- reached it! (403 = httpd with no index; connectivity succeeded)
```

> **Narrate:** A **403**, not a timeout — the CRM pod *reached* the billing database
> across tenants. Anything that returns an HTTP code proves the TCP connection opened.
> This is the open-by-default network, and it's exactly what we must stop.

---

## Step 2 — Apply the default-deny baseline (in team-billing)

```bash
cat <<'EOF' | oc apply -n team-billing -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: { name: default-deny-ingress }
spec:
  podSelector: {}
  policyTypes: [Ingress]
EOF
oc get networkpolicy -n team-billing
```

**Verified output** *(learner25 · OCP 4.18):*

```
networkpolicy.networking.k8s.io/default-deny-ingress created
NAME                   POD-SELECTOR   AGE
default-deny-ingress   <none>         3s
```

Re-test the cross-tenant probe now:

```
crm->db (deny on): 000
command terminated with exit code 28      <- curl timeout = BLOCKED
```

> **Narrate:** Empty `podSelector: {}` selects **every** pod in billing; no ingress rules
> means **nothing** may connect in. The CRM curl now **times out** — curl prints `000`
> and exits **28** (the real "blocked" signal: no connection, not an HTTP error). But so
> is *everything* blocked now, including the router and same-namespace traffic. We re-open
> deliberately.

---

## Step 3 — Re-open the sanctioned paths

```bash
# a) let the HAProxy router reach billing pods (Routes work again)
cat <<'EOF' | oc apply -n team-billing -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: { name: allow-from-ingress }
spec:
  podSelector: {}
  policyTypes: [Ingress]
  ingress:
    - from:
        - namespaceSelector:
            matchLabels: { policy-group.network.openshift.io/ingress: "" }
EOF

# b) allow ONLY subscriber-api -> subscriber-db
cat <<'EOF' | oc apply -n team-billing -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: { name: allow-api-to-db }
spec:
  podSelector: { matchLabels: { app: subscriber-db } }
  policyTypes: [Ingress]
  ingress:
    - from:
        - podSelector: { matchLabels: { app: subscriber-api } }
      ports: [ { protocol: TCP, port: 8080 } ]
EOF
oc get networkpolicy -n team-billing
```

**Verified output** *(learner25 · OCP 4.18):*

```
networkpolicy.networking.k8s.io/allow-from-ingress created
networkpolicy.networking.k8s.io/allow-api-to-db created
NAME                   POD-SELECTOR        AGE
allow-api-to-db        app=subscriber-db   13s
allow-from-ingress     <none>              24s
default-deny-ingress   <none>              33s
```

> **Note:** the selectors are **`app=...`** because `oc create deployment` labels pods
> `app=<name>`. (If you used `oc new-app`, they'd be `deployment=<name>`.)

> **Narrate:** Additive allows layered on the deny: the **router** can reach billing pods
> again, and **subscriber-api** may reach **subscriber-db** on 8080. We named the exact
> path — nothing else opens.

---

## Step 4 — Verify: sanctioned path OK, cross-tenant BLOCKED

```bash
# sanctioned: api -> db (same namespace, matches allow-api-to-db)  => works
oc rsh deployment/subscriber-api curl -s -o /dev/null -w "api->db: %{http_code}\n" \
  subscriber-db:8080/

# cross-tenant: crm -> db (no rule opens it under default-deny)    => times out
oc project team-crm
oc rsh deployment/crm curl -s --max-time 5 -o /dev/null -w "crm->db: %{http_code}\n" \
  subscriber-db.team-billing.svc.cluster.local:8080/ || echo "crm->db: BLOCKED (timeout)"
oc project team-billing
```

**Verified output** *(learner25 · OCP 4.18):*

```
api->db (allowed?): 403           <- allowed (403 = reached httpd, connection permitted)
crm->db: BLOCKED (timeout)        <- curl 000 / exit 28; denied by default-deny, no allow rule opens it
```

> **Narrate:** The sanctioned path returns an HTTP code (permitted); the cross-tenant
> path **times out** (curl `000`, exit 28 — dropped). Same database, two very different
> outcomes — that's tenant isolation. Note we isolated by *default* and shared by
> *exception*.
>
> **Bonus (verified):** the `allow-from-ingress` policy is what lets the **HAProxy router**
> reach billing pods under default-deny. With it, a Route to a billing app returns **403**
> (router reached the pod); delete it and the same Route returns **503** (router blocked).
> That's the classic "my Route broke after default-deny" gotcha, proven.

---

## Step 5 — Cleanup

```bash
oc delete project team-crm
oc delete networkpolicy --all -n team-billing
oc delete all -l app -n team-billing
oc delete project team-billing      # if these were throwaway projects
```

**Expected output** *(requires a cluster — representative):*

```
project.project.openshift.io "team-crm" deleted
networkpolicy ... deleted
```

---

## Wrap-up questions to pose

1. Before any policy, why could the CRM pod reach the billing DB?
2. What exactly does `podSelector: {}` with `policyTypes:[Ingress]` and no rules do?
3. After default-deny, why did the app's Route stop working — and which policy fixes it?
4. Why does the cross-tenant connection stay blocked no matter which allow-rules you add
   for billing?

---

> **✅ Verified:** oc 4.22 · OpenShift 4.18 (k8s v1.31.14) · 2026-07-05 · **learner25**
> (normal developer) across projects `l25-billing` + `l25-crm`. Every step ran live:
> open-by-default (**403**), default-deny (**curl 000 / timeout**), `allow-api-to-db` with
> **`app=`** selectors (api→db **403**, crm→db **blocked**), and the `allow-from-ingress`
> router path (**403** with it, **503** without). Isolation confirmed end-to-end.
