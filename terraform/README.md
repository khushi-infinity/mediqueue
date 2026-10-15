# Terraform — AWS Infrastructure

This directory provisions the AWS network and Kubernetes control plane that the
MediQueue Helm chart deploys onto. It does not deploy the application.

## What It Creates

| Resource | Details |
| --- | --- |
| VPC | `10.52.0.0/16`, DNS hostnames enabled |
| Public subnets | Two, tagged for internet-facing load balancers |
| Private subnets | Two, tagged for internal load balancers |
| NAT gateway | One (single NAT keeps the classroom cost down) |
| EKS cluster | Managed control plane, audit/auth/api logging enabled |
| Node group | Managed, `AL2023_x86_64_STANDARD`, 1–3 × `t3.medium`, 30 GB disk |
| EBS CSI | IRSA role so the cluster can bind `PersistentVolumeClaims` |
| Storage class | `k8s/storage-aws.yaml` provides an encrypted `gp3` class |

Workers run in private subnets. The EKS API is public but restricted to the
CIDRs in `api_allowed_cidrs`; the `0.0.0.0/0` default is rejected by a variable
validation rule.

## Usage

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars   # then set your own public IP/CIDR
terraform init
terraform plan
terraform apply
```

By default only `terraform fmt -check`, `init -backend=false` and `validate` are
run in CI, because they need no AWS account and create no billable resources.

Point `kubectl` at the new cluster with the `configure_kubectl` output:

```bash
aws eks update-kubeconfig --region ap-south-1 --name mediqueue-cluster
kubectl apply -f ../k8s/storage-aws.yaml
helm upgrade --install mediqueue ../helm/mediqueue -n mediqueue --create-namespace \
  -f ../helm/mediqueue/values-aws.yaml
```

Then replace `ingress.host` and `ingress.tlsSecret` with a real domain and
certificate. `values-aws.yaml` switches the bundled Prometheus and Grafana
Services from NodePort to ClusterIP, which is the right default behind an
Ingress or an internal load balancer.

## Cost Control

The managed node group, NAT gateway and control plane all bill hourly. Destroy
when the demonstration is finished and confirm the VPC and cluster are gone:

```bash
terraform destroy
aws eks list-clusters --region ap-south-1
```

## Scope

This is a teaching deployment, not a production landing zone: there is one NAT
gateway, no VPC flow logs, no private API endpoint, no backup policy and no
secrets manager. A real deployment would use a managed database instead of the
in-cluster PostgreSQL StatefulSet.
