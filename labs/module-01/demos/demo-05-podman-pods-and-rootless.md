# Demo 5 — Podman Pods & Rootless Containers

> **Scenario:** The customer **Self-Care Portal** is a web front end plus a small
> API. We'll group them into a single **pod** (shared network) the way Kubernetes
> does — and run the whole thing **rootless**, the Red Hat / OpenShift security
> model. This demo makes the Docker-vs-Podman differences concrete.

| | |
|---|---|
| **Concepts reinforced** | Docker vs Podman · daemonless · rootless · the pod concept (preview of Module 2) |
| **Maps to** | Module 1 "Docker and Podman overview", bridges to Visualization/Module 2 |
| **Time** | ~20 minutes |
| **Tools** | `podman` (rootless capable) |

---

> **🐳 Docker equivalents — note:** This demo is **intentionally Podman-specific.**
> Docker has **no native pod concept** and **no `generate kube`**. The closest
> Docker analogue is running containers on a shared network (or a `docker compose`
> project), but those containers don't share a single network namespace the way
> pod containers do, and you can't export them as a Kubernetes manifest. The
> daemonless/rootless contrast in Step 1 is precisely *why* OpenShift uses this
> model instead of the Docker daemon — so here we stay on Podman on purpose.

## Step 1 — Daemonless & rootless: show, don't tell

```bash
# Who runs the containers? (Docker would show a root-owned dockerd here)
podman info --format '{{.Host.Security.Rootless}}'      # -> true (when rootless)
id -u                                                   # your normal user, not 0
ps -ef | grep -i dockerd | grep -v grep || echo "No Docker daemon running"
```

> **Narrate:** With Docker, a single privileged **`dockerd`** daemon (running as
> root) is the parent of every container — a single point of failure and a big
> attack surface. Podman is **daemonless**: each container is a child of your
> shell, and can run **rootless** (as your unprivileged user). For a telecom
> running multi-tenant platforms, that's a major security win.

| | Docker | Podman |
|---|--------|--------|
| Architecture | Client + central daemon | Daemonless (fork/exec) |
| Runs as root? | Daemon needs root | Supports **rootless** |
| Single point of failure | Yes (the daemon) | No |
| Native pods | No | **Yes** |

---

## Step 2 — Create a pod for the Self-Care Portal

```bash
podman pod create --name selfcare -p 8088:8080
podman pod ps
```

```
POD ID        NAME      STATUS    CREATED        INFRA ID      # OF CONTAINERS
ca52a5760201  selfcare  Created   3 seconds ago  347f96de1537  1
```

> **Narrate:** A **pod** is a group of containers sharing one network namespace —
> they reach each other on `localhost`. The port is published **on the pod**, not
> the individual container. The `# OF CONTAINERS` is already **1**: that's the
> `infra` container holding the namespace open. This is *exactly* the Kubernetes
> pod model you'll meet in Module 2; Podman lets you rehearse it locally.

---

## Step 3 — Add the API container to the pod

We use the **`httpd-24` image's default command** — do **not** override it with
`httpd -DFOREGROUND`:

```bash
podman run -d --pod selfcare --name selfcare-api \
  registry.access.redhat.com/ubi9/httpd-24:latest

# seed a fake account-balance endpoint
podman exec selfcare-api bash -c \
  'echo "{\"msisdn\":\"966500000001\",\"balance_sar\":37.50,\"plan\":\"POST-PRO-200\"}" > /var/www/html/balance.json'
```

