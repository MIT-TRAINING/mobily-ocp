# Guide to Set Up a 3-Node OpenShift Container Platform (OCP) Cluster on AWS from Scratch

> **This course already has a live, proven cluster — you likely don't need Steps
> 1–7.** A working provisioning kit lives at
> [`labs/setup/ocp-cluster/`](../ocp-cluster/README.md) and has already stood up
> `mobily-ocp-training` (OCP 4.18, account `bigdata-training`, region
> `ap-south-1`, base domain `ocp.supercloudlabs.com`). Participants and
> instructors connect to it from the **`ocp-lab-trainer-box`** VM, which comes
> pre-configured with `oc`/`kubectl` and a working kubeconfig — no install
> needed. See **[Connecting from the `ocp-lab-trainer-box` VM](#connecting-from-the-ocp-lab-trainer-box-vm)**
> below, validated against the live cluster on 2026-07-16.
>
> The rest of this document is a **generic, from-scratch walkthrough** — useful
> for teaching how IPI installs work, or for standing up a *separate* cluster —
> but its cluster name (`ocpdemo`), domain (`example.com`), and instance sizing
> (`m5.xlarge`) are illustrative placeholders, not this course's real values.
>
> **Test coverage (2026-07-16):** Prerequisites through Step 6 were run for
> real on a disposable Ubuntu 24.04 EC2 VM (launched, exercised, and
> terminated the same session) — `apt-get` prereqs, AWS CLI install, SSH
> keygen, `openshift-install`/`oc` download & extraction, and
> `install-config.yaml` all confirmed working, including a real
> `openshift-install create manifests` run that accepted the file's schema.
> Step 7 (actual cluster creation) was **not** run — it would provision a
> second full OCP cluster (~40–45 min, real cost) and was out of scope for
> this pass; Steps 8+ (login/verify/console) are instead validated against
> the course's real cluster in [Connecting from the `ocp-lab-trainer-box`
> VM](#connecting-from-the-ocp-lab-trainer-box-vm).

## Architecture

``` text
                    Internet
                        |
               AWS Route53 (Optional)
                        |
                +----------------+
                | AWS LoadBalancer|
                +----------------+
                        |
          ------------------------------
          |            |               |
      Master-1     Master-2       Master-3
      (Control)    (Control)      (Control)

             Worker-1      Worker-2      Worker-3
```

For a true 3-node cluster, there are two options:

### Option A (Recommended for Production)

-   3 Control Plane nodes
-   2 or more Worker nodes
-   Minimum 5--6 EC2 instances

### Option B (Compact Cluster)

Only three nodes, each acting as both:

-   Control Plane
-   Worker

Ideal for training, demos, and labs.

------------------------------------------------------------------------

# Prerequisites

## AWS Account

Administrator permissions (or equivalent) for:

-   EC2
-   IAM
-   Route53
-   VPC
-   ELB
-   EBS
-   S3

## Local Machine

This is the machine that will *run the installer* (`openshift-install`) — for
this course that's the operator's own machine driving
`labs/setup/ocp-cluster/`, **not** the `ocp-lab-trainer-box` VM (which only
connects to the finished cluster and intentionally has no installer or AWS CLI
on it).

Install (RHEL/CentOS/Fedora):

``` bash
sudo yum install -y git curl wget jq unzip
```

On Ubuntu/Debian (e.g. if you provision from a machine like the trainer box):

``` bash
sudo apt-get update && sudo apt-get install -y git curl wget jq unzip
```

On macOS (via [Homebrew](https://brew.sh)):

``` bash
brew install git curl wget jq
```

(`unzip` ships with macOS already.)

## Install AWS CLI

Linux:

``` bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o awscliv2.zip
unzip awscliv2.zip
sudo ./aws/install

aws configure
aws sts get-caller-identity
```

macOS:

``` bash
brew install awscli
# or the official .pkg installer:
# curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o AWSCLIV2.pkg
# sudo installer -pkg AWSCLIV2.pkg -target /

aws configure
aws sts get-caller-identity
```

------------------------------------------------------------------------

# Step 1 -- Create SSH Key

``` bash
ssh-keygen -t ed25519
```

or

``` bash
ssh-keygen -t rsa
```

------------------------------------------------------------------------

# Step 2 -- Download OpenShift Tools

Download from the [OpenShift mirror](https://mirror.openshift.com/pub/openshift-v4/clients/ocp/latest/):

-   openshift-install
-   oc CLI

Linux:

``` bash
tar -xvf openshift-install-linux.tar.gz
sudo mv openshift-install /usr/local/bin/

tar -xvf openshift-client-linux.tar.gz
sudo mv oc kubectl /usr/local/bin/
```

macOS — download the `-mac.tar.gz` builds instead (an `-mac-arm64.tar.gz`
build is also published for Apple Silicon):

``` bash
tar -xvf openshift-install-mac.tar.gz
sudo mv openshift-install /usr/local/bin/

tar -xvf openshift-client-mac.tar.gz
sudo mv oc kubectl /usr/local/bin/
```

Or via Homebrew (`oc` only — `openshift-install` isn't packaged in brew):

``` bash
brew install openshift-cli
```

On first run, macOS Gatekeeper may block the unsigned binaries. Clear the
quarantine flag rather than disabling Gatekeeper system-wide:

``` bash
xattr -d com.apple.quarantine /usr/local/bin/openshift-install /usr/local/bin/oc /usr/local/bin/kubectl 2>/dev/null
```

Verify:

``` bash
openshift-install version
oc version
```

------------------------------------------------------------------------

# Step 3 -- Download Red Hat Pull Secret

Download the pull secret from the Red Hat Hybrid Cloud Console and save
it as:

``` text
pull-secret.txt
```

------------------------------------------------------------------------

# Step 4 -- Create Installation Directory

``` bash
mkdir ocp-cluster
cd ocp-cluster
```

------------------------------------------------------------------------

# Step 5 -- Generate install-config.yaml

``` bash
openshift-install create install-config
```

Provide:

-   Platform: AWS
-   Region: ap-south-1
-   Base Domain: example.com
-   Cluster Name: ocpdemo
-   Pull Secret
-   SSH Public Key

------------------------------------------------------------------------

# Step 6 -- Configure Compact Cluster

Edit `install-config.yaml`:

``` yaml
apiVersion: v1
baseDomain: example.com

metadata:
  name: ocpdemo

compute:
- name: worker
  replicas: 0

controlPlane:
  name: master
  replicas: 3

platform:
  aws:
    region: ap-south-1

pullSecret: "<pull-secret>"

sshKey: |
  ssh-rsa AAAAB3...
```

Important:

``` yaml
compute:
  replicas: 0
```

> **Hand-editing gotcha (confirmed by testing this template on a live VM):**
> the real pull secret is itself a JSON blob full of double quotes
> (`{"auths":{"cloud.openshift.com":{"auth":"..."}}}`), and `pullSecret`
> here is a double-quoted YAML string — so every inner `"` must be escaped
> as `\"`, e.g. `pullSecret: "{\"auths\":{...}}"`. Pasting the raw JSON
> unescaped breaks YAML parsing with `expected <block end>, but found
> <scalar>`. Prefer letting **Step 5's interactive wizard** write the file
> for you (it escapes this correctly); only hand-edit if you're changing
> `compute.replicas` afterward, and even then, edit around the existing
> `pullSecret` line rather than retyping it.

------------------------------------------------------------------------

# Step 7 -- Create the Cluster

``` bash
openshift-install create cluster
```

Installation typically takes **35--45 minutes**.

The installer automatically provisions:

-   VPC
-   Subnets
-   Security Groups
-   IAM Roles
-   EC2 Instances
-   Route53 Records
-   Load Balancers
-   EBS Volumes

------------------------------------------------------------------------

# Step 8 -- Login

``` bash
oc login https://api.ocpdemo.example.com:6443
```

Verify:

``` bash
oc get nodes
```

> For this course's actual cluster, skip the `oc login` step — the
> `ocp-lab-trainer-box` VM already has a kubeconfig authenticated as
> `kube:admin` against `https://api.mobily-ocp-training.ocp.supercloudlabs.com:6443`.
> See [Connecting from the `ocp-lab-trainer-box` VM](#connecting-from-the-ocp-lab-trainer-box-vm).

------------------------------------------------------------------------

# Connecting from the `ocp-lab-trainer-box` VM

Validated end-to-end on 2026-07-16 against the live `mobily-ocp-training`
cluster.

## 1. SSH to the trainer box

``` bash
ssh -i labs/setup/ocp-training-ubuntu.pem ubuntu@13.205.136.90
```

The instance (`i-0cab866786363ad75`, Ubuntu 24.04 LTS, account
`bigdata-training` / `ap-south-1`) uses the same key pair
(`ocp-training-ubuntu`) as `labs/setup/connect.sh`, but note that script's
hardcoded Elastic IP (`35.154.98.243`) points at a different, no-longer-running
instance — connect with the IP above instead, or update `connect.sh` if you
want a single script for both.

## 2. `oc` / `kubectl` are already installed — nothing else is

``` bash
oc version --client       # Client Version: 4.22.0
kubectl version --client  # Client Version: v1.35.2
```

By design, the trainer box does **not** have `openshift-install`, the `aws`
CLI, or `unzip` — it's a connect/demo endpoint, not an install host.
Provisioning happens separately via `labs/setup/ocp-cluster/` (run from the
operator's own machine).

## 3. The kubeconfig is already pre-loaded and authenticated

`~/.kube/config` on the box already has a `kube:admin` context for the real
cluster — no login required:

``` bash
oc whoami
# kube:admin
oc whoami --show-server
# https://api.mobily-ocp-training.ocp.supercloudlabs.com:6443
```

Multiple contexts are pre-populated (`kube:admin`, per-learner accounts like
`learner26`, plus an unrelated Developer Sandbox and `minikube` context from
other course modules) — check `kubectl config get-contexts` and
`oc config use-context <name>` if you need to switch.

## 4. Verify the cluster

``` bash
oc get nodes
```

Confirmed output (9 nodes, all `Ready`):

```
NAME                                         STATUS   ROLES                  VERSION
ip-10-0-20-123.ap-south-1.compute.internal   Ready    worker                 v1.31.14
ip-10-0-23-236.ap-south-1.compute.internal   Ready    control-plane,master   v1.31.14
ip-10-0-31-179.ap-south-1.compute.internal   Ready    worker                 v1.31.14
ip-10-0-44-62.ap-south-1.compute.internal    Ready    worker                 v1.31.14
ip-10-0-61-153.ap-south-1.compute.internal   Ready    control-plane,master   v1.31.14
ip-10-0-62-79.ap-south-1.compute.internal    Ready    worker                 v1.31.14
ip-10-0-66-28.ap-south-1.compute.internal    Ready    worker                 v1.31.14
ip-10-0-68-94.ap-south-1.compute.internal    Ready    worker                 v1.31.14
ip-10-0-93-108.ap-south-1.compute.internal   Ready    control-plane,master   v1.31.14
```

``` bash
oc get co
```

Confirmed: all sampled ClusterOperators `AVAILABLE=True`, `DEGRADED=False`, on
version `4.18.45`.

## 5. Console

``` bash
oc get route console -n openshift-console -o jsonpath='{.spec.host}'
# console-openshift-console.apps.mobily-ocp-training.ocp.supercloudlabs.com
```

Console: `https://console-openshift-console.apps.mobily-ocp-training.ocp.supercloudlabs.com`
— login as `kubeadmin` (password in `labs/setup/ocp-cluster/cluster/auth/kubeadmin-password`,
git-ignored) or as a per-learner account.

------------------------------------------------------------------------

# Step 9 -- Verify Cluster Operators

``` bash
oc get co
```

Expected:

-   Available=True
-   Progressing=False
-   Degraded=False

------------------------------------------------------------------------

# Step 10 -- Verify Pods

``` bash
oc get pods -A
```

Core components should include:

-   console
-   ingress
-   etcd
-   monitoring
-   authentication
-   dns

------------------------------------------------------------------------

# Step 11 -- Access OpenShift Console

    https://console-openshift-console.apps.ocpdemo.example.com

Login using:

-   Username: kubeadmin
-   Password: Generated during installation

------------------------------------------------------------------------

# Useful Commands

``` bash
oc get nodes
oc get projects
oc new-project demo
oc new-app nginx
oc expose svc/nginx
oc get routes
```

------------------------------------------------------------------------

# Recommended Sizing

  Resource        Recommendation
  --------------- ---------------------------------------------
  Nodes           3
  Instance Type   m5.xlarge (minimum), m5.2xlarge recommended
  CPU             4--8 vCPU
  Memory          16--32 GB
  Disk            120 GB gp3
  Region          ap-south-1

> This course's actual live cluster uses different (cheaper) sizing —
> `t3a.xlarge` masters + `t3a.large` workers, 6 workers currently — see
> `labs/setup/ocp-cluster/cluster.env` for the values actually driving it.

------------------------------------------------------------------------

# AWS Resources Created

-   VPC
-   Subnets
-   Internet Gateway
-   Route Tables
-   Security Groups
-   IAM Roles
-   EC2 Instances
-   EBS Volumes
-   Elastic Load Balancers
-   Route53 Records

------------------------------------------------------------------------

# Estimated Monthly Cost (24×7)

  Resource           Approx. Cost (USD)
  ---------------- --------------------
  EC2                          420--450
  EBS                            30--50
  Load Balancers                 25--40
  Miscellaneous                  10--30
  **Total**                **485--570**

------------------------------------------------------------------------

# Training Recommendations

-   Deploy a compact 3-node cluster.
-   Use `m5.2xlarge` instances with 120 GB gp3 storage.
-   Enable the integrated registry and monitoring.
-   Demonstrate Operators, Routes, SCCs, RBAC, StorageClasses,
    monitoring, logging, rolling updates, and troubleshooting.
