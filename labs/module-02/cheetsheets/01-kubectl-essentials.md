# kubectl Essentials Cheatsheet — Module 2

Commands are shown with **`kubectl`** against a
[minikube](../../setup/minikube-kubernetes.md) Kubernetes cluster. On OpenShift
(Module 3+) the same commands work as **`oc`** — notes call out the few
differences. Examples reuse the telecom services from the
[demos](../demos)/[exercises](../exercises).

> **Mental model:** every command below is an authenticated HTTPS call to the **one
> API server**. You declare desired state (`spec`); controllers reconcile actual
> state (`status`). Nothing here talks to etcd or a node directly.

---

## 1. Cluster (minikube) & context

| Command | What it does |
|---------|--------------|
| `minikube start --driver=docker` | Start a single-node cluster + wire up kubeconfig |
| `minikube start --nodes 3` | Start a 3-node cluster (for scheduling/drain demos) |
| `minikube status` / `minikube stop` / `minikube delete` | Health / pause / destroy |
| `kubectl config current-context` | Which cluster you're talking to (`minikube`) |
| `kubectl cluster-info` | API server + CoreDNS URLs (your front door) |
| `kubectl auth whoami` | Your identity. *OpenShift: `oc whoami`* |
| `kubectl version` | Client + server versions |

---

## 2. Namespaces

| Command | What it does |
|---------|--------------|
| `kubectl create namespace <name>` | Create a namespace. *OpenShift: `oc new-project <name>`* |
| `kubectl config set-context --current --namespace=<name>` | Switch default namespace. *OpenShift: `oc project <name>`* |
| `kubectl config view --minify -o jsonpath='{..namespace}'` | Show current namespace |
| `kubectl get namespaces` | List namespaces. *OpenShift: `oc get projects`* |
| `kubectl delete namespace <name>` | Delete a namespace and everything in it |

---

## 3. The core verbs (work on any object)

| Command | What it does |
|---------|--------------|
| `kubectl get <kind>` | List objects (`pods`, `svc`, `deploy`, `rs`, `nodes`, `events`…) |
| `kubectl get <kind> -o wide` | Add columns (pods: NODE, IP) |
| `kubectl get <kind> <name> -o yaml` | Full object as YAML |
| `kubectl describe <kind> <name>` | Human-readable detail **+ Events** (start debugging here) |
| `kubectl explain <kind>` / `kubectl explain <kind>.spec` | Field-level schema docs (no cluster change) |
| `kubectl get <kind> -w` | **Watch** — stream changes live |
| `kubectl get all` | Common objects in the current namespace |
| `kubectl api-resources` | Every object type the cluster exposes |
| `kubectl delete <kind> <name>` | Delete an object |
| `kubectl apply -f <file>` | Declaratively create/update from a manifest |
| `kubectl create -f <file>` | Create from a manifest (errors if it exists) |
| `kubectl edit <kind> <name>` | Open the live object in `$EDITOR` |

---

## 4. Labels & selectors (the glue)

| Command | What it does |
|---------|--------------|
| `kubectl get pods -l app=subscriber-api` | List by label selector |
| `kubectl get pods --show-labels` | Show every pod's labels |
| `kubectl label pod <name> tier=frontend` | Add/replace a label (`--overwrite`) |
| `kubectl label pod <name> tier-` | Remove a label (trailing `-`) |
| `kubectl get pods -L app -L tier` | Show given labels as **columns** |

---

## 5. Output & JSONPath (scripting-friendly)

| Command | What it does |
|---------|--------------|
| `kubectl get pod <p> -o jsonpath='{.status.phase}{"\n"}'` | One field |
| `kubectl get deploy <d> -o jsonpath='{.spec.replicas}'` | Desired replicas |
| `kubectl get deploy <d> -o jsonpath='{.status.availableReplicas}'` | Actual replicas |
| `kubectl get pods -o jsonpath='{.items[*].spec.nodeName}'` | All pods' nodes |
| `kubectl get pods -o name` | Just `pod/<name>` lines (great for scripting) |
| `kubectl get pods --sort-by=.metadata.creationTimestamp` | Sorted output |
| `kubectl get pod <p> -o custom-columns=NAME:.metadata.name,NODE:.spec.nodeName` | Custom columns |

**Example — spec vs status side by side:**
```bash
kubectl get deployment subscriber-api \
  -o jsonpath='spec={.spec.replicas} avail={.status.availableReplicas}{"\n"}'
```

---

## 6. Workloads: deploy, scale, roll out

