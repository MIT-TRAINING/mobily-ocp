# Module 1 — Guided Demos (Instructor-Led)

These are **instructor-led, narrated walkthroughs**. The instructor runs each step
live on screen while explaining *what* is happening and *why* it matters.
Participants watch and follow along; they practice independently in the
[`../exercises`](../exercises) afterwards.

All scenarios use a **telecom domain** framing (subscribers, CDRs, tariff
catalogs, self-care portals) so the concepts land in a context the audience
recognizes. The data and services are fictional and illustrative.

## Demos in this module

| # | Demo | Concepts reinforced | Telecom scenario | Time |
|---|------|---------------------|------------------|------|
| 1 | [Run & manage containers](demo-01-run-and-manage-containers.md) | Container lifecycle, logs, exec, inspect | Run a **Subscriber Lookup API** | ~20 min |
| 2 | [Build an image & explore layers](demo-02-build-image-and-layers.md) | Images, layers, build cache, OCI | Build a **Tariff Catalog API** | ~25 min |
| 3 | [Registry: tag, push, pull](demo-03-registry-push-pull.md) | Registries, tags vs digests, distribution | Ship the **Tariff Catalog** image | ~20 min |
| 4 | [Networking & persistent storage](demo-04-networking-and-storage.md) | Ports, container networks, volumes, ephemerality | **CDR ingest** API + database | ~30 min |
| 5 | [Podman pods & rootless](demo-05-podman-pods-and-rootless.md) | Docker vs Podman, daemonless, rootless, pods | **Self-care portal** pod | ~20 min |

## Conventions

- Commands use **`podman`** because it matches the OpenShift toolchain (CRI-O,
  Buildah, native pods) the course builds toward. Docker is interchangeable for
  almost everything here — `alias docker=podman` makes the commands identical.
  Each demo opens with a **🐳 Docker equivalents** callout spelling out exactly
  what (if anything) differs for Docker users. Demo 5 is intentionally
  Podman-only (Docker has no pods / `generate kube`).
- Base images are pulled from public registries (`registry.access.redhat.com`,
  `docker.io`). The first pull needs internet; subsequent runs use the local
  cache.
- Each demo ends with a **Cleanup** section — run it so the next demo starts
  from a clean state.
- Companion material: the interactive visualizations in [`../`](../index.html)
  and the concept guide in [`../../../guides/module-01-container-fundamentals.md`](../../../guides/module-01-container-fundamentals.md).

## Pre-flight check (run once before Demo 1)

```bash
podman --version          # confirm Podman (or docker --version)
podman info | head -20    # confirm the engine is healthy
podman pull registry.access.redhat.com/ubi9/ubi:latest   # warm the cache
```

> **Instructor tip:** pre-pull every base image used in the demos *before* class.
> Pulling large images live over shared conference Wi-Fi kills the pace.