> **Why no `httpd -DFOREGROUND`?** The `ubi9/httpd-24` image ships with `mod_ssl`
> enabled, and its real entrypoint (`/usr/bin/run-httpd`) **generates the
> self-signed TLS cert** before starting Apache. If you override the command with
> a bare `httpd -DFOREGROUND`, you skip that setup and Apache dies with
> `AH00526: SSLCertificateFile: file '/etc/httpd/tls/localhost.crt' does not exist`.
> Let the image run its default command — it serves plain HTTP on **8080** *and*
> sets up TLS correctly. (This is a recurring gotcha with sclorg images: prefer
> the image's own run script over hand-rolled commands.)

---

## Step 4 — Prove the shared network namespace with a sidecar

A pod's containers share **one** network namespace, so they reach each other on
`localhost`. Demonstrate it with a throwaway **sidecar** in the *same* pod that
calls the API over `localhost` — exactly how a real sidecar (log shipper, proxy,
metrics agent) talks to the app container:

```bash
podman run --rm --pod selfcare \
  registry.access.redhat.com/ubi9/ubi:latest \
  curl -s http://localhost:8080/balance.json
```

```json
{"msisdn":"966500000001","balance_sar":37.50,"plan":"POST-PRO-200"}
```

```bash
podman pod ps
podman ps --pod --format "table {{.Names}}\t{{.Pod}}\t{{.Status}}"
```

```
NAMES               POD ID        STATUS
ca52a5760201-infra  ca52a5760201  Up 30 seconds
selfcare-api        ca52a5760201  Up 28 seconds
```

> **Narrate:** The sidecar reached `localhost:8080` and got the API's response —
> proof that pod containers share a network namespace (the `infra` container holds
> it). The `--rm` sidecar exits after the call, so only `selfcare-api` and `infra`
> remain. A real sidecar would stay running alongside the app.

> **⚠️ Why not a second web server (e.g. nginx) in this pod?** Because containers
> in a pod **share the same network namespace, they cannot both bind the same
> port.** Both `ubi9/httpd-24` and `ubi9/nginx-120` default to **8080**, so adding
> nginx to this pod makes the second container fail to bind 8080 —
> `address already in use`. Co-located pod containers must each listen on a
> **different** port (that's why real app+sidecar pairs use distinct ports). This
> is the same constraint Kubernetes enforces on pod containers.

---

## Step 5 — Hit the portal from the host

```bash
curl -s http://localhost:8088/balance.json
```

```json
{"msisdn":"966500000001","balance_sar":37.50,"plan":"POST-PRO-200"}
```

> **Narrate:** Host port **8088** was published on the *pod* (Step 2) and maps to
> container port 8080 — the same `-p` model you saw on single containers, now at
> the pod level.

---

## Step 6 — Generate Kubernetes YAML (the OpenShift bridge)

This is the "wow" moment that links Module 1 to the rest of the course:

```bash
podman kube generate selfcare > selfcare-pod.yaml   # older alias: podman generate kube
head -22 selfcare-pod.yaml
```

```yaml
# Save the output of this file and use kubectl create -f to import
# it into Kubernetes.
apiVersion: v1
kind: Pod
metadata:
  labels:
    app: selfcare
  name: selfcare
spec:
  containers:
  - args:
    - /usr/bin/run-httpd
    image: registry.access.redhat.com/ubi9/httpd-24:latest
    name: selfcare-api
    ports:
    - containerPort: 8080
      hostPort: 8088
    securityContext:
      runAsNonRoot: true
```

> **Narrate:** Podman just turned our running pod into a **Kubernetes manifest** —
> the same kind of YAML we'll apply to OpenShift in Modules 3–9. The mental model
> you build with Podman pods transfers directly to the platform.

---

## Step 7 — Cleanup

```bash
podman pod rm -f selfcare
rm -f selfcare-pod.yaml
```

---

## Wrap-up questions to pose

1. Name two security advantages of Podman's daemonless/rootless model for a
   telecom platform.
2. How did the sidecar reach `selfcare-api` inside the pod, and why couldn't a
   second container also bind port 8080?
3. Why is `podman kube generate` a useful stepping stone toward OpenShift?

---

> **✅ Verified:** podman 5.8.2 · 2026-06-25 · images `ubi9/httpd-24:latest`,
> `ubi9/ubi:latest`. Every command and output above is from a real run.
