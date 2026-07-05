# Demo 2 — MachineConfig & MachineConfigPools

> **Scenario:** Mobily's internal registry uses a certificate signed by a **corporate
> root CA**. Every worker node must trust it — but RHCOS is immutable and we don't SSH
> into nodes. We'll inspect the **MachineConfigPools**, apply a **MachineConfig** that
> drops the CA file onto every worker, and watch the **MCO** roll it out node-by-node,
> then show how **pausing** a pool batches changes.

| | |
|---|---|
| **Concepts reinforced** | `MachineConfig` (Ignition) · `MachineConfigPool` · MCO render & rollout · `maxUnavailable` · pause/unpause |
| **Maps to** | Guide §5 · Visualization 03 · Exercise 2 |
| **Time** | ~30 minutes |
| **Cluster** | Shared OCP 4.18 — **applying** needs **cluster-admin** (reads are read-only) |

---

> **⎈ Kubernetes equivalent:** none — `MachineConfig`/`MachineConfigPool` are
> OpenShift's answer to node configuration that vanilla Kubernetes leaves to Ansible or
> golden images. `oc get`/`describe`/`patch` are standard `kubectl` verbs.

> ⚠️ **Admin-only apply.** Step 3 modifies node config and triggers reboots — instructor
> runs it on a lab cluster, or demonstrates with `--dry-run=server`. Reads (Steps 1–2)
> are safe.

## Talking points to open with

- Immutable nodes don't mean *unchangeable* — they mean changed **declaratively**.
- A `MachineConfig` targets a **pool**; the MCO **renders** all configs for that pool
  into one and rolls it out safely (cordon → drain → reboot, one node at a time).
- **Pause** a pool to batch changes or protect a maintenance window.

---

## Step 1 — Inspect the pools

```bash
oc get machineconfigpool        # alias: oc get mcp
```

**Expected output** *(requires a cluster — representative):*

```
NAME     CONFIG                     UPDATED   UPDATING   DEGRADED   MACHINECOUNT   READYMACHINECOUNT   AGE
master   rendered-master-9f3c...    True      False      False      3              3                   40d
worker   rendered-worker-a1b2...    True      False      False      2              2                   40d
```

> **Narrate:** Two default pools, **master** and **worker**. `UPDATED=True` means every
> node in the pool runs the **rendered** config (the merged result of all MachineConfigs
> targeting it). We'll change the worker pool's rendered config by adding one.

---

## Step 2 — Look at existing MachineConfigs

```bash
oc get machineconfig | head
```

**Expected output** *(requires a cluster — representative):*

```
NAME                                  GENERATEDBYCONTROLLER   IGNITIONVERSION   AGE
00-master                             ...                     3.4.0             40d
00-worker                             ...                     3.4.0             40d
99-worker-generated-registries        ...                     3.4.0             40d
rendered-worker-a1b2c3...             ...                     3.4.0             40d
...
```

> **Narrate:** Source MachineConfigs (numbered) plus the `rendered-*` merge the MCO
> produces. We add a new source config; the MCO regenerates the `rendered-worker-*` and
> rolls it.

---

## Step 3 — Apply a MachineConfig (admin) — trust the corporate CA

```bash
cat <<'EOF' | oc apply -f -
apiVersion: machineconfiguration.openshift.io/v1
kind: MachineConfig
metadata:
  labels:
    machineconfiguration.openshift.io/role: worker
  name: 50-worker-mobily-corp-ca
spec:
  config:
    ignition:
      version: 3.4.0
    storage:
      files:
        - path: /etc/pki/ca-trust/source/anchors/mobily-corp-ca.crt
          mode: 0644
          contents:
            source: data:text/plain;base64,<BASE64_OF_CA_PEM>
EOF
```

**Expected output** *(requires admin on a cluster — representative):*

```
machineconfig.machineconfiguration.openshift.io/50-worker-mobily-corp-ca created
```

> **Narrate:** A small declarative file — `role: worker` targets the worker pool, the
> Ignition `storage.files` entry drops the CA. We never named a node; the MCO will place
> it on **all** workers. *(The base64 blob is a placeholder — supply your real CA.)*

---

## Step 4 — Watch the pool roll it out

```bash
oc get mcp worker -w
# in another terminal, watch nodes cordon/drain/reboot:
oc get nodes -w
```

**Expected output** *(requires a cluster — representative):*

```
NAME     CONFIG                    UPDATED   UPDATING   DEGRADED   MACHINECOUNT   READYMACHINECOUNT
worker   rendered-worker-a1b2...   False     True       False      2              1
worker   rendered-worker-c3d4...   True      False      False      2              2
# nodes: worker-0 -> SchedulingDisabled (drain) -> reboot -> Ready, then worker-1
```

> **Narrate:** `UPDATING=True`, one node at a time (**maxUnavailable=1** by default):
> cordon → drain → write file → reboot → Ready, then the next. Capacity never drops below
> one worker, so the subscriber-api keeps serving. When `UPDATED=True` returns, every
> worker trusts the CA.

---

## Step 5 — Pause a pool to batch / protect a window

```bash
oc patch mcp worker --type merge -p '{"spec":{"paused":true}}'
# ... apply several MachineConfigs here; nothing reboots ...
oc get mcp worker      # UPDATED stays True; changes are queued
oc patch mcp worker --type merge -p '{"spec":{"paused":false}}'   # now it rolls once
```

**Expected output** *(requires admin — representative):*

```
machineconfigpool.machineconfiguration.openshift.io/worker patched
...
machineconfigpool.machineconfiguration.openshift.io/worker patched
```

> **Narrate:** With the pool **paused**, config accumulates but no node reboots — perfect
> for Mobily's nightly billing window, or to apply five changes and reboot each node
> **once**. Unpause and the MCO renders everything together and rolls it.

---

## Step 6 — Cleanup (admin)

```bash
oc delete machineconfig 50-worker-mobily-corp-ca
oc patch mcp worker --type merge -p '{"spec":{"paused":false}}'   # ensure not left paused
```

**Expected output** *(requires admin — representative):*

```
machineconfig.machineconfiguration.openshift.io "50-worker-mobily-corp-ca" deleted
```

> **Narrate:** Deleting the source MachineConfig regenerates the rendered config *without*
> the CA and rolls the nodes back — the same loop in reverse. Always leave pools
> **unpaused**.

---

## Wrap-up questions to pose

1. How do you change a file on every worker without SSH?
2. What does a MachineConfigPool group, and what is a `rendered-*` config?
3. With `maxUnavailable=1`, how many workers reboot at once — and why is that the
   default?
4. Give two reasons to pause a pool.

---

> **◐ Partially verified:** every command **requires a live OpenShift cluster** (Steps
> 3–6 need cluster-admin) and was **not** runnable in the authoring environment. Output
> is **representative of OpenShift 4.18**; the MachineConfig YAML follows the Ignition
> 3.4.0 schema but the CA blob is a placeholder — supply your own and run live. Nothing
> is presented as independently verified.

> **Gating validated (2026-07-05, as learner25):** the cluster-scope actions in this demo
> returned `Error from server (Forbidden)` for the normal user **learner25** — confirming
> it is correctly **cluster-admin / instructor-led**, as marked. Reproduce the live output
> with an admin/cluster-reader login.
