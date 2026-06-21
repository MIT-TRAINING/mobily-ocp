# Docker / Podman Commands Cheatsheet — Module 1

Commands are shown with **`podman`**. **`docker` is identical** unless a row's
notes say otherwise (`alias docker=podman` works for everything in this module).
**Pods** and **`generate kube`** are **Podman-only**.

Examples reuse the telecom services from the [demos](../demos)/[exercises](../exercises).

---

## 1. Setup & info

| Command | What it does |
|---------|--------------|
| `podman --version` | Show version |
| `podman info` | Engine details (storage, network, rootless) |
| `podman info --format '{{.Host.Security.Rootless}}'` | Are we rootless? (`true`) |
| `podman login quay.io` | Authenticate to a registry |
| `podman logout quay.io` | Drop stored credentials |

> **Docker difference:** Docker runs a root **daemon** (`dockerd`); Podman is
> **daemonless** and can run **rootless**. There is no `dockerd` to check for in
> Podman.

---

## 2. Images

| Command | What it does |
|---------|--------------|
| `podman pull <image>` | Download an image |
| `podman images` | List local images |
| `podman build -t name:tag .` | Build from a Containerfile/Dockerfile |
| `podman tag src name:tag` | Add another name/tag (same image ID) |
| `podman history name:tag` | Show the image's **layers** |
| `podman inspect name:tag` | Full image metadata (JSON) |
| `podman rmi name:tag` | Remove an image |
| `podman image prune` | Remove dangling images |
| `podman save -o app.tar name:tag` | Export image to a tar archive |
| `podman load -i app.tar` | Import image from a tar archive |
| `podman search <term>` | Search registries |

> **Docker difference:** modern `docker build` uses **BuildKit** — cached steps
> show `CACHED` instead of `--> Using cache`. Use `DOCKER_BUILDKIT=0 docker build`
> for classic output.

**Telecom example:**
```bash
podman build -t tariff-catalog:1.0 .
podman history tariff-catalog:1.0
```

---

## 3. Registry: tag → push → pull

```bash
podman login quay.io
podman tag tariff-catalog:1.0 quay.io/<ns>/tariff-catalog:1.0
podman push quay.io/<ns>/tariff-catalog:1.0
podman pull quay.io/<ns>/tariff-catalog:1.0

# Immutable digest
podman inspect quay.io/<ns>/tariff-catalog:1.0 --format '{{index .RepoDigests 0}}'
podman pull quay.io/<ns>/tariff-catalog@sha256:<digest>
```

**Image reference anatomy:**
```
quay.io / <namespace> / tariff-catalog : 1.0
registry    namespace       repo        tag
```

> **Docker difference:** credentials live in `~/.docker/config.json` (Docker) vs
> `${XDG_RUNTIME_DIR}/containers/auth.json` (Podman). Never commit either.

---

## 4. Running containers — `podman run`

```bash
podman run -d --name subscriber-api -p 8080:80 <image>
```

| Flag | Meaning |
|------|---------|
| `-d` | Detached (background) |
| `--name X` | Friendly name |
| `-p 8080:80` | Publish host:container port |
| `-e KEY=val` | Set an environment variable |
| `-v vol:/path` | Mount a volume (persistent) |
| `--network NET` | Attach to a network |
| `--rm` | Auto-remove on exit |
| `-it` | Interactive + TTY (for shells) |
| `--memory 512m` | Memory limit (cgroups) |
| `--cpus 0.5` | CPU limit (cgroups) |
| `--restart on-failure` | Restart policy |
| `-w /dir` | Working directory inside container |
| `-u 1001` | Run as a specific UID |

**Interactive shell into a fresh container:**
```bash
podman run -it --rm registry.access.redhat.com/ubi9/ubi:latest bash
```

---

## 5. Container lifecycle

| Command | Transition |
|---------|-----------|
| `podman create --name X <image>` | → Created |
| `podman start X` | Created/Stopped → Running |
| `podman stop X` | Running → Stopped (graceful, SIGTERM) |
| `podman kill X` | Running → Stopped (force, SIGKILL) |
| `podman restart X` | Restart |
| `podman pause X` / `podman unpause X` | Running ⇄ Paused |
| `podman rm X` | Remove (writable layer destroyed) |
| `podman rm -f X` | Force-remove (stop first) |

> A **stopped** container keeps its writable layer (restartable). Only `rm`
> deletes it. See Visualization 04.

---

## 6. Inspect & debug

| Command | What it does |
|---------|--------------|
| `podman ps` | Running containers |
| `podman ps -a` | All (incl. stopped) |
| `podman logs X` | Container logs |
| `podman logs -f --tail 50 X` | Follow last 50 lines |
| `podman exec -it X bash` | Shell into a running container |
| `podman exec X <cmd>` | Run a command inside |
| `podman inspect X` | Full config/state (JSON) |
| `podman stats --no-stream X` | CPU/memory snapshot (cgroups) |
| `podman top X` | Processes inside the container |
| `podman port X` | Published port mappings |
| `podman cp X:/path ./local` | Copy files out of (or into) a container |
| `podman diff X` | Files changed vs the image |

