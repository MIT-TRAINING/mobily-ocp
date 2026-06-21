# Module 1 — Cheatsheets

Quick-reference command sheets for the Module 1 labs, demos, and exercises. Keep
them open in a second window while you work.

| Cheatsheet | Use it for |
|------------|-----------|
| [Linux commands](linux-commands.md) | Navigating the shell, files, processes, networking, and the kernel features behind containers (namespaces, cgroups) |
| [Docker / Podman commands](docker-podman-commands.md) | Everything container: images, run/lifecycle, exec/logs, networks, volumes, registry, pods |

## Conventions

- Container commands are shown with **`podman`**. **`docker` is identical** unless
  a row says otherwise (`alias docker=podman` works). Pods and `generate kube`
  are **Podman-only**.
- `<placeholders>` mean "substitute your own value." Never paste real passwords
  into commands or commit credential files.
- Examples use the same telecom services as the [demos](../demos) and
  [exercises](../exercises) — subscriber APIs, CDRs, tariffs, etc.

Companion material: [interactive visualizations](../index.html) ·
[concept guide](../../../guides/module-01-container-fundamentals.md).
