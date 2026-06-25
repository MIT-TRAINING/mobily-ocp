# Architecture Inspection Cheatsheet — Module 2

Commands for looking *inside* the cluster — the control plane, worker nodes, the
scheduler, and the event trail that ties them together. On
[minikube](../../setup/minikube-kubernetes.md) you are **cluster-admin**, so all of
these work; node-spreading commands (drain, multi-node placement) need a
multi-node cluster (`minikube start --nodes 3`).

On OpenShift (Module 3+) the same commands work as `oc`; the control plane lives in
`openshift-*` namespaces instead of `kube-system`, and `kubectl taint` ≈
`oc adm taint`.

---

## 1. Nodes — the worker machines

| Command | What it does |
|---------|--------------|
| `kubectl get nodes` | List nodes + STATUS + ROLES |
| `kubectl get nodes -o wide` | Add internal IP, OS, kernel, runtime |
| `kubectl get nodes -L node-role.kubernetes.io/control-plane` | Show roles as a column |
| `kubectl describe node <node>` | Capacity, allocatable, labels, taints, **running pods** |
| `kubectl get node <node> -o jsonpath='{.status.capacity}'` | CPU/memory/pods capacity |
| `kubectl top nodes` | Live CPU/memory per node (needs `minikube addons enable metrics-server`) |
| `kubectl get pods -A -o wide --field-selector spec.nodeName=<node>` | Everything running on one node |
| `minikube node add` | Add a node to a running cluster |

> **minikube note:** the default single node is `minikube` (control-plane **and**
> schedulable). Multi-node adds `minikube-m02`, `minikube-m03` as workers.

---

## 2. Node labels & taints (scheduling inputs)

| Command | What it does |
|---------|--------------|
| `kubectl label node <node> disktype=ssd` | Label a node (a scheduler `nodeSelector` target) |
| `kubectl label node <node> disktype-` | Remove the label (trailing `-`) |
| `kubectl get nodes -L disktype` | Show which nodes carry the label |
| `kubectl taint nodes <node> tenant=billing:NoSchedule` | Repel pods that don't tolerate it. *OpenShift: `oc adm taint nodes …`* |
| `kubectl taint nodes <node> tenant=billing:NoSchedule-` | Remove the taint (trailing `-`) |
| `kubectl cordon <node>` | Mark unschedulable (no **new** pods) |
| `kubectl drain <node> --ignore-daemonsets --delete-emptydir-data` | Evict pods (reschedule elsewhere) |
| `kubectl uncordon <node>` | Return node to service |

---

## 3. Control-plane components (they run as pods)

| Command | What it does |
|---------|--------------|
| `kubectl get pods -n kube-system` | All control-plane + add-on pods |
| `kubectl get pods -n kube-system | grep apiserver` | The API server (the only client of etcd) |
| `kubectl get pods -n kube-system | grep etcd` | etcd (the source of truth) |
| `kubectl get pods -n kube-system | grep scheduler` | The scheduler |
| `kubectl get pods -n kube-system | grep controller-manager` | The reconciliation loops |
| `kubectl get pods -n kube-system | grep coredns` | CoreDNS (service discovery) |
| `kubectl logs -n kube-system <scheduler-pod>` | Scheduler logs (deep dives) |

> **Golden rule reminder:** every component above talks **only** through the API
> server; **etcd is the single source of truth**. Back up etcd = back up the cluster.
> *(OpenShift: these live in `openshift-kube-apiserver`, `openshift-etcd`, etc.,
> managed by cluster Operators.)*

---

## 4. The scheduler — placement & diagnosis

| Command | What it does |
|---------|--------------|
| `kubectl get pods -o wide` | The NODE column = the scheduler's binding |
| `kubectl get pod <p> -o jsonpath='{.spec.nodeName}'` | Which node a pod was bound to |
| `kubectl describe pod <p>` → `Events:` | `Scheduled` (scheduler chose) vs `FailedScheduling` (none fit) |
| `kubectl get events --field-selector reason=FailedScheduling` | All scheduling failures |
| `kubectl get pod <p> -o jsonpath='{.status.qosClass}'` | QoS class (from requests/limits) |

