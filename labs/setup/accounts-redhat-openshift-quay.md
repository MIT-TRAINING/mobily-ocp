# Account Setup — Red Hat, OpenShift Developer Sandbox & Quay.io

Before the labs begin, every participant needs three free accounts. They all
build on **one** Red Hat login, so create that first and the rest reuse it.

| # | Account | Cost | What it gives you | Time |
|---|---------|------|-------------------|------|
| 1 | **Red Hat account** + Developer Subscription for Individuals | Free | Single sign-on for everything below; pull access to Red Hat container images / UBI; no-cost RHEL on up to 16 systems | ~5 min |
| 2 | **OpenShift Developer Sandbox** | Free | Private access to a shared OpenShift 4 cluster — 30-day renewable trial, no credit card | ~5 min |
| 3 | **Quay.io** | Free (public repos) | Container registry for `podman push` / `podman pull` in the registry labs | ~3 min |

> ✅ **Do these before Session 1.** All three are self-service and need no
> approval from the trainer. Use a **personal or work email you can check** —
> each step sends a verification email.

> 🔐 **Never commit or share credentials.** Where a step produces a token,
> password, or pull secret, treat it like the `.pem` key in this folder: keep it
> local. In any committed lab file use placeholders such as `<your-token>` or
> `$OCP_PASSWORD`.

---

## 1. Red Hat account + Developer Subscription for Individuals

This is the foundation. The same login works for the Customer Portal, the
Developer program, the OpenShift Sandbox, and (via SSO) Quay.io.

### Steps

1. Go to **<https://developers.redhat.com/register>**.
2. Fill in the registration form:
   - **Red Hat login** (username — choose carefully, it can't be changed later)
   - Email address, password
   - First / last name, country
3. Accept the **Terms & Conditions** and submit.
4. Open the **verification email** Red Hat sends and click the confirmation link
   to activate the account.
5. Sign in once at **<https://developers.redhat.com>** to confirm it works.

### Activate the no-cost Developer Subscription

Joining the Red Hat Developer program **automatically grants** the *Red Hat
Developer Subscription for Individuals* — no separate purchase. To verify it:

1. Go to **<https://access.redhat.com/management/subscriptions>** (Customer
   Portal → *Subscriptions*).
2. You should see **Red Hat Developer Subscription for Individuals** listed.

What the subscription includes:

- **Red Hat Enterprise Linux** on up to **16 physical or virtual systems**
  (x86_64 and aarch64), for development, demos, prototyping, QA, and small
  production.
- Access to currently supported RHEL releases **plus older versions across a
  ~10-year lifespan**, from the Customer Portal.
- Red Hat Software Collections, Developer Toolset, and related add-ons.

> ⚠️ **One per account.** Only **one** no-cost subscription may be attached to a
> given Red Hat account, and it's **self-supported** (no Red Hat support SLA).
> The subscription is a **12-month** term — renew it yearly (see below).

### Renewing (after 12 months)

If the subscription lapses, re-activate it at
**<https://developers.redhat.com/d4i-renewal>** while signed in. Renewal is free
and reuses the same account.

---

## 2. OpenShift Developer Sandbox

A free, no-commitment **30-day trial** giving you private access to a shared,
multi-tenant **OpenShift 4** cluster — ideal for the OpenShift labs in this
course. No credit card required; it only needs the Red Hat account from Step 1.

### Steps

1. Go to **<https://developers.redhat.com/developer-sandbox>**.
2. Click **Start your sandbox for free**.
3. **Log in** with your Red Hat account (Step 1).
4. **Phone verification** — first-time access requires confirming a phone number
   (Red Hat uses this only to prevent fraudulent accounts; no marketing calls).
   Enter your mobile number, request the **SMS code**, and type it in.
5. Wait for the cluster to provision (usually under a minute), then click
   **Launch** to open the OpenShift web console.

### What you get / limits to know

- The sandbox is **active for 30 days**, and is **renewable** — just start it
  again from the same page when it expires (your work is not preserved across
  re-provisioning).
- You get **pre-created projects/namespaces** (e.g. `<username>-dev` and
  `<username>-stage`). You **cannot** create arbitrary new namespaces or get
  cluster-admin — it is a shared cluster.
- **Idle cleanup:** pods are automatically stopped after **12 hours** of
  continuous running; sandbox VMs stop after **1 hour**. Re-deploy as needed.
