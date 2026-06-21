# Exercise 5 — Capstone: Run a Small Self-Care Portal Stack

> **Scenario:** Bring it all together. Stand up a miniature **Customer Self-Care
> Portal** the way a telecom would: a **front end**, an **API** you build
> yourself, and a **database** with persistent storage — all wired on a private
> network. This exercise exercises every Module 1 skill at once.

| | |
|---|---|
| **Practice** | build + run + network + volume + lifecycle (everything) |
| **Maps to** | All Module 1 visualizations & demos |
| **Difficulty** | ⭐⭐⭐ Advanced · ~45 min |

---

## Target architecture

```
                 host :8090
                      │
              ┌───────▼────────┐
              │  selfcare-web  │  (front end, published)
              └───────┬────────┘
                      │  selfcare-net (private, DNS by name)
              ┌───────▼────────┐
              │  selfcare-api  │  (you BUILD this image)
              └───────┬────────┘
                      │
              ┌───────▼────────┐
              │  selfcare-db   │  (PostgreSQL + VOLUME)
              └────────────────┘
```

Only `selfcare-web` is exposed to the host. The API and DB stay private. The DB
uses a **volume** so subscriber data survives a rebuild.

---

## Requirements (acceptance criteria)

1. A **private network** `selfcare-net` exists; the API and DB are **not**
   published to the host.
2. **`selfcare-db`** runs PostgreSQL with a **named volume** for its data dir, and
   contains a `subscribers` table with at least one row (a fake account).
3. **`selfcare-api`** is an image **you build** (`selfcare-api:1.0`) that returns
   a subscriber's account summary as JSON on `/account`. It may read from the DB
   or, to keep it simple, return a static summary — your choice, but it must be
   **your image** built from a Containerfile.
4. **`selfcare-web`** (any stock httpd/nginx) is published on host port **8090**.
5. **Persistence proof:** destroy and recreate `selfcare-db` with the same volume
   and show the subscriber row survived.
6. **Cleanup** removes all containers, the volume, the network, and your image.

---

## Validation

```bash
# Req 1 — private services have NO host ports
podman ps --format "table {{.Names}}\t{{.Ports}}"
# selfcare-web shows 0.0.0.0:8090->...   ; api and db show no host mapping

# Req 3 — your API answers
podman exec selfcare-web curl -s http://selfcare-api:8080/account
# e.g. {"msisdn":"966500000001","plan":"POST-PRO-200","balance_sar":37.50,"status":"ACTIVE"}

# Req 4 — front end reachable from the host
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8090   # 200

# Req 5 — DB row persists across a rebuild
podman exec selfcare-db psql -U portal -d portal -c "SELECT msisdn,plan FROM subscribers;"
```

---

## Hints

- Reuse the Flask pattern from Exercise 2 for `selfcare-api`.
- Containers on `selfcare-net` reach each other by name: the web can curl
  `http://selfcare-api:8080`, the API can connect to `selfcare-db:5432`.
- For PostgreSQL persistence, mount the volume at `/var/lib/pgsql/data`.
- Test inter-container calls with `podman exec selfcare-web curl ...`.

---

## Reflection — connect to the platform

For each piece, name the **OpenShift** equivalent you'll meet later:

| Module 1 construct (this exercise) | OpenShift equivalent (later modules) |
|------------------------------------|--------------------------------------|
| `podman build` your API image | BuildConfig / source-to-image (Module 9) |
| `selfcare-net` + DNS by name | Service + cluster DNS (Module 6) |
| `-p 8090` published front end | Route / Ingress (Module 6) |
| named **volume** | PersistentVolumeClaim (Module 7) |
| DB password on the CLI | Secret (Module 7) |
| the three containers together | a Deployment / pod set (Modules 3–9) |

---

<details>
<summary><strong>✅ Solution</strong> (one correct approach)</summary>

**1. API image — `~/selfcare-api/app.py`:**
```python
from flask import Flask, jsonify
app = Flask(__name__)

@app.get("/account")
def account():
    return jsonify(msisdn="966500000001", plan="POST-PRO-200",
                   balance_sar=37.50, status="ACTIVE")

@app.get("/health")
def health(): return jsonify(status="ok")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
```
`~/selfcare-api/requirements.txt`: `flask==3.0.3`

`~/selfcare-api/Containerfile`:
```dockerfile
FROM registry.access.redhat.com/ubi9/python-311:latest
WORKDIR /opt/app-root/src
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
EXPOSE 8080
CMD ["python", "app.py"]
```

**2. Build and assemble the stack:**
```bash
cd ~/selfcare-api && podman build -t selfcare-api:1.0 .

# private network
podman network create selfcare-net

# database with a volume (Req 2)
podman volume create selfcare-data
podman run -d --name selfcare-db --network selfcare-net \
  -e POSTGRESQL_USER=portal -e POSTGRESQL_PASSWORD=portal-pass \
  -e POSTGRESQL_DATABASE=portal \
  -v selfcare-data:/var/lib/pgsql/data \
  registry.access.redhat.com/rhel9/postgresql-15:latest
sleep 6
podman exec selfcare-db psql -U portal -d portal -c \
  "CREATE TABLE subscribers(msisdn text, plan text, status text);"
podman exec selfcare-db psql -U portal -d portal -c \
  "INSERT INTO subscribers VALUES ('966500000001','POST-PRO-200','ACTIVE');"

# API (private, no -p)  (Req 3)
podman run -d --name selfcare-api --network selfcare-net selfcare-api:1.0

# front end (published)  (Req 4)
podman run -d --name selfcare-web --network selfcare-net -p 8090:8080 \
  registry.access.redhat.com/ubi9/httpd-24:latest httpd -DFOREGROUND
```

**3. Validate:**
```bash
podman ps --format "table {{.Names}}\t{{.Ports}}"
podman exec selfcare-web curl -s http://selfcare-api:8080/account
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8090
```

**4. Persistence proof (Req 5):**
```bash
podman rm -f selfcare-db
podman run -d --name selfcare-db --network selfcare-net \
  -e POSTGRESQL_USER=portal -e POSTGRESQL_PASSWORD=portal-pass -e POSTGRESQL_DATABASE=portal \
  -v selfcare-data:/var/lib/pgsql/data \
  registry.access.redhat.com/rhel9/postgresql-15:latest
sleep 6
podman exec selfcare-db psql -U portal -d portal -c "SELECT msisdn,plan FROM subscribers;"
# the row is still there → volume persisted the data
```

**5. Cleanup (Req 6):**
```bash
podman rm -f selfcare-web selfcare-api selfcare-db
podman volume rm selfcare-data
podman network rm selfcare-net
podman rmi selfcare-api:1.0
```

**What you proved:** you built an image, ran a multi-container app on a private
network with name-based DNS, exposed only the front end, and persisted data with
a volume across a rebuild — the complete Module 1 toolkit, and a direct preview of
how the same stack is expressed on OpenShift.
</details>
