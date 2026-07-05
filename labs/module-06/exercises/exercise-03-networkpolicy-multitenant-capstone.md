# Exercise 3 — NetworkPolicy + Multi-Tenant Isolation (Capstone)

> **Scenario:** Mobily's **team-billing** and **team-crm** share one cluster. Today a CRM
> pod can reach the billing **subscriber-db** — unacceptable. As platform engineer, lock
> billing down to a **default-deny** baseline, re-open only the sanctioned paths (router
> in, `subscriber-api → subscriber-db`), and **prove** the cross-tenant connection is
> blocked while the app still works. This capstone combines Services, Routes, and
> NetworkPolicies into real tenant isolation.

| | |
|---|---|
| **Practice** | default-deny · allow-from-ingress · allow-api-to-db · podSelector/namespaceSelector · cross-tenant verification |
| **Maps to** | Guide §8, §9, §10 · Visualization 03 · Demo 3 |
| **Difficulty** | ⭐⭐⭐ Advanced (capstone) · ~30–35 min · **needs two projects** |

> ⚠️ **Two projects required** for the cross-tenant test. On the Developer Sandbox (one
> project) do the single-namespace default-deny/allow parts and follow the instructor for
> the cross-tenant block.

---

## Tasks

1. In **team-billing**, deploy **subscriber-db** (Service on 8080) and **subscriber-api**.
   In **team-crm**, deploy **crm**.
2. **Prove the problem:** from the CRM pod, reach `subscriber-db.team-billing…` and
   confirm it currently **succeeds** (403 = reached).
3. Apply a **default-deny-ingress** policy in team-billing. Re-test the CRM connection and
   confirm it now **times out**.
4. Restore external access: add **allow-from-ingress** so the HAProxy router can reach
   billing pods (needed for Routes).
5. Restore the app path: add **allow-api-to-db** permitting *only* `subscriber-api →
   subscriber-db` on 8080.
6. **Verify the end state:** `api → db` **works**, `crm → db` (cross-tenant) **stays
   blocked**. Explain why no billing allow-rule ever opens the CRM path.
7. Name the **full stack** of layers (beyond NetworkPolicy) that make a real tenant
   boundary.

> **Hint (Task 4):** allow ingress from `namespaceSelector` matching label
> `policy-group.network.openshift.io/ingress: ""`.

> **Hint (Task 6):** `--max-time 5` on `curl` so a blocked call fails fast instead of
> hanging.

---

## Validation

```bash
# Task 2/3/6 — the cross-tenant probe (run from team-crm)
oc rsh -n team-crm deployment/crm curl -s --max-time 5 -o /dev/null \
  -w "crm->db: %{http_code}\n" subscriber-db.team-billing.svc.cluster.local:8080/ \
  || echo "crm->db: BLOCKED"

# Task 6 — the sanctioned path (run from team-billing)
oc rsh -n team-billing deployment/subscriber-api curl -s -o /dev/null \
  -w "api->db: %{http_code}\n" subscriber-db:8080/

# policies in place
oc get networkpolicy -n team-billing
```

---

## Reflection

- Before any policy, *why* could CRM reach the billing DB?
- After default-deny, the app's Route broke too — which policy restores it, and what does
  it match on?
- Why does the cross-tenant CRM→db connection remain blocked regardless of the billing
  allow-rules you add?

---

<details>
<summary><strong>✅ Solution</strong> (try the tasks first)</summary>

