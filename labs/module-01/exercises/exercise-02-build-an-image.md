# Exercise 2 — Build a Container Image

> **Scenario:** Build a containerized **SMS Gateway health/status API** that the
> NOC can poll. You'll author a `Containerfile`, build the image, and prove you
> understand the **build cache**.

| | |
|---|---|
| **Practice** | Containerfile authoring · `build` · `history` · layer cache |
| **Maps to** | Visualization 03 & 05, Demo 2 |
| **Difficulty** | ⭐⭐ Intermediate · ~30 min |

---

## Tasks

1. Create a working directory `~/sms-gateway` and add a tiny app `app.py`:
   ```python
   from flask import Flask, jsonify
   app = Flask(__name__)
   QUEUE = {"queued": 12, "sent_last_min": 4187, "failed_last_min": 3}

   @app.get("/health")
   def health(): return jsonify(status="ok", component="sms-gateway")

   @app.get("/metrics")
   def metrics(): return jsonify(QUEUE)

   if __name__ == "__main__":
       app.run(host="0.0.0.0", port=8080)
   ```
   and `requirements.txt` containing `flask==3.0.3`.

2. Write a **`Containerfile`** that:
   - starts `FROM registry.access.redhat.com/ubi9/python-311:latest`
   - sets the working directory to `/opt/app-root/src`
   - installs dependencies **in a layer that caches independently of the app code**
   - copies `app.py`
   - exposes port `8080` and runs `python app.py`

3. **Build** the image tagged `sms-gateway:1.0`.

4. List the image **layers** with `podman history`.

5. **Edit `app.py` only** (e.g., change `"queued": 12` to `"queued": 20`) and
   rebuild as `sms-gateway:1.1`. Confirm from the build output that the
   dependency-install layer was **served from cache** (not re-run).

6. Run `sms-gateway:1.1` on port 8080 and verify `/health` and `/metrics`.

---

## Validation

```bash
# Task 3/4
podman images sms-gateway
podman history sms-gateway:1.0

# Task 5 — look for "Using cache" on the pip install step
podman build -t sms-gateway:1.1 . 2>&1 | grep -iE "pip install|using cache"

# Task 6
podman run -d --name sms -p 8080:8080 sms-gateway:1.1
curl -s http://localhost:8080/health    # {"component":"sms-gateway","status":"ok"}
curl -s http://localhost:8080/metrics   # {"failed_last_min":3,"queued":20,"sent_last_min":4187}
```

---

## Stretch goals

- **Break the cache on purpose:** move `COPY app.py .` *above* the `pip install`
  line, rebuild, and observe Flask reinstalling on every code change. Then put it
  back and explain why order matters.
- Add a `LABEL maintainer="noc@operator.example"` and find it via
  `podman inspect`.
- Compare image size to the base: `podman images` — how much did your app add on
  top of the base layer?

---

## Reflection

- Why install dependencies in a separate, earlier layer than the app code?
- If 5 teams build images `FROM ubi9/python-311`, how many copies of that base
  layer exist on a host?

---

<details>
<summary><strong>✅ Solution</strong></summary>

**Containerfile:**
```dockerfile
FROM registry.access.redhat.com/ubi9/python-311:latest
WORKDIR /opt/app-root/src

# Dependencies first → cached unless requirements.txt changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code last → changes most often
COPY app.py .

EXPOSE 8080
CMD ["python", "app.py"]
```

**Commands:**
```bash
mkdir -p ~/sms-gateway && cd ~/sms-gateway
# ... create app.py, requirements.txt, Containerfile ...

podman build -t sms-gateway:1.0 .
podman history sms-gateway:1.0

sed -i 's/"queued": 12/"queued": 20/' app.py
podman build -t sms-gateway:1.1 .     # STEP for pip install shows "Using cache"

podman run -d --name sms -p 8080:8080 sms-gateway:1.1
curl -s http://localhost:8080/health
curl -s http://localhost:8080/metrics

# cleanup
podman rm -f sms
```

**Key point:** Because `requirements.txt` (and its `pip install`) sit in an
earlier, unchanged layer, editing `app.py` only invalidates the final small
layer — the expensive dependency install is reused from cache. Reorder them and
every code change reinstalls Flask. The base layer is stored **once** and shared
by all images built `FROM` it.
</details>

---

> **✅ Verified:** podman 5.8.2 · 2026-06-25 · base `ubi9/python-311:latest`.
> Build, `--> Using cache` on the pip layer, and `/health` + `/metrics` responses
> above are from a real run.
