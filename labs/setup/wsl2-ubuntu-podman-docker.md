# Local Containers on Windows — WSL2 + Ubuntu 24.04 (Podman / Docker)

> **Who needs this:** participants on **Windows laptops** who want to run the
> container labs locally. Containers are a Linux technology, so on Windows we run a
> real Linux (Ubuntu 24.04) inside **WSL2** and install the engine there. This
> course is **Podman-first** (it matches the OpenShift toolchain — CRI-O, Buildah,
> rootless), so install **Podman**; Docker is offered as an optional alternative.
>
> **On macOS or Linux already?** Skip this guide — install Podman natively
> (`brew install podman` / `sudo apt install podman`) and jump to Module 1.

Everything you install here mirrors the cloud lab VM (Ubuntu 24.04, rootless
Podman with `crun`, Red Hat **UBI** images on **port 8080**), so your local skills
transfer 1:1 to the shared cluster and to OpenShift later.

---

## 1. Prerequisites

| Requirement | Detail |
|-------------|--------|
| Windows version | Windows 11, or Windows 10 version 2004+ (build 19041+) |
| Virtualization | Enabled in BIOS/UEFI (Intel VT-x / AMD-V). Most corporate laptops have it on; if WSL fails to start, check here first. |
| Privileges | Local admin for the **one-time** `wsl --install` (and to enable virtualization). Day-to-day lab work needs no admin. |
| Disk / RAM | ≥ 10 GB free; 8 GB RAM (16 GB recommended, per the course requirements). |

> **Corporate machines:** if Windows features are locked down, you may need IT to
> enable the *Virtual Machine Platform* and *Windows Subsystem for Linux* features.

---

## 2. Install WSL2 + Ubuntu 24.04

Open **PowerShell as Administrator** (Start → type "PowerShell" → *Run as
administrator*) and run:

```powershell
wsl --install -d Ubuntu-24.04
```

This enables the WSL2 features, installs the kernel, and installs Ubuntu 24.04.
**Reboot if prompted.** On first launch Ubuntu asks you to create a **UNIX
username and password** (these are local to Ubuntu — not your Windows login).

Make sure everything is up to date and on **version 2**:

```powershell
wsl --update                 # update the WSL kernel
wsl --set-default-version 2  # default new distros to WSL2
wsl -l -v                    # verify
```

```
  NAME            STATE           VERSION
* Ubuntu-24.04    Running         2
```

> ⚠️ The **VERSION must be 2**. If it shows `1`, convert it:
> `wsl --set-version Ubuntu-24.04 2`. WSL1 cannot run containers properly.

Now open the **Ubuntu** terminal (Start → "Ubuntu 24.04") and update the OS:

```bash
sudo apt update && sudo apt -y upgrade
```

> **Tip:** from here on, run all Linux commands inside this **Ubuntu** shell. You
> can also open it from Windows Terminal (pick the Ubuntu profile) or VS Code via
> the **WSL** extension (`code .` inside Ubuntu opens VS Code attached to WSL).

---

## 3. Enable systemd (do this once)

Rootless Podman and the Docker daemon both behave best when **systemd** is
managing the session. Enable it in Ubuntu:

```bash
sudo tee /etc/wsl.conf >/dev/null <<'EOF'
[boot]
systemd=true
EOF
```

Then, back in **PowerShell**, fully restart WSL so the change takes effect:

```powershell
wsl --shutdown
```

Reopen the Ubuntu terminal and confirm systemd is running:

```bash
systemctl is-system-running     # "running" or "degraded" is fine
```

