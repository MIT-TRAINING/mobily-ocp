# Module 1 — Exercises (Hands-On Practice)

These are **participant-driven** tasks. Unlike the [demos](../demos) (which the
instructor performs), here **you** do the work, then verify it with the provided
**validation** commands. Each exercise has a fully worked **solution** at the
bottom — try the tasks first, then check.

All scenarios are **telecom-flavored** so you practice in a realistic context.
Sample data (MSISDNs, plans, CDRs) is fictional.

## Exercises in this module

| # | Exercise | What you'll practice | Telecom scenario | Difficulty |
|---|----------|----------------------|------------------|------------|
| 1 | [Run & manage containers](exercise-01-run-and-manage.md) | run, ps, logs, exec, lifecycle | **Number Portability** status service | ⭐ Beginner |
| 2 | [Build an image](exercise-02-build-an-image.md) | Containerfile, layers, build cache | **SMS Gateway** health API | ⭐⭐ Intermediate |
| 3 | [Registry workflow](exercise-03-registry-workflow.md) | tag, login, push, pull, digest | Ship the **SMS Gateway** | ⭐⭐ Intermediate |
| 4 | [Networking & storage](exercise-04-networking-and-storage.md) | networks, DNS, ports, volumes | **Usage Metering** API + cache | ⭐⭐⭐ Advanced |
| 5 | [Capstone: a small stack](exercise-05-capstone-selfcare-stack.md) | everything combined | **Self-Care Portal** stack | ⭐⭐⭐ Advanced |

## Before you start

```bash
podman --version        # or docker --version
podman info | head      # engine healthy?
```

- Commands use **`podman`**; **`docker`** works identically (`alias docker=podman`).
- Replace placeholders like `<your-namespace>` / `<your-msisdn>` with your own
  values.
- **Never** put real passwords in commands or commit credential files
  (`auth.json`, `.env`). Use placeholders, as the exercises show.

## How to self-assess

Each exercise's **Validation** section gives commands whose output confirms
success. If your output matches, you've completed the task. Stuck? The
**Solution** section walks through one correct approach — but learning sticks
better if you struggle a little first.

Companion material: interactive visualizations in [`../`](../index.html), the
guided [demos](../demos), and the concept guide in
[`../../../guides/module-01-container-fundamentals.md`](../../../guides/module-01-container-fundamentals.md).