| Command | What it does |
|---------|--------------|
| `kubectl create deployment <n> --image=<img> --replicas=3` | Create a Deployment |
| `kubectl scale deployment <n> --replicas=5` | Change **desired** count (scaling = editing spec) |
| `kubectl get deploy,rs,pods -l app=<n>` | See the Deployment→ReplicaSet→Pod chain |
| `kubectl rollout status deployment/<n>` | Track a rollout to completion |
| `kubectl rollout restart deployment/<n>` | Recreate all pods (re-trigger scheduling) |
| `kubectl rollout undo deployment/<n>` | Roll back to the previous ReplicaSet |
| `kubectl delete pod <p>` | Delete a pod — the ReplicaSet **recreates** it (self-healing) |

> **OpenShift extra:** `oc new-app <img>` creates a Deployment **+** Service in one
> command. On Kubernetes, do the two steps: `kubectl create deployment …` then
> `kubectl expose deployment …`.

**Telecom example:**
```bash
kubectl create deployment subscriber-api \
  --image=registry.access.redhat.com/ubi9/httpd-24:latest --replicas=3
kubectl scale deployment subscriber-api --replicas=6     # evening peak
```

---

## 7. Inspect a running pod

| Command | What it does |
|---------|--------------|
| `kubectl logs <pod>` / `kubectl logs -f <pod>` | Container logs (follow with `-f`) |
| `kubectl logs <pod> -c <container>` | A specific container in the pod |
| `kubectl exec <pod> -- <cmd>` | Run a command in a pod |
| `kubectl exec -it <pod> -- sh` | Interactive shell. *OpenShift: `oc rsh <pod>`* |
| `kubectl port-forward <pod> 8080:8080` | Tunnel a pod port to localhost |
| `kubectl get pod <p> -o jsonpath='{.status.conditions[*].type}'` | Birth milestones: PodScheduled→Initialized→ContainersReady→Ready (k8s ≥1.31 also lists `PodReadyToStartContainers`; emitted order varies) |

---

## 8. Services & DNS (service discovery)

| Command | What it does |
|---------|--------------|
| `kubectl expose deployment <n> --port=8080` | Create a ClusterIP Service. *OpenShift: `oc expose …`* |
| `kubectl get svc <n>` | Show the Service + its stable ClusterIP |
| `kubectl get svc <n> -o jsonpath='{.spec.selector}'` | The Service's selector |
| `kubectl get endpoints <n>` | Live pod IPs behind the Service (match **+** Ready) |
| `kubectl get endpointslices -l kubernetes.io/service-name=<n>` | Newer endpoint representation (**preferred on k8s 1.33+**) |

> **k8s 1.33+ note:** `kubectl get endpoints` still works but prints
> `Warning: v1 Endpoints is deprecated in v1.33+; use discovery.k8s.io/v1 EndpointSlice`.
> Prefer `kubectl get endpointslices -l kubernetes.io/service-name=<n>`.

**DNS resolution from inside the cluster** (a throwaway client pod):
```bash
kubectl run tmp --rm -it --restart=Never \
  --image=registry.access.redhat.com/ubi9/ubi -- \
  bash -c 'getent hosts subscriber-api; curl -s http://subscriber-api:8080/'
# OpenShift equivalent: oc debug --image=registry.access.redhat.com/ubi9/ubi -- ...
```

> **Service FQDN:** `<service>.<namespace>.svc.cluster.local` → the Service's stable
> ClusterIP. kube-proxy then load-balances to a live endpoint. Use the **name**,
> never a pod IP.

---

## 9. Manifests from `<<EOF` (no file needed)

```bash
cat <<'EOF' | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata: { name: subscriber-api }
spec:
  replicas: 3
  selector: { matchLabels: { app: subscriber-api } }
  template:
    metadata: { labels: { app: subscriber-api } }
    spec:
      containers:
        - name: api
          image: registry.access.redhat.com/ubi9/httpd-24:latest
          ports: [{ containerPort: 8080 }]
EOF
```

> Generate a starter manifest without applying it:
> `kubectl create deployment subscriber-api --image=<img> --dry-run=client -o yaml`.

---

## 10. Cleanup

| Command | What it does |
|---------|--------------|
| `kubectl delete deployment <n>` | Remove a Deployment (and its pods) |
| `kubectl delete svc <n>` | Remove a Service |
| `kubectl delete all -l app=<n>` | Remove common objects matching a label |
| `kubectl delete namespace <name>` | Nuke the whole namespace |
| `minikube delete` | Destroy the entire cluster (ultimate reset) |

> See the [architecture-inspection sheet](02-architecture-inspection.md) for nodes,
> control-plane components, the scheduler, and diagnosing `Pending`/no-endpoints.