**Useful `--format` (Go template) snippets:**
```bash
podman ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
podman inspect X --format '{{.State.Status}}'
podman inspect X --format '{{.NetworkSettings.IPAddress}}'
```

---

## 7. Networking

| Command | What it does |
|---------|--------------|
| `podman network create NET` | Create a user-defined network |
| `podman network ls` | List networks |
| `podman network inspect NET` | Network details |
| `podman network rm NET` | Remove a network |
| `podman network connect NET X` | Attach a running container to a network |

> On a **user-defined network**, containers resolve each other by **name** (DNS) —
> e.g. `cdr-api` reaches the database at `cdr-db:5432`. No published port is needed
> for in-network traffic; `-p` is only for host→container access.

**Telecom example:**
```bash
podman network create cdr-net
podman run -d --name cdr-db  --network cdr-net <postgres-image>
podman run -d --name cdr-api --network cdr-net -p 9090:8080 <api-image>
# cdr-api can now reach the DB at cdr-db:5432
```

---

## 8. Volumes & storage

| Command | What it does |
|---------|--------------|
| `podman volume create V` | Create a named volume |
| `podman volume ls` | List volumes |
| `podman volume inspect V` | Details (incl. host path) |
| `podman volume rm V` | Remove a volume |
| `podman run -v V:/data ...` | Mount a named volume |
| `podman run -v /host/dir:/data ...` | Bind-mount a host directory |
| `podman run --tmpfs /tmp ...` | In-memory scratch (vanishes on stop) |

> The container's **writable layer is ephemeral** — destroyed with the container.
> A **volume** has an independent lifecycle, so data survives a rebuild. This is
> the local precursor to OpenShift Persistent Volumes (Module 7).

---

## 9. Pods — **Podman only** 🟣

Docker has no native pod concept; these have **no Docker equivalent**.

| Command | What it does |
|---------|--------------|
| `podman pod create --name P -p 8088:8080` | Create a pod (shared network namespace) |
| `podman run -d --pod P --name c1 <image>` | Add a container to the pod |
| `podman pod ps` | List pods |
| `podman pod stop\|start\|rm P` | Control the whole pod |
| `podman generate kube P > pod.yaml` | Export pod as a **Kubernetes manifest** |
| `podman play kube pod.yaml` | Run containers from a Kubernetes YAML |

> Containers in a pod share `localhost` — the model you'll meet as Kubernetes pods
> in Module 2. `generate kube` is the bridge from Podman to OpenShift.

---

## 10. System & cleanup

| Command | What it does |
|---------|--------------|
| `podman ps -aq` | All container IDs (for scripting) |
| `podman rm -f $(podman ps -aq)` | Remove **all** containers (⚠️) |
| `podman image prune -a` | Remove all unused images |
| `podman volume prune` | Remove unused volumes |
| `podman system df` | Disk usage by images/containers/volumes |
| `podman system prune -a` | Reclaim everything unused (⚠️) |

---

## 11. Quick telecom recipes

```bash
# Run a subscriber API and hit its health endpoint
podman run -d --name sub-api -p 8080:8080 <image>
curl -s http://localhost:8080/health

# Build, tag and ship the tariff catalog
podman build -t tariff:1.0 . \
  && podman tag tariff:1.0 quay.io/<ns>/tariff:1.0 \
  && podman push quay.io/<ns>/tariff:1.0

# CDR DB with persistent storage
podman volume create cdr-data
podman run -d --name cdr-db -v cdr-data:/var/lib/pgsql/data <postgres-image>

# Tail a running gateway's logs
podman logs -f --tail 100 sms-gateway

# Nuke the lab environment between exercises
podman rm -f $(podman ps -aq) 2>/dev/null; podman volume prune -f
```

---

## 12. Docker ↔ Podman quick map

| Task | Podman | Docker | Same? |
|------|--------|--------|-------|
| Run / ps / logs / exec / stop / rm | `podman ...` | `docker ...` | ✅ identical |
| Build | `podman build` | `docker build` | ✅ (BuildKit output differs) |
| Images / tag / push / pull | `podman ...` | `docker ...` | ✅ (creds file location differs) |
| Networks / volumes | `podman network\|volume` | `docker network\|volume` | ✅ identical |
| Rootless by default | yes | no (daemon as root) | ❌ different model |
| Pods | `podman pod ...` | — | ❌ Podman-only |
| Export to Kubernetes YAML | `podman generate kube` | — | ❌ Podman-only |
