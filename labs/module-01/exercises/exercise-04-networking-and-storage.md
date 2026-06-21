# Exercise 4 — Container Networking & Persistent Storage

> **Scenario:** A **Usage Metering API** records data usage per subscriber and
> keeps a running counter in a **Redis** cache. You'll wire two containers
> together on a private network and make the cache data **survive** a container
> rebuild.

| | |
|---|---|
| **Practice** | `network create`, DNS by name, port publishing, `volume`, ephemerality |
| **Maps to** | Visualization 03 (storage), Demo 4 |
| **Difficulty** | ⭐⭐⭐ Advanced · ~30 min |

---

## Tasks

### Part A — Networking
1. Create a user-defined network named `metering-net`.
2. Start a **Redis** cache named `usage-cache` on that network (no published
   port — it must be reachable only *inside* the network).
   > Image: `registry.redhat.io/rhel9/redis-6:latest` or
   > `docker.io/library/redis:7` (use whichever you can pull).
3. From a temporary `ubi9` container on the same network, **resolve
   `usage-cache` by name** and confirm connectivity to its port (6379).

### Part B — Prove ephemerality, then fix it
4. Set a usage counter in the cache, e.g. for MSISDN `966500000003`, value
   `2048` (MB used today). Then **destroy and recreate** the Redis container
   **without** a volume and show the counter is **gone**.
5. Recreate the cache **with a named volume** mounted at Redis's data dir, set
   the counter again, then destroy + recreate the container with the **same
   volume** and show the counter **survived**.

> Note: to persist, Redis must write to disk. Either run it with
> `--appendonly yes` or issue a `SAVE` before destroying the container.

---

## Validation

```bash
# Part A — name resolves on the network
podman run --rm --network metering-net registry.access.redhat.com/ubi9/ubi:latest \
  getent hosts usage-cache
# -> <ip>   usage-cache

# Part B (after the volume-backed rebuild) — counter persists
podman exec usage-cache redis-cli GET usage:966500000003
# -> "2048"
```

---

## Stretch goals

- Publish a port for a throwaway web container on `metering-net` and confirm the
  cache still has **no** published port (defence in depth: expose the API, hide
  the datastore).
- Use `podman volume inspect usage-data` to find where the volume lives on the
  host.
- Explain how this maps to OpenShift **Services** (DNS) and **Persistent Volume
  Claims** (storage) in later modules.

---

## Reflection

- How did containers find each other without hard-coded IPs?
- Why did the counter survive the rebuild only when a volume was attached?
- Why is it good practice to *not* publish the datastore's port?

---

<details>
<summary><strong>✅ Solution</strong></summary>

```bash
# --- Part A ---
podman network create metering-net

podman run -d --name usage-cache --network metering-net \
  docker.io/library/redis:7 redis-server --appendonly yes

podman run --rm --network metering-net registry.access.redhat.com/ubi9/ubi:latest \
  getent hosts usage-cache          # name resolves via the network's DNS

# --- Part B: ephemeral (data lost) ---
podman exec usage-cache redis-cli SET usage:966500000003 2048
podman rm -f usage-cache
podman run -d --name usage-cache --network metering-net docker.io/library/redis:7
sleep 2
podman exec usage-cache redis-cli GET usage:966500000003   # -> (nil)  ← gone

# --- Part B: persistent (data survives) ---
podman rm -f usage-cache
podman volume create usage-data
podman run -d --name usage-cache --network metering-net \
  -v usage-data:/data docker.io/library/redis:7 redis-server --appendonly yes
podman exec usage-cache redis-cli SET usage:966500000003 2048
podman exec usage-cache redis-cli SAVE

podman rm -f usage-cache
podman run -d --name usage-cache --network metering-net \
  -v usage-data:/data docker.io/library/redis:7 redis-server --appendonly yes
sleep 2
podman exec usage-cache redis-cli GET usage:966500000003   # -> "2048" ← survived!

# cleanup
podman rm -f usage-cache
podman volume rm usage-data
podman network rm metering-net
```

**Key point:** On a user-defined network, containers resolve each other by
**name** (built-in DNS) — the seed of Kubernetes Services. The writable layer is
ephemeral; a **volume** has an independent lifecycle, so data survives container
replacement — the seed of OpenShift Persistent Volumes.
</details>
