# Talos Kubernetes Cluster Provisioning with Longhorn

This guide provides step-by-step instructions to provision a Kubernetes cluster using Talos and set up Longhorn for distributed storage.

---

## Table of Contents

- [Talos Kubernetes Cluster Provisioning with Longhorn](#talos-kubernetes-cluster-provisioning-with-longhorn)
  - [Table of Contents](#table-of-contents)
  - [Prerequisites](#prerequisites)
  - [How to Change Parameters](#how-to-change-parameters)
  - [Commands for Provisioning a Cluster](#commands-for-provisioning-a-cluster)
    - [Option 1: Using Terraform](#option-1-using-terraform)
    - [Option 2: Using `longhorn-tests` Repository](#option-2-using-longhorn-tests-repository)
  - [Commands for Destroying a Cluster](#commands-for-destroying-a-cluster)
  - [How to Bootstrap a Longhorn Cluster](#how-to-bootstrap-a-longhorn-cluster)
    - [Step 1: Create Namespace and Apply Security Labels](#step-1-create-namespace-and-apply-security-labels)
    - [Step 2: Deploy Longhorn](#step-2-deploy-longhorn)

---

## Prerequisites

Before proceeding, ensure the following requirements are met:

- **Install `talosctl`**  
  - Download and install `talosctl` by following the official [installation guide](https://www.talos.dev/v1.9/talos-guides/install/).
  - Make sure `talosctl` is accessible from your system's PATH.

---

## How to Change Parameters

The cluster parameters can be customized by modifying the `variables.tf` file. Below are the key parameters you can adjust:

- **`aws_region`**: The AWS region where resources will be created.
- **`lh_aws_instance_count_controlplane`**: Number of control plane instances.
- **`lh_aws_instance_count_worker`**: Number of worker instances.
- **`lh_aws_instance_type_controlplane`**: Instance type for control plane nodes.
- **`lh_aws_instance_type_worker`**: Instance type for worker nodes.

---

## Commands for Provisioning a Cluster

### Option 1: Using Terraform

To provision the cluster using Terraform, run the following commands:

```bash
terraform init
terraform apply -auto-approve
```

### Option 2: Using `longhorn-tests` Repository

Alternatively, you can build the Talos cluster by cloning the `longhorn-tests` repository and running the setup script:

```bash
git clone https://github.com/longhorn/longhorn-tests
cd longhorn-tests
TF_VAR_k8s_distro_name=k3s LONGHORN_TEST_CLOUDPROVIDER=aws DISTRO=talos ./pipelines/utilities/terraform_setup.sh
```

---

## Commands for Destroying a Cluster

To destroy the cluster and remove all associated resources, execute:

```bash
terraform destroy -auto-approve
```

---

## How to Bootstrap a Longhorn Cluster

### Step 1: Create Namespace and Apply Security Labels

Run the following commands to create the `longhorn-system` namespace and apply necessary security labels:

```bash
kubectl create ns longhorn-system
kubectl label ns longhorn-system pod-security.kubernetes.io/enforce=privileged
kubectl label ns longhorn-system pod-security.kubernetes.io/enforce-version=latest
kubectl label ns longhorn-system pod-security.kubernetes.io/audit=privileged
kubectl label ns longhorn-system pod-security.kubernetes.io/audit-version=latest
kubectl label ns longhorn-system pod-security.kubernetes.io/warn=privileged
kubectl label ns longhorn-system pod-security.kubernetes.io/warn-version=latest
```

### Step 2: Deploy Longhorn

Deploy Longhorn into the cluster by running the following command:

```bash
kubectl apply -f https://raw.githubusercontent.com/longhorn/longhorn/master/deploy/longhorn.yaml
```
