# Kubernetes Dashboard — enable & access from the browser

How to open the **minikube Kubernetes Dashboard** on a lab VM, through the
browser, over the VM's trusted HTTPS URL (`https://<ip-dashes>.sslip.io/`).

The dashboard runs *inside* minikube. We reach it through two layers:

1. **`kubectl proxy`** on the VM — authenticates to the cluster and exposes the
   API server (and the dashboard's service proxy) on `localhost:8001`.
2. **code-server's built-in authenticated proxy** — `/proxy/8001/` forwards your
   already-logged-in browser session to that local port. So the dashboard inherits
   code-server's login + the VM's trusted Let's Encrypt cert; no SSH tunnel, no
   separate port to open in the security group.

> The participant VMs (cloned from the golden AMI) enable the dashboard addon at
> boot via `lab-cluster.service`, so steps 1–2 are usually the only ones needed.
> Step 0 is for the trainer box / any VM where the addon was turned off.

---

## Step 0 — make sure the dashboard addon is enabled

The dashboard only exists if the addon is on. Symptom when it's **off**:
`kubectl proxy` works but the dashboard URL returns

```json
{ "status": "Failure", "message": "services \"kubernetes-dashboard\" not found",
  "reason": "NotFound", "code": 404 }
```

Enable it (idempotent — safe to run if already on):

```bash
minikube addons enable dashboard
```

Wait for the pods, then confirm the service exists:

```bash
kubectl -n kubernetes-dashboard rollout status deploy/kubernetes-dashboard
kubectl -n kubernetes-dashboard get svc
```

You should see a `kubernetes-dashboard` service before continuing.

---

## Step 1 — start `kubectl proxy` (in a code-server terminal)

Open a terminal in code-server (Terminal → New Terminal) and run:

```bash
kubectl proxy --port=8001 --accept-hosts='.*'
```

Leave this terminal running. Two flags matter:

- `--port=8001` — the port code-server will forward to.
- `--accept-hosts='.*'` — **required.** By default `kubectl proxy` only accepts
  requests whose `Host` header is `localhost`/`127.0.0.1` and returns
  **`Forbidden`** for anything else. Requests arriving through code-server carry the
  external `*.sslip.io` host, so without this flag every request is rejected:

  ```
  Forbidden (403)
  ```

To keep it running after you close the terminal:

```bash
nohup kubectl proxy --port=8001 --accept-hosts='.*' >/tmp/kproxy.log 2>&1 &
```

---

## Step 2 — open the dashboard in your browser

Use your VM's own host (the one in the address bar of your lab URL) and append the
proxy path:

```
https://<ip-dashes>.sslip.io/proxy/8001/api/v1/namespaces/kubernetes-dashboard/services/http:kubernetes-dashboard:/proxy/
```

Example for `13.205.136.90`:

```
https://13-205-136-90.sslip.io/proxy/8001/api/v1/namespaces/kubernetes-dashboard/services/http:kubernetes-dashboard:/proxy/
```

The dashboard loads with **no token prompt** — `kubectl proxy` authenticates with
the VM's kubeconfig on your behalf.

---

## Notes & gotchas

- **Use `/proxy/8001/`, not `/absproxy/8001/`.** The dashboard's HTML references its
  CSS/JS with *relative* paths, which resolve correctly under `/proxy/<port>/`
  (code-server strips the prefix before forwarding).
- The trailing segment `http:kubernetes-dashboard:/proxy/` (with the colons) is the
  Kubernetes API **service-proxy** syntax — `http:<service-name>:` — not a typo.
  Keep the trailing slash.
- Keep the `kubectl proxy` process alive while using the dashboard.
- This path requires no extra security-group ports: it rides the existing 443 the
  same way the lab editor does.

### Alternative: SSH tunnel from your laptop (no code-server)

If you'd rather not go through the browser editor, `labs/setup/dashboard.sh` opens
an SSH tunnel and runs `kubectl proxy` on the VM, then you open
`http://localhost:8001/...` locally. Nothing is exposed publicly. See that script.
