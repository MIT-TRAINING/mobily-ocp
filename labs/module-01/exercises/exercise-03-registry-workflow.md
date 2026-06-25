# Exercise 3 — Registry Workflow (Tag, Push, Pull)

> **Scenario:** Your **SMS Gateway** image (Exercise 2) runs locally, but the NOC
> in another data center needs it. Ship it through a registry and pull it back as
> if onto a fresh node.

| | |
|---|---|
| **Practice** | `login`, `tag`, `push`, `pull`, digests |
| **Maps to** | Visualization 05, Demo 3 |
| **Difficulty** | ⭐⭐ Intermediate · ~20 min |
| **Prereq** | `sms-gateway:1.1` from Exercise 2 · a free **Quay.io** or **Docker Hub** account |

---

> **⚠️ Requires a registry login.** This exercise pushes to / pulls from a real
> registry, so you need your own **Quay.io** (or Docker Hub) account: `podman login`
> first and replace `<your-namespace>` with **your** namespace.

## Tasks

1. **Log in** to your registry (`quay.io` or `docker.io`). Use a **token**, not
   your account password, where possible.

2. **Tag** `sms-gateway:1.1` with your full remote reference, e.g.
   `quay.io/<your-namespace>/sms-gateway:1.1`.

3. **Push** the image. Watch which layers upload.

4. Capture the image's **digest** (`sha256:...`).

5. **Simulate a fresh node:** remove the local image(s), then **pull** the image
   back from the registry and run it. Confirm `/health` responds.

6. **Bonus:** pull the image **by digest** instead of by tag.

---

## Validation

```bash
# Task 2 — both names point to the same IMAGE ID
podman images | grep sms-gateway

# Task 4 — digest present
podman inspect quay.io/<your-namespace>/sms-gateway:1.1 \
  --format '{{index .RepoDigests 0}}'

# Task 5 — after rmi + pull + run
curl -s http://localhost:8080/health
# {"component":"sms-gateway","status":"ok"}
```

---

## Stretch goals

- Push a second tag (`:latest`) pointing at the **same** image and confirm both
  tags share one digest. Then discuss: why is deploying `:latest` risky in
  production?
- Inspect your local credentials file location
  (`${XDG_RUNTIME_DIR}/containers/auth.json`) and confirm it is **not** something
  you'd ever commit to git.
- Use `skopeo inspect docker://quay.io/<your-namespace>/sms-gateway:1.1` to read
  the manifest **without pulling** the image.

---

## Reflection

- What are the four parts of `quay.io/<your-namespace>/sms-gateway:1.1`?
- During push, why were some layers skipped or fast?
- When would you deploy by digest instead of tag?

---

<details>
<summary><strong>✅ Solution</strong></summary>

```bash
# 1. Login (use a token when prompted for password)
podman login quay.io

# 2. Tag for the registry (replace <your-namespace>)
podman tag sms-gateway:1.1 quay.io/<your-namespace>/sms-gateway:1.1

# 3. Push
podman push quay.io/<your-namespace>/sms-gateway:1.1

# 4. Digest
podman inspect quay.io/<your-namespace>/sms-gateway:1.1 \
  --format '{{index .RepoDigests 0}}'

# 5. Simulate a fresh node
podman rmi quay.io/<your-namespace>/sms-gateway:1.1 sms-gateway:1.1
podman pull quay.io/<your-namespace>/sms-gateway:1.1
podman run -d --name sms -p 8080:8080 quay.io/<your-namespace>/sms-gateway:1.1
curl -s http://localhost:8080/health

# 6. Bonus — pull by digest
podman pull quay.io/<your-namespace>/sms-gateway@sha256:<paste-digest>

# cleanup
podman rm -f sms
podman logout quay.io
```

**Key point:** `tag` only adds a label — both names reference the same image ID.
The **tag** is mutable; the **digest** (`@sha256:...`) is the immutable content
hash. Pushing uploads only layers the registry lacks. Pin production to a version
tag or digest, never bare `:latest`.
</details>

---

> **◐ Partially verified:** podman 5.8.2 · 2026-06-25. Local `build`/`tag`/`run`
> mechanics verified; `login`/`push`/`pull` require your own registry account.
