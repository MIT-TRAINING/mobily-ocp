# Assignment 1 — Containerize the Self-Care API

> **Module 1 · Container Fundamentals & Runtime Refresher**
> **Telecom scenario:** Mobily's *Self-Care* team has a tiny subscriber-lookup
> service (`selfcare-api`). Today it only runs on a developer's laptop. Your job
> is to **package it as a portable container image**, run it reliably, prove its
> configuration is externalized, and **publish it to a registry** so the rest of
> the course (Modules 2–3) can pull the exact same artifact onto Kubernetes.

| | |
|---|---|
| **Maps to** | Images, registries & container lifecycle · networking & storage |
| **Tools** | `podman` (Docker works identically: `alias docker=podman`) |
| **Provided** | [`app/`](./app) — `server.py`, `data/`, `Containerfile` |
| **Difficulty** | ⭐⭐ Intermediate · ~60–75 min |
| **Weight** | 20 % of the Modules 1–3 assessment |

---

## Learning objectives

By the end you can:

1. Read a `Containerfile` and explain each instruction's effect on the image layers.
2. Build, tag, run, inspect, and tear down a container through its full lifecycle.
3. Externalize configuration with environment variables (12-factor).
4. Persist and mount data with a **volume**, and reason about the writable layer.
5. Tag with a registry path, log in, **push**, and **pull by digest**.

## Prerequisites

```bash
podman --version           # 5.x expected
podman info | head         # engine healthy?
cd assessments/app         # the provided app lives here
```

A free **Docker Hub** (or Quay.io) account. Never commit credentials — when you
log in, podman stores them in `${XDG_RUNTIME_DIR}/containers/auth.json`, which is
git-ignored. Use placeholders like `<your-registry-user>` in anything you submit.

---

## The app (what you are packaging)

`selfcare-api` is dependency-free Python (stdlib only). It serves:

| Endpoint | Purpose |
|---|---|
| `GET /healthz` | probe target → `{"status":"ok"}` |
| `GET /version` | image/runtime info (version, region, pod, dataset counts) |
| `GET /subscribers/<msisdn>` | one subscriber profile + tariff |
| `GET /tariffs` | tariff catalog |

It is configured **entirely through environment variables** —
`SELFCARE_PORT`, `SELFCARE_REGION`, `SELFCARE_BANNER`, `SELFCARE_API_KEY`,
`SELFCARE_DATA_DIR`. Read [`app/server.py`](./app/server.py) and
[`app/Containerfile`](./app/Containerfile) before you start.

---

## Tasks

### Part A — Build & inspect (5 pts)
1. **Build** the image and tag it `selfcare-api:1.0.0`.
2. List your images and record the **size** and **image ID**.
3. Inspect the image's **history** (layers). Which instruction created the
   largest layer? Which layers are shared with the UBI base?
4. Inspect the image's **labels** and confirm the `EXPOSE`d port and default `CMD`.

### Part B — Run & manage the lifecycle (6 pts)
5. **Run** it detached as `selfcare`, publishing host **8080** → container **8080**,
   and set `SELFCARE_REGION=riyadh-dc1`.
6. Confirm it's healthy: `curl` `/healthz` and `/version`. The `/version`
   response must show `"region":"riyadh-dc1"` and a `"pod"` equal to the
   container's short ID — **prove config came from your `-e` flag**, not the image.
7. Look up subscriber **966500000004** over HTTP. What is their `status`?
8. Read the container's **logs** (you should see your access-log lines).
9. Drive the lifecycle: `stop` → confirm `Exited` → `start` → confirm it still serves.
10. Inspect one-shot **CPU/memory** usage.

### Part C — Configuration & persistence (5 pts)
11. The dataset is **baked into the image** at `/app/data`. Run a **second**
    container `selfcare-edge` on port **8081** that instead reads its data from a
    **host directory you control**, mounted over `/app/data`, seeded with your own
    copy of `subscribers.json` + `tariffs.json`. Add one extra subscriber to your
    host copy and prove the running container serves it **without a rebuild**.
12. Explain (in writing) the difference between the data baked into the image and
    the data served from your mounted volume — and what `podman rm` destroys in
    each case.

### Part D — Publish to a registry (4 pts)
13. **Re-tag** the image for your registry namespace, e.g.
    `docker.io/<your-registry-user>/selfcare-api:1.0.0`.
14. **Log in** and **push** it.
15. Remove the local image, then **pull it back by digest**
    (`...@sha256:...`) and run it to prove the published artifact is intact.

---

## Deliverables

Submit a single Markdown file `submission-01.md` containing:

- The exact commands you ran for each part (credentials redacted to placeholders).
- Pasted output of: `podman images selfcare-api`, the `/version` JSON from Task 6,
  the subscriber-4 lookup, and the `podman push` digest line.
- Your written answers to Tasks 7, 12, and the two "which layer" questions in Part A.

---

## Validation (self-check before submitting)

