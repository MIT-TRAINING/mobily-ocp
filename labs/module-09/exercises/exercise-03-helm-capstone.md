# Exercise 3 — Package an App with Helm (Capstone)

> **Scenario:** Package the Mobily **self-care** app as a **Helm chart** so it deploys many
> ways from one template. Scaffold the chart, set sensible defaults, validate and render it
> (offline), then install it as a release and walk **upgrade → rollback**. This capstone
> ties together chart authoring, values, and the release lifecycle.

| | |
|---|---|
| **Practice** | `helm create`/`lint`/`template`/`show values` · values override · install/upgrade/rollback/history |
| **Maps to** | Guide §5, §6, §7 · Visualization 03 · Demo 3 |
| **Difficulty** | ⭐⭐⭐ Advanced (capstone) · ~30–35 min · authoring is **offline**; install needs a cluster (normal user OK) |

---

## Tasks

1. Scaffold a chart named **`self-care`** and list its files.
2. Edit `values.yaml` defaults to a rootless UBI image
   (`registry.access.redhat.com/ubi9/httpd-24:latest`, port 8080) and `replicaCount: 2`.
3. **`helm lint`** the chart (must pass), then **`helm template`** it and confirm the
   rendered `replicas` and `image` — all **offline, no cluster**.
4. Override at render time: `--set replicaCount=4` and confirm the rendered value changes.
5. **(cluster)** `helm install self-care ./self-care`; list the release; `helm upgrade`
   with `replicaCount=5`; then `helm rollback` to revision 1 and read `helm history`.

> **Hint (Task 3):** `helm template self-care ./self-care | grep -E 'replicas:|image:'`.

> **Hint (Task 4):** `--set` beats `values.yaml`; you don't have to edit the file to test.

---

## Validation

```bash
# Tasks 1–4 run OFFLINE (no cluster):
helm lint ./self-care                                   # 0 chart(s) failed
helm template self-care ./self-care | grep -E 'replicas:|image:'          # replicas: 2, UBI image
helm template self-care ./self-care --set replicaCount=4 | grep 'replicas:' # replicas: 4

# Task 5 (cluster):
helm list                                               # self-care, revision, deployed
helm history self-care                                  # 1 install, 2 upgrade, 3 rollback
```

---

## Reflection

- Which steps here needed a cluster, and which were pure local authoring?
- How does one chart serve dev and prod without duplicated YAML?
- After a bad upgrade, what does `helm rollback` do to the revision history?

---

<details>
<summary><strong>✅ Solution</strong> (try the tasks first)</summary>

```bash
# 1. Scaffold
helm create self-care
find self-care -maxdepth 2 -type f | sort

# 2. Edit defaults in self-care/values.yaml:
#    replicaCount: 2
#    image: { repository: registry.access.redhat.com/ubi9/httpd-24, tag: "latest" }
#    service: { port: 8080 }
#    (or override at render/install time with --set)

# 3. Lint + render (OFFLINE)
helm lint ./self-care
helm template self-care ./self-care \
  --set replicaCount=2 \
  --set image.repository=registry.access.redhat.com/ubi9/httpd-24 \
  --set image.tag=latest | grep -E 'replicas:|image:'

# 4. Override at render time
helm template self-care ./self-care --set replicaCount=4 | grep 'replicas:'

# 5. (cluster) install → upgrade → rollback
helm install self-care ./self-care --set replicaCount=2
helm list
helm upgrade self-care ./self-care --set replicaCount=5
helm history self-care
helm rollback self-care 1
helm history self-care

# Cleanup
helm uninstall self-care        # if installed
rm -rf self-care
```

**Verified output (Tasks 1, 3, 4 — helm v3.16.3, run live offline):**

```
Creating self-care
==> Linting ./self-care
[INFO] Chart.yaml: icon is recommended
1 chart(s) linted, 0 chart(s) failed

# helm template ... --set replicaCount=2 --set image...=ubi9/httpd-24:latest
  replicas: 2
          image: "registry.access.redhat.com/ubi9/httpd-24:latest"

# --set replicaCount=4
  replicas: 4
```

**Representative output (Task 5 — requires a cluster):**

```
NAME: self-care
REVISION: 1
STATUS: deployed
REVISION  STATUS       DESCRIPTION
1         superseded   Install complete
2         deployed     Upgrade complete
3         deployed     Rollback to 1
```

**Key point:** the chart is authored and validated **entirely offline** (`create`/`lint`/
`template` — no cluster), which is why Helm fits CI. Values (defaults + `--set` overrides,
`--set` winning) make one chart serve many environments. Installing creates a **release**;
`upgrade`/`rollback` give a versioned, reversible lifecycle (add `--atomic` to auto-revert a
failed upgrade).
</details>

---

> **✅ Verified (authoring) / ◐ representative (install).** Tasks 1, 3, 4
> (`helm create`/`lint`/`template` with `--set`) were **run live with helm v3.16.3** —
> that output is real, no cluster needed. Task 5 (`helm install`/`upgrade`/`rollback`)
> **requires a live cluster** and is **representative of a real run**; a normal user can
> validate it in their own project when the cluster is up.
