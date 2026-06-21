# Demo 2 — Build an Image & Explore Layers

> **Scenario:** Marketing wants a **Tariff Catalog API** that returns the
> operator's prepaid/postpaid plans. We'll containerize a tiny Python service,
> build the image, and dissect its layers and build cache.

|                         |                                                                                         |
| ----------------------- | --------------------------------------------------------------------------------------- |
| **Concepts reinforced** | Containerfile → image · layers & build cache · OCI image structure · image vs container |
| **Maps to**             | Visualization 03 (Image Layers & CoW), Visualization 05 (Build → Ship → Run)            |
| **Time**                | ~25 minutes                                                                             |
| **Tools**               | `podman` (or `docker`)                                                                  |

---

> **🐳 Docker equivalents:** `docker build`, `docker images`, `docker history`,
> and `docker inspect` are identical. One cosmetic difference: modern Docker uses
> **BuildKit**, so build output looks different and cached steps are marked
> **`CACHED`** instead of Podman's **`--> Using cache`** (Step 3) — the caching
> _behaviour_ is the same. To see the classic step-by-step output, run
> `DOCKER_BUILDKIT=0 docker build ...`.

## Step 0 — Set up the build context

```bash
mkdir -p ~/tariff-catalog && cd ~/tariff-catalog
```

Create the telecom app — a minimal Flask API (`app.py`):

```python
from flask import Flask, jsonify
app = Flask(__name__)

TARIFFS = [
    {"code": "PRE-VISITOR",   "type": "prepaid",  "monthly_sar": 0,   "data_gb": 5},
    {"code": "POST-PRO-200",  "type": "postpaid", "monthly_sar": 200, "data_gb": 100},
    {"code": "POST-UNLTD-400","type": "postpaid", "monthly_sar": 400, "data_gb": "unlimited"},
]

@app.get("/health")
def health(): return jsonify(status="ok")

@app.get("/tariffs")
def tariffs(): return jsonify(TARIFFS)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
```

Create `requirements.txt`:

```
flask==3.0.3
```

Create the **Containerfile**:

```dockerfile
FROM registry.access.redhat.com/ubi9/python-311:latest
WORKDIR /opt/app-root/src

# Dependencies first — this layer is cached unless requirements.txt changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code last — changes most often
COPY app.py .

EXPOSE 8080
CMD ["python", "app.py"]
```

> **Narrate:** Layer **ordering is deliberate**. Dependencies change rarely, so we
> copy + install them _before_ the frequently-changing app code. We'll exploit
> that cache in Step 3.

---

## Step 1 — Build the image

```bash
podman build -t tariff-catalog:1.0 .
```

**Expected output** (abridged) — note each `STEP` is a layer:

```
STEP 1/7: FROM registry.access.redhat.com/ubi9/python-311:latest
STEP 2/7: WORKDIR /opt/app-root/src
STEP 3/7: COPY requirements.txt .
STEP 4/7: RUN pip install --no-cache-dir -r requirements.txt
STEP 5/7: COPY app.py .
STEP 6/7: EXPOSE 8080
STEP 7/7: CMD ["python", "app.py"]
COMMIT tariff-catalog:1.0
Successfully tagged localhost/tariff-catalog:1.0
```

---

## Step 2 — Inspect the layers

```bash
podman images tariff-catalog
podman history tariff-catalog:1.0
```

`history` shows the layer stack — exactly the model from Visualization 03:

```
ID            CREATED         CREATED BY                                SIZE
<missing>     5 seconds ago   CMD ["python" "app.py"]                   0 B
<missing>     6 seconds ago   COPY app.py .                             1.2 kB
<missing>     8 seconds ago   RUN pip install ... flask                 14 MB
<missing>     12 seconds ago  COPY requirements.txt .                   18 B
...           ...             FROM ubi9/python-311                      ~250 MB
```

> **Narrate:** The big base layer is shared by _every_ image built `FROM` it.
> Your app adds only a few small layers on top — the storage efficiency from the
> visualization.

---

## Step 3 — Prove the build cache (the layer-ordering payoff)

Change **only the app code** (add a plan), then rebuild:

```bash
sed -i '' 's/"data_gb": 100/"data_gb": 150/' app.py
podman build -t tariff-catalog:1.1 .
```

**Expected output** — watch the `Using cache` lines:

```
STEP 3/7: COPY requirements.txt .  --> Using cache
STEP 4/7: RUN pip install ...       --> Using cache    ← deps NOT re-installed
STEP 5/7: COPY app.py .             --> 9a1b... (rebuilt)
```

> **Narrate:** Because dependencies sit in an earlier, unchanged layer, the slow
> `pip install` was **served from cache** — only the app-code layer rebuilt. Put
> the wrong way round, every code change would reinstall Flask. This is _the_
> reason Containerfile order matters.

---

## Step 4 — Run it and confirm it's a telecom API

```bash
podman run -d --name tariff -p 8080:8080 tariff-catalog:1.1
curl -s http://localhost:8080/tariffs | python3 -m json.tool
```

```json
[
  {"code": "PRE-VISITOR", "type": "prepaid", "monthly_sar": 0, "data_gb": 5},
  {"code": "POST-PRO-200", "type": "postpaid", "monthly_sar": 200, "data_gb": 150},
  ...
]
```

---

## Step 5 — Peek at OCI metadata

```bash
podman inspect tariff-catalog:1.1 --format \
  'Cmd: {{.Config.Cmd}} | Exposed: {{.Config.ExposedPorts}} | Arch: {{.Architecture}}'
```

> **Narrate:** That config (entrypoint, exposed ports, architecture) is the **OCI
> image config** — part of what makes the image portable across Docker, Podman,
> and CRI-O on OpenShift.

---

## Step 6 — Cleanup

```bash
podman rm -f tariff
podman rmi tariff-catalog:1.0 tariff-catalog:1.1   # keep base image cached
```

> Keep the `~/tariff-catalog` directory — **Demo 3 pushes this image to a
> registry.**

---

## Wrap-up questions to pose

1. Why did we `COPY requirements.txt` and install deps _before_ copying `app.py`?
2. If ten teams build images `FROM ubi9/python-311`, how many copies of that base
   layer are stored?
3. What's the difference between `tariff-catalog:1.0` and `tariff-catalog:1.1` at
   the layer level?