```bash
# B6 — config really came from the environment, not the image default:
curl -s localhost:8080/version | grep -q '"region": "riyadh-dc1"' && echo "PASS region"

# B7 — suspended subscriber:
curl -s localhost:8080/subscribers/966500000004 | grep -q '"status": "SUSPENDED"' && echo "PASS lookup"

# C11 — mounted volume overrides the baked-in data (your extra subscriber shows up):
curl -s localhost:8081/subscribers/966599999999 | grep -q '"msisdn"' && echo "PASS volume override"

# D — pulled-by-digest image runs:
curl -s localhost:8082/healthz | grep -q '"status": "ok"' && echo "PASS digest pull"
```

---

## Grading rubric (20 pts)

| Criteria | Pts |
|---|---|
| Image builds, correctly tagged, layers/labels explained | 5 |
| Full lifecycle demonstrated (run/logs/stop/start/stats) | 4 |
| Config proven to come from env (`region`/`pod` in `/version`) | 2 |
| Volume override works without rebuild + correct written explanation | 5 |
| Registry push **and** pull-by-digest succeed | 4 |
| **Total** | **20** |

> Deductions: hard-coding config into the image instead of using env (−2);
> committing any real credential/`auth.json` (−5, automatic).

---

## Stretch goals (not graded)

- Rebuild with `podman build --format docker` and show the `HEALTHCHECK` status in
  `podman ps` flip to `healthy`. Why does the **default** podman build ignore it?
- Run the image with `--read-only` plus a writable `tmpfs` and confirm it still
  serves (proof it needs no writable root — important for OpenShift's restricted SCC).
- Use `podman generate kube selfcare > pod.yaml`. Keep that file — you'll compare
  it to a hand-written Pod in Assignment 2.

---

<details>
<summary><strong>✅ Reference solution</strong> (attempt the tasks first)</summary>

```bash
cd assessments/app

# A — build & inspect
podman build -t selfcare-api:1.0.0 .
podman images selfcare-api
podman history selfcare-api:1.0.0          # COPY data/ + the base python layer dominate
podman inspect selfcare-api:1.0.0 --format '{{.Config.ExposedPorts}} {{.Config.Cmd}} {{json .Config.Labels}}'

# B — run & manage
podman run -d --name selfcare -p 8080:8080 -e SELFCARE_REGION=riyadh-dc1 selfcare-api:1.0.0
curl -s localhost:8080/healthz
curl -s localhost:8080/version                      # region=riyadh-dc1, pod=<short id>
curl -s localhost:8080/subscribers/966500000004     # status: SUSPENDED
podman logs selfcare
podman stop selfcare && podman ps -a --format '{{.Names}} {{.Status}}'
podman start selfcare && curl -s localhost:8080/healthz
podman stats --no-stream selfcare

# C — volume override (data from a host dir, no rebuild)
mkdir -p /tmp/edge-data
cp data/subscribers.json data/tariffs.json /tmp/edge-data/
# add an extra subscriber to the HOST copy (edit the file or use python):
python3 - <<'PY'
import json
p="/tmp/edge-data/subscribers.json"; d=json.load(open(p))
d.append({"msisdn":"966599999999","name":"Edge Test","plan":"POST-GOLD",
          "status":"ACTIVE","balance_sar":10.0,"data_gb_left":1.0})
json.dump(d, open(p,"w"), indent=2)
PY
# On the Linux lab VMs any host path works. On a macOS/Windows `podman machine`
# the path must be under your HOME (only that is mounted into the VM) — e.g. use
# "$HOME/edge-data" instead of /tmp/edge-data.
podman run -d --name selfcare-edge -p 8081:8080 -v /tmp/edge-data:/app/data:Z selfcare-api:1.0.0
curl -s localhost:8081/subscribers/966599999999     # served WITHOUT rebuilding the image
# Baked-in data ships inside an image layer (immutable, in every pull). The mounted
# volume lives on the host and shadows /app/data at run time; `podman rm` deletes the
# container's writable layer but NOT the host volume, and never the image layer.

# D — publish & pull by digest
podman tag selfcare-api:1.0.0 docker.io/<your-registry-user>/selfcare-api:1.0.0
podman login docker.io                              # prompts; stored in auth.json (git-ignored)
podman push docker.io/<your-registry-user>/selfcare-api:1.0.0     # note the sha256 digest
podman rmi docker.io/<your-registry-user>/selfcare-api:1.0.0
podman pull docker.io/<your-registry-user>/selfcare-api@sha256:<digest-from-push>
podman run -d --name selfcare-pinned -p 8082:8080 \
  docker.io/<your-registry-user>/selfcare-api@sha256:<digest-from-push>
curl -s localhost:8082/healthz

# cleanup
podman rm -f selfcare selfcare-edge selfcare-pinned
```

**Key points:** one image → many containers; configuration belongs in the
*environment*, not the image; durable/large data belongs in a *volume*, not the
writable layer; and a **digest** (`@sha256:`) pins the exact bytes you tested —
tags can move, digests cannot. These three ideas reappear as ConfigMaps,
PersistentVolumes, and image digests in Modules 2–3.
</details>

---

> **✅ Verified:** podman 5.8.2 · 2026-06-25 · base `ubi9/python-39`. The build,
> run, env-override, volume-override, and auth flows above are from real runs on
> this app. (Registry push/pull uses your own account — commands shown, digest is
> account-specific.)