> **Why this matters:** without a login session, rootless Podman can fail with
> `RunRoot ... not writable` / `crun not found` because `XDG_RUNTIME_DIR`
> (`/run/user/1000`) isn't created. systemd creates it on boot — the same fix the
> lab VM applies. (See [Troubleshooting](#9-troubleshooting).)

---

## 4. Option A — Podman (recommended)

Install Podman and the **crun** low-level runtime (the course/VM standard):

```bash
sudo apt -y install podman crun
podman --version
```

Confirm it's running **rootless** (no daemon, no root — exactly how OpenShift runs
pods):

```bash
podman info --format '{{.Host.Security.Rootless}}'   # -> true
```

```
true
```

> Ubuntu 24.04 ships the `subuid`/`subgid` mappings rootless Podman needs already
> configured for your user, so there's nothing else to set up.

### Smoke test (identical to Module 1, Demo 1)

Run the fictional **Subscriber Lookup API** — same UBI image and **port 8080** as
the demos, so what you do here is exactly what you'll do in class:

```bash
podman run -d --name subscriber-api -p 8080:8080 \
  registry.access.redhat.com/ubi9/nginx-120:latest \
  nginx -g "daemon off;"

podman ps
curl -s http://localhost:8080/ | head -5      # served from inside the container
```

> **Why port 8080, not 80?** Red Hat **UBI / sclorg** images run as a non-root,
> arbitrary-UID user (just like OpenShift), and non-root processes can't bind
> ports below 1024 — so these images listen on **8080**. Always map `8080:8080`.

Clean up:

```bash
podman rm -f subscriber-api
```

✅ If `curl` returned HTML, your Podman setup is ready. **You can stop here** and go
to [Module 1](../../guides/module-01-container-fundamentals.md). Only
continue to Option B if you specifically need Docker.

---

## 5. Option B — Docker Engine inside WSL2 (optional alternative)

This installs the **Docker Engine directly inside Ubuntu** via Docker's official
apt repo. It does **not** use Docker Desktop, so there's no Docker Desktop license
to worry about. Pick **either** Podman **or** Docker — you don't need both.

```bash
# 1. Add Docker's official apt repository
sudo apt -y install ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null

# 2. Install the engine, CLI, and plugins
sudo apt update
sudo apt -y install docker-ce docker-ce-cli containerd.io \
  docker-buildx-plugin docker-compose-plugin
```

Start the daemon (systemd from Step 3 makes this work) and run Docker without
`sudo`:

```bash
sudo systemctl enable --now docker        # start now + on every boot
sudo usermod -aG docker $USER             # let your user talk to the daemon
newgrp docker                             # apply the group in this shell (or just re-open Ubuntu)
docker version
```

### Smoke test (same image and port)

```bash
docker run -d --name subscriber-api -p 8080:8080 \
  registry.access.redhat.com/ubi9/nginx-120:latest \
  nginx -g "daemon off;"
docker ps
curl -s http://localhost:8080/ | head -5
docker rm -f subscriber-api
```

> If `docker` commands say *"Cannot connect to the Docker daemon"*, the daemon
> isn't running — see [Troubleshooting](#9-troubleshooting).

---

## 6. Podman ↔ Docker: they're nearly identical

The course shows commands with `podman`. **Docker is interchangeable for almost
everything** — make the commands identical with an alias:

```bash
echo 'alias docker=podman' >> ~/.bashrc && source ~/.bashrc   # only if using Podman
```

| | Podman | Docker |
|---|--------|--------|
| Architecture | **Daemonless**, runs **rootless** by default | Root **daemon** (`dockerd`); rootless is opt-in |
| `run / ps / build / exec / logs / push / pull` | identical | identical |
| Pods / `podman generate kube` | ✅ supported | ❌ Podman-only |
| Best fit for this course | ✅ matches OpenShift (CRI-O, Buildah) | works fine for Modules 1–2 |

> You normally run **one** engine. If you installed both, note that only one can
> publish to host port 8080 at a time.

---

## 7. Working across Windows and Linux

- **Your Linux files** live in the Ubuntu filesystem (fast). Reach them from
  Windows Explorer at `\\wsl$\Ubuntu-24.04\home\<your-user>`.
- **Your Windows files** are mounted in Ubuntu under `/mnt/c/...`. Keep lab work
  *inside* the Linux home dir (`~`) — building images on `/mnt/c` is much slower.
- Clone the course repo inside Ubuntu, e.g. `~/OcpTraining`, and open it with
  `code .` (VS Code WSL extension).

---

## 8. Resource tuning (optional)

WSL2 grabs memory on demand. To cap it (useful on an 8 GB laptop), create
`C:\Users\<you>\.wslconfig` in **Windows** (not inside Ubuntu):

```ini
[wsl2]
memory=6GB
processors=4
```

Apply with `wsl --shutdown` (PowerShell), then reopen Ubuntu. Use the same
`wsl --shutdown` any time WSL gets into a bad state — it's a safe full reset.

---

## 9. Troubleshooting

| Symptom | Fix |
|---------|-----|
| `wsl -l -v` shows VERSION **1** | `wsl --set-version Ubuntu-24.04 2` (containers need WSL2). |
| WSL won't start / "Virtual Machine Platform" error | Enable virtualization in BIOS; ensure the *Virtual Machine Platform* + *WSL* Windows features are on (`wsl --install` enables them with admin rights). |
| Podman: `RunRoot ... not writable` or `OCI runtime crun not found` | Install crun (`sudo apt -y install crun`) **and** enable systemd (Step 3), then `wsl --shutdown` and reopen. |
| Podman rootless check returns `false` | You ran as root (`sudo`). Run `podman` as your normal user — rootless is the default and what we want. |
| Docker: `Cannot connect to the Docker daemon` | `sudo systemctl enable --now docker`. Confirm systemd is on (Step 3). |
| Docker needs `sudo` every time | `sudo usermod -aG docker $USER`, then re-open the Ubuntu terminal (or `newgrp docker`). |
| First image pull is very slow | The UBI base image downloads once, then it's cached. On corporate Wi-Fi, pull before class. Subsequent runs are instant. |
| `curl localhost:8080` refused | Container not running (`podman ps`), or you mapped the wrong port — UBI images listen on **8080**, so use `-p 8080:8080`. |

---

## 10. Next steps

- **Run the containers labs:**
  [Module 1 — Container Fundamentals](../../guides/module-01-container-fundamentals.md)
  and its [guided demos](../module-01/demos/README.md) (the smoke test above is the
  start of Demo 1).
- **Stand up a Kubernetes cluster** in this same Ubuntu (minikube uses the Docker
  driver inside WSL2): [minikube setup](minikube-kubernetes.md).
