# Demo 3 — Registry: Tag, Push, Pull

> **Scenario:** The **Tariff Catalog API** image from Demo 2 lives only on the
> instructor's laptop. To run it on any other host or on OpenShift, it must be
> **shipped to a registry**. We'll tag it, push it, and pull it back as if onto a
> different node.

| | |
|---|---|
| **Concepts reinforced** | Registries · image references (registry/repo:tag) · tags vs digests · push/pull distribution |
| **Maps to** | Visualization 05 (Build → Ship → Run) |
| **Time** | ~20 minutes |
| **Tools** | `podman` (or `docker`) · a registry account (Quay.io or Docker Hub) |
| **Prereq** | The `~/tariff-catalog` build context from Demo 2 |

---

> **🐳 Docker equivalents:** `docker login / tag / push / pull` are identical.
> The main difference is **where credentials are stored** — Docker uses
> `~/.docker/config.json`, Podman uses `${XDG_RUNTIME_DIR}/containers/auth.json`.
> Either way, never commit that file. `docker inspect --format '{{index
> .RepoDigests 0}}'` returns the digest the same way.

## Step 0 — Anatomy of an image reference

Put this on screen and dissect it before touching the CLI:

```
quay.io/<your-namespace>/tariff-catalog:1.1
└──┬──┘ └─────┬──────┘ └─────┬──────┘ └┬┘
registry   namespace        repo       tag
```

> **Narrate:** A bare name like `tariff-catalog` defaults to `docker.io/library`.
> For your own images you always specify **registry/namespace/repo:tag**.

---

## Step 1 — Log in to the registry

Using Quay.io (Red Hat's registry; Docker Hub works identically):

```bash
podman login quay.io
# Username: <your-quay-user>
# Password: <your-quay-password-or-token>
```

```
Login Succeeded!
```

> **Security note:** prefer a **robot account / token** over your real password.
> Credentials are stored in `${XDG_RUNTIME_DIR}/containers/auth.json` — never
> commit that file.

---

## Step 2 — (Re)build and tag for the registry

If the image from Demo 2 is gone, rebuild it, then tag it with the full registry
path. Replace `<your-namespace>` with **your own** Quay.io namespace.

```bash
cd ~/tariff-catalog
podman build -t tariff-catalog:1.1 .

# Tag the local image with the remote reference
podman tag tariff-catalog:1.1 quay.io/<your-namespace>/tariff-catalog:1.1
podman images | grep tariff
```

> **Narrate:** `tag` doesn't copy anything — both names point at the **same image
> ID**. A tag is just a label.

---

## Step 3 — Push to the registry

```bash
podman push quay.io/<your-namespace>/tariff-catalog:1.1
```

**Expected output** — note layers upload individually (and shared layers are
skipped if already present):

```
Copying blob sha256:a1b2c3...  done
Copying blob sha256:d4e5f6...  done
Copying config sha256:9f86d0... done
Writing manifest to image destination
```

> **Narrate:** Only the layers the registry doesn't already have are uploaded —
> the de-duplication you saw in Visualization 05.

---

## Step 4 — Note the digest (immutable identity)

```bash
podman inspect quay.io/<your-namespace>/tariff-catalog:1.1 \
  --format '{{index .RepoDigests 0}}'
```

```
quay.io/<your-namespace>/tariff-catalog@sha256:9f86d081884c7d659a2feaa0c55ad015...
```

> **Narrate:** The **tag** `1.1` is mutable — we could overwrite it tomorrow. The
> **digest** `@sha256:...` is the content hash; it *always* refers to these exact
> bytes. Production deployments pin to digests for reproducibility.

---

## Step 5 — Simulate pulling onto "another host"

Remove the local copies so the next pull must come from the registry — this
mimics a fresh OpenShift node:

```bash
podman rmi quay.io/<your-namespace>/tariff-catalog:1.1 tariff-catalog:1.1
podman pull quay.io/<your-namespace>/tariff-catalog:1.1
podman run -d --name tariff -p 8080:8080 quay.io/<your-namespace>/tariff-catalog:1.1
curl -s http://localhost:8080/health
```

```
{"status":"ok"}
```

> **Narrate:** Built once, shipped, pulled, and running again — **the same
> artifact**. This is precisely how an image moves from a developer's laptop to a
> production OpenShift cluster.

---

## Step 6 — (Optional) Pull by digest

Show that the immutable reference works too:

```bash
podman pull quay.io/mobily-academy/tariff-catalog@sha256:9f86d0...   # paste full digest
```

---

## Step 7 — Cleanup

```bash
podman rm -f tariff
podman rmi quay.io/<your-namespace>/tariff-catalog:1.1 2>/dev/null
podman logout quay.io
```

---

## Wrap-up questions to pose

1. What are the four parts of `quay.io/<your-namespace>/tariff-catalog:1.1`?
2. Why would you deploy production workloads by **digest** instead of `:latest`?
3. During the push, why were some layers skipped?