- Need more time for a specific reason? The team can extend on request:
  **devsandbox@redhat.com**.

### Log in from the `oc` CLI

The course VM already has `oc` installed (see
[`ocp-training-ubuntu-vm.md`](./ocp-training-ubuntu-vm.md)). To drive the
sandbox from the command line:

1. In the web console, click your **username (top-right) → Copy login command**.
2. Click **Display Token**, then copy the full `oc login …` line.
3. Paste it into the terminal:

   ```bash
   oc login --token=<your-sha256-token> --server=https://api.<sandbox-cluster>:6443
   ```

4. Confirm you're connected:

   ```bash
   oc whoami
   oc get projects
   ```

> The token is short-lived — re-copy it from the console when it expires.

> **Alternative:** Red Hat **OpenShift trials on cloud marketplaces** (AWS,
> Azure) and the full **60-day OpenShift trial** also exist, but the Sandbox is
> the recommended zero-setup option for this course.

---

## 3. Quay.io container registry

`quay.io` is Red Hat's hosted container registry. **Public repositories are
always free** — that's all the registry labs (push/pull, tagging, image
inspection) need. Private repositories require a paid plan.

### Steps

1. Go to **<https://quay.io>** and click **Sign in**.
2. Click **Sign in with Red Hat** and authenticate with the account from Step 1
   (recommended — one fewer password). A Quay username is proposed on first
   login; accept or adjust it.
   - *(Alternatively, "Create Account" lets you register a standalone Quay-only
     username/email/password.)*
3. Confirm your email if prompted.

### Set a CLI password (required for `podman` / `docker` login)

If you signed in via Red Hat SSO you have **no Quay password yet**, so the CLI
can't log in. Create one:

1. Click your **username (top-right) → Account Settings**.
2. Under **Docker CLI Password / CLI Password**, click **Change Password** and
   set a password (or, for better security, use **Generate Encrypted
   Password** to get a CLI-only token that doesn't expose your real password).

### Log in and push an image (Podman-first)

The course uses **Podman**; `docker` is equivalent (`alias docker=podman`).

```bash
# Log in (use your Quay username, not email)
podman login quay.io
#   Username: <your-quay-username>
#   Password: <your-cli-password-or-encrypted-token>

# Tag a local image for your namespace
podman tag localhost/subscriber-api:1.0 \
  quay.io/<your-quay-username>/subscriber-api:1.0

# Push it
podman push quay.io/<your-quay-username>/subscriber-api:1.0
```

### Make a new repository public

New repos default to **private**. To keep within the free tier:

1. Open the repository in the Quay UI → **Settings** (gear icon).
2. Set **Repository Visibility** to **Public**.

(Or create the repository ahead of time via **+ Create New Repository** and
choose **Public**.)

> 💡 For pulling Red Hat images later (e.g. on OpenShift), you may also need your
> **pull secret** from <https://console.redhat.com/openshift/install/pull-secret>.
> Keep it local — never commit it.

---

## Quick checklist

- [ ] Red Hat account created and email verified
- [ ] Developer Subscription for Individuals visible under *Subscriptions*
- [ ] OpenShift Developer Sandbox launched; `oc login` works (`oc whoami`)
- [ ] Quay.io account created (via Red Hat SSO)
- [ ] Quay CLI password set; `podman login quay.io` succeeds

---

## References

- [No-cost RHEL Individual Developer Subscription — FAQs](https://developers.redhat.com/articles/faqs-no-cost-red-hat-enterprise-linux)
- [Activate your no-cost Red Hat Enterprise Linux subscription](https://developers.redhat.com/blog/2021/02/10/how-to-activate-your-no-cost-red-hat-enterprise-linux-subscription)
- [Developer Subscription for Individuals — renewal](https://developers.redhat.com/d4i-renewal)
- [Red Hat OpenShift Developer Sandbox](https://developers.redhat.com/developer-sandbox) · [Sandbox FAQ](https://developers.redhat.com/developer-sandbox/FAQ)
- [OpenShift trial on Developer Sandbox](https://www.redhat.com/en/technologies/cloud-computing/openshift/openshift-developer-sandbox-trial)
- [Getting started with Quay.io](https://docs.quay.io/solution/getting-started.html) · [Quay plans / pricing](https://quay.io/plans/)
