# OpenShift Training — Ubuntu VM Access Details

EC2 instance provisioned for the OpenShift Container Platform training.

> ⚠️ **The private key `ocp-training-ubuntu.pem` in this folder is a credential.**
> It is git-ignored and must **never** be committed, emailed, or shared in plain
> text. Anyone with this file can SSH into the VM.

## Instance

| Property | Value |
|----------|-------|
| Name tag | `ocp-training-ubuntu` |
| Instance ID | `i-01a4cc9b471fd3525` |
| Type | `t3.large` (2 vCPU · 8 GiB RAM) |
| OS | Ubuntu 24.04 LTS (Noble) — AMI `ami-006f82a1d5a27da54` |
| Storage | 50 GB gp3 root volume (deletes on termination) |
| Region / AZ | `ap-south-1` / `ap-south-1a` |
| Public IP (Elastic) | **`35.154.98.243`** (static) |
| Private IP | `172.31.46.84` |
| Default user | `ubuntu` |
| AWS account | `486036174736` (profile `openshift-training`) |

## Installed tooling

| Tool | Version | Notes |
|------|---------|-------|
| Podman | 4.9.3 | rootless-enabled for `ubuntu` |
| Buildah | 1.33.7 | image builder (installed with Podman) |
| Docker Engine | 29.6.0 | `ubuntu` is in the `docker` group (no `sudo` needed) |
| Docker Compose / Buildx | plugins | `docker compose`, `docker buildx` |
| oc (OpenShift CLI) | 4.22.0 | in `/usr/local/bin` |
| kubectl | 1.35.2 | in `/usr/local/bin` |
| helm | 4.2.2 | in `/usr/local/bin` |

Both `podman` and `docker` work for the `ubuntu` user without `sudo`. Bash
completions for `oc`/`kubectl`/`helm` and a `k` alias for `kubectl` are enabled
via `/etc/profile.d/ocp-tools-completion.sh` (active on next login).

## Network / security

| Property | Value |
|----------|-------|
| Security group | `sg-03eb227596eb67d3b` (`ocp-training-ubuntu-sg`) |
| VPC / Subnet | `vpc-041787c748f619e49` / `subnet-0a1e22b94a8c510ff` |
| SSH ingress | TCP 22 from **101.0.63.160/32** only |
| Key pair | `ocp-training-ubuntu` |
| Private key | `labs/setup/ocp-training-ubuntu.pem` (chmod 400) |
| Elastic IP | `35.154.98.243` (alloc `eipalloc-0a8619d12f9ca5b92`) |

> **Note:** An **Elastic IP** is associated, so the address `35.154.98.243` is
> **stable** across stop/start. (The EIP incurs a small charge only while the
> instance is *stopped*; it is free while the instance is running.)

## Connect

```bash
ssh -i labs/setup/ocp-training-ubuntu.pem ubuntu@35.154.98.243
```

Or use the helper script from the repo root:

```bash
./labs/setup/connect.sh
```

### If your public IP changes
SSH is locked to `101.0.63.160/32`. If you connect from a new network, add your
new IP:

```bash
MY_IP=$(curl -s https://checkip.amazonaws.com)
aws ec2 authorize-security-group-ingress --profile openshift-training --region ap-south-1 \
  --group-id sg-03eb227596eb67d3b --protocol tcp --port 22 --cidr ${MY_IP}/32
```

## Lifecycle management

```bash
P="--profile openshift-training --region ap-south-1"

# Stop (stops compute billing; EBS storage still billed; public IP will change)
aws ec2 stop-instances  $P --instance-ids i-01a4cc9b471fd3525

# Start again
aws ec2 start-instances $P --instance-ids i-01a4cc9b471fd3525

# Check status
aws ec2 describe-instances $P --instance-ids i-01a4cc9b471fd3525 \
  --query 'Reservations[0].Instances[0].State.Name' --output text
```

## Teardown (when training is finished)

This permanently deletes the VM and its storage:

```bash
P="--profile openshift-training --region ap-south-1"
aws ec2 terminate-instances $P --instance-ids i-01a4cc9b471fd3525
aws ec2 wait instance-terminated $P --instance-ids i-01a4cc9b471fd3525
aws ec2 release-address $P --allocation-id eipalloc-0a8619d12f9ca5b92   # free the Elastic IP
aws ec2 delete-security-group $P --group-id sg-03eb227596eb67d3b
aws ec2 delete-key-pair $P --key-name ocp-training-ubuntu
rm -f labs/setup/ocp-training-ubuntu.pem
```

## Cost (approximate, ap-south-1, on-demand)

- `t3.large`: ~$0.0832/hour (~$60/month if left running 24×7)
- 50 GB gp3: ~$4.50/month
- Elastic IP: free while attached to a *running* instance; ~$0.005/hour only
  while the instance is *stopped*

**Stop the instance when not in use** to avoid the compute charge.