**Diagnosing a `Pending` pod (the #1 scheduling symptom):**
```bash
kubectl get pod <p>                                  # STATUS: Pending
kubectl describe pod <p> | sed -n '/Events:/,$p'     # read the reason
#   "Insufficient cpu/memory"          -> no node has capacity  (lower requests / add nodes)
#   "didn't match node selector/affinity" -> no node has the required label
#   "had untolerated taint ..."        -> add a matching toleration
#   "Insufficient <quota>" / exceeded quota -> namespace ResourceQuota too small
```

---

## 5. Reconciliation & self-healing (watch it work)

| Command | What it does |
|---------|--------------|
| `kubectl get deploy <d> -o jsonpath='spec={.spec.replicas} avail={.status.availableReplicas}{"\n"}'` | Desired vs actual |
| `kubectl delete pod <p>` then `kubectl get pods -w` | Watch the ReplicaSet recreate it |
| `kubectl get rs -l app=<n>` | The ReplicaSet keeping N pods alive |
| `kubectl get pod <p> -o jsonpath='{.metadata.ownerReferences[0].kind}'` | Who owns this pod (ReplicaSet) |

---

## 6. Events — the audit trail of every actor

| Command | What it does |
|---------|--------------|
| `kubectl get events --sort-by=.lastTimestamp` | Chronological event trail |
| `kubectl get events -w` | Stream events live (watch a pod's birth) |
| `kubectl get events --field-selector type=Warning` | Just warnings |
| `kubectl get events --field-selector involvedObject.name=<pod>` | Events for one object |

**Map event `REASON`s to the request flow (Demo 4 / Viz 04):**

| REASON | Actor | Step |
|--------|-------|------|
| `ScalingReplicaSet` | Deployment controller | created the ReplicaSet |
| `SuccessfulCreate` (on a ReplicaSet) | ReplicaSet controller | created the Pods |
| `Scheduled` | kube-scheduler | bound pod → node |
| `Pulled` / `Created` / `Started` | kubelet (+ container runtime) | ran the container |

---

## 7. Services, endpoints & DNS (discovery internals)

| Command | What it does |
|---------|--------------|
| `kubectl get svc <n> -o jsonpath='{.spec.clusterIP}'` | The stable virtual IP |
| `kubectl get endpoints <n>` | Live pod IPs behind the Service (match **+** Ready) |
| `kubectl get endpoints <n> -w` | Watch endpoints self-heal as pods churn |
| `kubectl describe svc <n>` | Selector, ports, and Endpoints in one view |
| `kubectl exec <pod> -- getent hosts <svc>` | Resolve a Service name → ClusterIP via CoreDNS |

> **k8s 1.33+ note:** `kubectl get endpoints` prints a deprecation warning (still
> works); prefer `kubectl get endpointslices -l kubernetes.io/service-name=<n>`.

**No endpoints? (Service returns 503 / connection refused):**
```bash
kubectl get endpoints <svc>                 # empty list = nowhere to route
kubectl get pods -l <selector> -o wide      # are there pods? are they Ready?
kubectl get svc <svc> -o jsonpath='{.spec.selector}'   # does selector match the pod labels?
# Causes: no matching pods · pods NotReady (failing probe) · selector/label mismatch
```

---

## 8. API & resource discovery

| Command | What it does |
|---------|--------------|
| `kubectl api-resources` | Every object kind (name, shortname, namespaced, kind) |
| `kubectl api-resources --namespaced=false` | Cluster-scoped kinds (Node, Namespace, PV…) |
| `kubectl explain <kind> --recursive` | Full field tree the apiserver validates against |
| `kubectl get --raw /readyz` | API server health probe |
| `kubectl get pods -A -v=6 2>&1 \| grep https` | See the literal API call `kubectl` makes |

> Back to the verbs and workload commands? See
> [kubectl essentials](01-kubectl-essentials.md).
