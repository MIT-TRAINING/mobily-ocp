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

> **Narrate:** A **pod** is a group of containers sharing one network namespace —
> they reach each other on `localhost`. The port is published **on the pod**, not
> the individual container. This is *exactly* the Kubernetes pod model you'll meet
> in Module 2; Podman lets you rehearse it locally.

---

## Step 3 — Add the API container to the pod

```bash
podman run -d --pod selfcare --name selfcare-api \
  registry.access.redhat.com/ubi9/httpd-24:latest httpd -DFOREGROUND

# seed a fake account-balance endpoint
podman exec selfcare-api bash -c \
  'echo "{\"msisdn\":\"966500000001\",\"balance_sar\":37.50,\"plan\":\"POST-PRO-200\"}" > /var/www/html/balance.json'
```

---

## Step 4 — Add the web front end to the same pod

```bash
podman run -d --pod selfcare --name selfcare-web \
  registry.access.redhat.com/ubi9/nginx-120:latest nginx -g "daemon off;"

podman pod ps
podman ps --pod --format "table {{.Names}}\t{{.Pod}}\t{{.Status}}"
```

```
NAMES           POD       STATUS
selfcare-api    selfcare  Up
selfcare-web    selfcare  Up
```

> **Narrate:** Two containers, one pod. Because they share the network namespace,
> `selfcare-web` can call the API at **`localhost`** — no separate network needed.
> Notice there's also an `infra` container holding the namespace — that's how pods
> work under the hood.

---

## Step 5 — Hit the portal

```bash
curl -s http://localhost:8088/balance.json
```

```json
{"msisdn":"966500000001","balance_sar":37.50,"plan":"POST-PRO-200"}
```

---

## Step 6 — Generate Kubernetes YAML (the OpenShift bridge)

This is the "wow" moment that links Module 1 to the rest of the course:

```bash
podman generate kube selfcare > selfcare-pod.yaml
head -20 selfcare-pod.yaml
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
2. How did `selfcare-web` and `selfcare-api` communicate inside the pod?
3. Why is `podman generate kube` a useful stepping stone toward OpenShift?
