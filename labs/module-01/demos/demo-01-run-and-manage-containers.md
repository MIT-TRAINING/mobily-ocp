# Demo 1 — Run & Manage Containers

> **Scenario:** The operator's support team needs a small **Subscriber Lookup
> API** running so agents can resolve an MSISDN to an account. We'll run it as a
> container and manage its full lifecycle — exactly the day-to-day moves an
> operator performs on any containerized service.

| | |
|---|---|
| **Concepts reinforced** | Container = running instance of an image · lifecycle (create → run → stop → rm) · logs, exec, inspect |
| **Maps to** | Visualization 04 (Lifecycle), Visualization 01 (VM vs Container) |
| **Time** | ~20 minutes |
| **Tools** | `podman` (or `docker`) |

---

> **🐳 Docker equivalents:** Every command in this demo is identical under Docker
> — just swap `podman` for `docker` (or `alias docker=podman`). `docker
> run / ps / exec / logs / stats / stop / start / pause / unpause / rm` all behave
> the same here.

## Talking points to open with

- A **container is just a running process** wrapped in isolation — nothing more.
- One **image** can produce **many containers** (we'll prove it).
- Everything we do here (`run`, `ps`, `logs`, `exec`, `stop`, `rm`) maps directly
  to how you'll manage pods later in OpenShift.

---

## Step 1 — Run the Subscriber Lookup API

We'll use a stock NGINX image to stand in for the API endpoint, then make it
"telecom" by serving a subscriber record.

```bash
podman run -d --name subscriber-api -p 8080:8080 \
  registry.access.redhat.com/ubi9/nginx-120:latest \
  nginx -g "daemon off;"
```

**Expected output** (a long container ID):

```
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
```

> **Narrate:** `-d` = detached (runs in the background); `--name` gives it a
> friendly handle; `-p 8080:8080` publishes the container's port to host port
> 8080. The image was pulled once and is now cached.
>
> **Why port 8080, not 80?** Red Hat **UBI / sclorg** images are built to run as
> a **non-root, arbitrary-UID** user — exactly how OpenShift runs pods. A non-root
> process can't bind privileged ports (<1024), so this NGINX is configured to
> listen on **8080**, not 80. Map host→container as `8080:8080`. (This is a
> preview of the OpenShift security model you'll meet in the RBAC/security
> modules — and why mapping to container port 80 here would just connection-refuse.)

Verify it's running:

```bash
podman ps
```

```
CONTAINER ID  IMAGE                    ...  STATUS         PORTS                   NAMES
e3b0c4429...  .../nginx-120:latest     ...  Up 5 seconds   0.0.0.0:8080->8080/tcp  subscriber-api
```

---

## Step 2 — One image, many containers

Prove the image→container relationship by launching two more instances on
different ports (think: scaling the lookup service):

```bash
podman run -d --name subscriber-api-2 -p 8081:8080 registry.access.redhat.com/ubi9/nginx-120:latest nginx -g "daemon off;"
podman run -d --name subscriber-api-3 -p 8082:8080 registry.access.redhat.com/ubi9/nginx-120:latest nginx -g "daemon off;"
podman ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

```
NAMES              STATUS         PORTS
subscriber-api     Up 2 minutes   0.0.0.0:8080->8080/tcp
subscriber-api-2   Up 8 seconds   0.0.0.0:8081->8080/tcp
subscriber-api-3   Up 5 seconds   0.0.0.0:8082->8080/tcp
```

> **Narrate:** Three independent containers, **one shared image** on disk. This
> is the density advantage from Visualization 01 — only a thin writable layer per
> container.

---

## Step 3 — Inject a telecom payload with `exec`

Write a fake subscriber record into the first container and serve it:

```bash
podman exec subscriber-api bash -c \
  'echo "{\"msisdn\":\"966500000001\",\"plan\":\"Postpaid Pro 200\",\"status\":\"ACTIVE\"}" > /opt/app-root/src/subscriber.json'

curl -s http://localhost:8080/subscriber.json
```

```json
{"msisdn":"966500000001","plan":"Postpaid Pro 200","status":"ACTIVE"}
```

> **Narrate:** `exec` runs a command *inside* a running container — invaluable for
> troubleshooting. But note: this change lives only in the **writable layer**. If
> we remove the container, it's gone (the ephemeral lesson — Demo 4 fixes it with
> volumes).

---

## Step 4 — Observe: logs, stats, inspect

```bash
podman logs --tail 5 subscriber-api          # request logs
podman stats --no-stream subscriber-api      # live CPU / memory (cgroups!)
podman inspect subscriber-api --format '{{.State.Status}} | {{.NetworkSettings.IPAddress}}'
```

> **Narrate:** `stats` is **cgroups** in action (Visualization 02). `inspect`
> dumps the full container config as JSON — state, network, mounts, env.

---

## Step 5 — Walk the lifecycle

Drive the container through the state machine from Visualization 04:

```bash
podman stop subscriber-api-3      # running  -> stopped
podman ps -a --format "table {{.Names}}\t{{.Status}}"   # see "Exited"
podman start subscriber-api-3     # stopped  -> running again (data intact)
podman pause subscriber-api-2     # running  -> paused
podman unpause subscriber-api-2   # paused   -> running
```

```
NAMES              STATUS
subscriber-api     Up 6 minutes
subscriber-api-2   Up 6 minutes (paused)
subscriber-api-3   Exited (0) 4 seconds ago
```

> **Narrate:** A **stopped** container keeps its writable layer — you can restart
> it. Only `rm` destroys it. This is the exact lifecycle you clicked through in
> the visualization.

---

## Step 6 — Cleanup

```bash
podman rm -f subscriber-api subscriber-api-2 subscriber-api-3
podman ps -a        # confirm all gone
```

> **Narrate:** `rm -f` force-removes (stops first if needed). The writable layers
> — including our injected `subscriber.json` — are now **permanently destroyed**.
> That's the cue for Demo 4: persistent storage.

---

## Wrap-up questions to pose

1. We ran three containers from one image — what was shared and what was unique?
2. Where did the `subscriber.json` we wrote actually live, and why is it gone now?
3. Which command would you use to debug a misbehaving container *without*
   stopping it?
