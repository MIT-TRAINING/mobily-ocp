# Demo 4 — Container Networking & Persistent Storage

> **Scenario:** A **CDR Ingest API** receives Call Detail Records and writes them
> to a database. This needs two things every real telecom service needs:
> containers that can **talk to each other** over a network, and storage that
> **survives** a container restart. We'll build both — and deliberately lose data
> first to prove why.

| | |
|---|---|
| **Concepts reinforced** | Port publishing · container networks & DNS · volumes vs writable layer · ephemerality |
| **Maps to** | Visualization 03 (storage / CoW), Module 1 networking & storage topics |
| **Time** | ~30 minutes |
| **Tools** | `podman` (or `docker`) |

---

> **🐳 Docker equivalents:** Identical — `docker network create`, automatic
> DNS-by-name on user-defined networks, `docker volume create`, and `-v
> name:/path` all behave the same. (Under the hood rootless Podman routes traffic
> via netavark/pasta rather than a Docker bridge, but the commands and the
> behaviour you observe here are unchanged.)

## Part A — Networking: two containers that talk

### Step 1 — Create a user-defined network

```bash
podman network create cdr-net
podman network ls | grep cdr-net
```

> **Narrate:** On a user-defined network, containers get **automatic DNS by name**
> — no hard-coded IPs. This is the seed of what Kubernetes Services do later.

### Step 2 — Start the database (the "CDR store")

```bash
podman run -d --name cdr-db --network cdr-net \
  -e POSTGRESQL_USER=cdr -e POSTGRESQL_PASSWORD=cdr-pass \
  -e POSTGRESQL_DATABASE=cdr \
  registry.access.redhat.com/rhel9/postgresql-15:latest
```

> **Security note:** real credentials never go on the command line like this — in
> OpenShift they come from **Secrets** (Module 7). Here it's for demonstration.

### Step 3 — Start a client container and resolve the DB by name

```bash
podman run -it --rm --network cdr-net \
  registry.access.redhat.com/ubi9/ubi:latest \
  bash -c 'getent hosts cdr-db'
```

```
10.89.0.2     cdr-db
```

> **Narrate:** The name `cdr-db` resolved automatically — that's the container
> network's built-in DNS. The CDR Ingest API would connect to `cdr-db:5432`
> without ever knowing the IP.

### Step 4 — Publish a port to the outside world

```bash
podman run -d --name cdr-api --network cdr-net -p 9090:8080 \
  registry.access.redhat.com/ubi9/nginx-120:latest nginx -g "daemon off;"
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:9090
```

```
200
```

> **Narrate:** `-p 9090:8080` is the only door from the host into the container.
> `cdr-db` has **no** published port — it's reachable only *inside* `cdr-net`.
> That's a basic isolation pattern: expose the API, hide the database.

---

## Part B — Storage: lose data, then keep it

### Step 5 — Demonstrate ephemerality (write to the writable layer)

```bash
podman exec cdr-db bash -c \
  "psql -U cdr -d cdr -c 'CREATE TABLE cdr(id serial, msisdn text, seconds int);'"
podman exec cdr-db bash -c \
  "psql -U cdr -d cdr -c \"INSERT INTO cdr(msisdn,seconds) VALUES ('966500000001', 142);\""
podman exec cdr-db bash -c "psql -U cdr -d cdr -c 'SELECT * FROM cdr;'"
```

```
 id |   msisdn     | seconds
----+--------------+---------
  1 | 966500000001 |     142
```

Now **destroy the container** and recreate it:

```bash
podman rm -f cdr-db
podman run -d --name cdr-db --network cdr-net \
  -e POSTGRESQL_USER=cdr -e POSTGRESQL_PASSWORD=cdr-pass -e POSTGRESQL_DATABASE=cdr \
  registry.access.redhat.com/rhel9/postgresql-15:latest
sleep 5
podman exec cdr-db bash -c "psql -U cdr -d cdr -c 'SELECT * FROM cdr;'"
```

```
ERROR:  relation "cdr" does not exist
```

> **Narrate (the punchline):** The CDR table — and the call record — are **gone**.
> The data lived in the container's writable layer, which was destroyed with the
> container. For a billing system, that's catastrophic. Visualization 03 in one
> command.

### Step 6 — Add a volume so data survives

```bash
podman rm -f cdr-db
podman volume create cdr-data

podman run -d --name cdr-db --network cdr-net \
  -e POSTGRESQL_USER=cdr -e POSTGRESQL_PASSWORD=cdr-pass -e POSTGRESQL_DATABASE=cdr \
  -v cdr-data:/var/lib/pgsql/data \
  registry.access.redhat.com/rhel9/postgresql-15:latest
sleep 5

# write the record again
podman exec cdr-db bash -c \
  "psql -U cdr -d cdr -c 'CREATE TABLE cdr(id serial, msisdn text, seconds int);'"
podman exec cdr-db bash -c \
  "psql -U cdr -d cdr -c \"INSERT INTO cdr(msisdn,seconds) VALUES ('966500000001', 142);\""
```

Now destroy and recreate **with the same volume**:

```bash
podman rm -f cdr-db
podman run -d --name cdr-db --network cdr-net \
  -e POSTGRESQL_USER=cdr -e POSTGRESQL_PASSWORD=cdr-pass -e POSTGRESQL_DATABASE=cdr \
  -v cdr-data:/var/lib/pgsql/data \
  registry.access.redhat.com/rhel9/postgresql-15:latest
sleep 5
podman exec cdr-db bash -c "psql -U cdr -d cdr -c 'SELECT * FROM cdr;'"
```

```
 id |   msisdn     | seconds
----+--------------+---------
  1 | 966500000001 |     142
```

> **Narrate:** Same data, brand-new container. The **volume's lifecycle is
> independent** of the container. This is the exact principle OpenShift scales up
> with Persistent Volumes and Persistent Volume Claims (Module 7).

---

## Step 7 — Cleanup

```bash
podman rm -f cdr-api cdr-db
podman volume rm cdr-data
podman network rm cdr-net
```

---

## Wrap-up questions to pose

1. How did `cdr-api` reach `cdr-db` without knowing its IP address?
2. Why was `cdr-db` *not* given a `-p` published port?
3. Two containers were destroyed and recreated — why did data survive the second
   time but not the first?
