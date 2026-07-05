# Exercise 2 — Explore MachineConfig & MachineConfigPools

> **Scenario:** Before Mobily rolls a node-config change, you need to understand how
> node configuration actually works on this cluster: which **pools** exist, what
> **rendered config** each runs, and (if you have admin) how a **MachineConfig** rolls
> out — and how you'd **pause** a pool to protect a billing window.

| | |
|---|---|
| **Practice** | `oc get mcp`/`machineconfig` · rendered config · pool conditions · (admin) apply + pause |
| **Maps to** | Guide §5 · Visualization 03 · Demo 2 |
| **Difficulty** | ⭐⭐ Intermediate · ~25 min · reads OK; **apply needs cluster-admin** |

---

## Tasks

1. List the **MachineConfigPools** and read each one's `UPDATED / UPDATING / DEGRADED`
   and machine counts.
2. Find the **rendered config name** currently applied to the **worker** pool.
3. List **MachineConfigs** and identify which are *source* configs vs the `rendered-*`
   merge.
4. `oc describe mcp worker` and read its **node selector**, `maxUnavailable`, and
   current/updated machine counts.
5. **(admin)** Write a MachineConfig that adds a small file to the worker pool, apply
   it, and observe the pool go `UPDATING → UPDATED` (one node at a time). *If not admin,*
   write the YAML and `--dry-run=server` it, and explain what *would* happen.
6. **(admin)** Show how to **pause** then **unpause** the worker pool, and explain when
   you'd do that.

> **Hint (Task 2):** `oc get mcp worker -o jsonpath='{.spec.configuration.name}{"\n"}'`.

> **Hint (Task 5):** target a pool with the label
> `machineconfiguration.openshift.io/role: worker`; use Ignition `version: 3.4.0`.

---

## Validation

```bash
# Task 1
oc get machineconfigpool

# Task 2 — the worker pool's rendered config
oc get mcp worker -o jsonpath='{.spec.configuration.name}{"\n"}'

# Task 4 — maxUnavailable + counts
oc get mcp worker -o jsonpath='maxUnavailable={.spec.maxUnavailable} machines={.status.machineCount} updated={.status.updatedMachineCount}{"\n"}'

# Task 5 (admin) — after apply, pool transitions
oc get mcp worker -w
```

---

## Reflection

- RHCOS is immutable. So *how* does a file get onto every worker, and what object
  expresses that intent?
- What's the difference between a **source** MachineConfig and a **rendered** one?
- With `maxUnavailable=1`, why does the subscriber-api stay up during a rollout?

---

<details>
<summary><strong>✅ Solution</strong> (try the tasks first)</summary>

```bash
# 1. Pools
oc get mcp

# 2. Worker rendered config
oc get mcp worker -o jsonpath='{.spec.configuration.name}{"\n"}'      # rendered-worker-<hash>

# 3. Source vs rendered
oc get machineconfig | grep -v '^rendered'    # source configs (00-*, 99-*, your 50-*)
oc get machineconfig | grep '^rendered'       # merged outputs

# 4. Describe the pool
oc describe mcp worker | sed -n '/Node Selector/,/Configuration/p'
oc get mcp worker -o jsonpath='maxUnavailable={.spec.maxUnavailable} machines={.status.machineCount} updated={.status.updatedMachineCount}{"\n"}'

# 5. (admin) Apply a tiny MachineConfig to the worker pool
cat <<'EOF' | oc apply -f -          # add --dry-run=server if not admin
apiVersion: machineconfiguration.openshift.io/v1
kind: MachineConfig
metadata:
  labels: { machineconfiguration.openshift.io/role: worker }
  name: 50-worker-mobily-motd
spec:
  config:
    ignition: { version: 3.4.0 }
    storage:
      files:
        - path: /etc/mobily-motd
          mode: 0644
          contents: { source: "data:text/plain;charset=utf-8;base64,TW9iaWx5IG5vZGUK" }
EOF
oc get mcp worker -w        # UPDATING=True, one node at a time, then UPDATED=True

# 6. (admin) Pause / unpause
oc patch mcp worker --type merge -p '{"spec":{"paused":true}}'    # batch / protect window
oc patch mcp worker --type merge -p '{"spec":{"paused":false}}'   # roll out

# Cleanup (admin)
oc delete machineconfig 50-worker-mobily-motd
oc patch mcp worker --type merge -p '{"spec":{"paused":false}}'
```

**Representative output** *(requires a cluster; apply needs admin — OCP 4.18):*

```
NAME     CONFIG                    UPDATED   UPDATING   DEGRADED   MACHINECOUNT   READYMACHINECOUNT
master   rendered-master-9f3c...   True      False      False      3              3
worker   rendered-worker-a1b2...   True      False      False      2              2

# worker rendered config:
rendered-worker-a1b2c3d4...

# after apply:
worker   rendered-worker-a1b2...   False     True       False      2              1
worker   rendered-worker-c3d4...   True      False      False      2              2
```

**Key point:** you never SSH a node. A **MachineConfig** (source) targets a **pool**;
the MCO renders all source configs into one `rendered-*` and rolls it node-by-node
(`maxUnavailable=1`), draining first — so apps stay up. **Pause** to batch changes or
freeze reboots during a sensitive window.
</details>

---

> **◐ Partially verified:** all `oc get/describe/patch/apply` against MachineConfig
> objects **require a live OpenShift cluster** (apply/patch need cluster-admin) and were
> not runnable here. Output is **representative of OpenShift 4.18**; the YAML follows the
> Ignition 3.4.0 schema. Run live for your real pool names and rendered hashes. Nothing
> is presented as independently verified.