```bash
# 1. Two tenants  (use `oc create deployment` — labels pods app=<name>, and does not
#    pre-create a Service, so `oc expose deployment` works)
oc new-project team-billing 2>/dev/null || oc project team-billing
oc create deployment subscriber-db  --image=registry.access.redhat.com/ubi9/httpd-24:latest
oc expose deployment subscriber-db --port=8080
oc create deployment subscriber-api --image=registry.access.redhat.com/ubi9/httpd-24:latest
oc new-project team-crm 2>/dev/null
oc create deployment crm --image=registry.access.redhat.com/ubi9/httpd-24:latest

# 2. Prove it's open (403 = reached)
oc rsh -n team-crm deployment/crm curl -s --max-time 5 -o /dev/null \
  -w "crm->db: %{http_code}\n" subscriber-db.team-billing.svc.cluster.local:8080/

# 3. default-deny in billing
oc apply -n team-billing -f - <<'EOF'
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: { name: default-deny-ingress }
spec: { podSelector: {}, policyTypes: [Ingress] }
EOF
# re-test -> now times out (BLOCKED)

# 4. allow the router in (Routes work again)
oc apply -n team-billing -f - <<'EOF'
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: { name: allow-from-ingress }
spec:
  podSelector: {}
  policyTypes: [Ingress]
  ingress:
    - from: [ { namespaceSelector: { matchLabels: { policy-group.network.openshift.io/ingress: "" } } } ]
EOF

# 5. allow ONLY api -> db
oc apply -n team-billing -f - <<'EOF'
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: { name: allow-api-to-db }
spec:
  podSelector: { matchLabels: { app: subscriber-db } }
  policyTypes: [Ingress]
  ingress:
    - from: [ { podSelector: { matchLabels: { app: subscriber-api } } } ]
      ports: [ { protocol: TCP, port: 8080 } ]
EOF

# 6. Verify end state
oc rsh -n team-billing deployment/subscriber-api curl -s -o /dev/null -w "api->db: %{http_code}\n" subscriber-db:8080/
oc rsh -n team-crm deployment/crm curl -s --max-time 5 -o /dev/null -w "crm->db: %{http_code}\n" \
  subscriber-db.team-billing.svc.cluster.local:8080/ || echo "crm->db: BLOCKED"

# 7. Full tenant boundary = Project + RBAC (who) + ResourceQuota/LimitRange (how much)
#    + NetworkPolicy (who talks to whom) + route sharding (how exposed) [+ dedicated nodes for hard tenancy].

# Cleanup
oc delete project team-crm
oc delete networkpolicy --all -n team-billing ; oc delete all -l app -n team-billing
oc delete project team-billing   # if throwaway
```

**Verified output** *(learner25 · OCP 4.18 · projects `l25-billing` + `l25-crm`):*

```
crm->db (no policy): 403     # step 2: open by default (reached)
crm->db: 000 / exit 28       # step 3: default-deny drops it (curl timeout = BLOCKED)
api->db (allowed?): 403      # step 6: sanctioned path allowed
crm->db: 000 / BLOCKED       # step 6: cross-tenant still denied

NAME                   POD-SELECTOR        AGE
allow-api-to-db        app=subscriber-db   13s
allow-from-ingress     <none>              24s
default-deny-ingress   <none>              33s
```

> Bonus (verified): with `allow-from-ingress` present, a Route to a billing app returns
> **403** (router reaches the pod); delete that policy and the same Route returns **503**
> (default-deny blocks the router).

**Key point:** the pod network is **open by default** — the CRM pod reached billing until
a **default-deny** selected the billing pods. NetworkPolicies are **additive allow-only**:
you re-open the router path and the `api→db` path *explicitly*, and the cross-tenant
connection stays blocked because **no billing policy ever names team-crm as allowed**.
Isolate by default, share by exception — layered with Project + RBAC + quota for a full
tenant boundary.
</details>

---

> **✅ Verified:** oc 4.22 · OpenShift 4.18 (k8s v1.31.14) · 2026-07-05 · **learner25**
> (normal developer) across projects `l25-billing` + `l25-crm`. Ran live: open-by-default
> (**403**), default-deny (**curl 000 / timeout**), `allow-api-to-db` with **`app=`**
> selectors (api→db **403**, crm→db **blocked**), and the `allow-from-ingress` router path
> (**403** with it, **503** without). Cross-tenant isolation confirmed end-to-end.
