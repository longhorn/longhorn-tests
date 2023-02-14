terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
    }
  }
}

provider "aws" {
  region = var.aws_region
  access_key = var.lh_aws_access_key
  secret_key = var.lh_aws_secret_key
}

resource "random_string" "random_suffix" {
  length           = 8
  special          = false
  lower            = true
  upper            = false
}

locals {
  cluster_name = "${var.test_name}-${random_string.random_suffix.id}-cluster"
  resource_name_prefix = "${var.test_name}-${random_string.random_suffix.id}"
}

module "vpc" {
  source = "terraform-aws-modules/vpc/aws"
  name = "${local.resource_name_prefix}-vpc"
  cidr = "10.0.0.0/16"
  azs             = ["${var.aws_region}a", "${var.aws_region}c"]
  public_subnets  = ["10.0.1.0/24", "10.0.2.0/24"]
  private_subnets  = ["10.0.101.0/24", "10.0.102.0/24"]
  enable_nat_gateway     = true
  single_nat_gateway     = true
  one_nat_gateway_per_az = false
  map_public_ip_on_launch = true

  tags = {
    Name = "${local.resource_name_prefix}-vpc"
    Owner = "longhorn-infra"
  }
}

# EKS Terraform - IAM Role for K8s Cluster (Control Plane)
resource "aws_iam_role" "eks_service_role" {
  name = "${local.resource_name_prefix}-eks-service-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "eks.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "eks_iam_policy_attachment" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
  role       = aws_iam_role.eks_service_role.name
}

# EKS Terraform - IAM Role for EKS Worker Nodes
resource "aws_iam_role" "eks_node_role" {
  name = "${local.resource_name_prefix}-eks-node-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ec2.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "worker_node_policy_attachment" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
  role       = aws_iam_role.eks_node_role.name
}

resource "aws_iam_role_policy_attachment" "cni_policy_attachment" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
  role       = aws_iam_role.eks_node_role.name
}

resource "aws_iam_role_policy_attachment" "ecr_readonly_policy_attachment" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
  role       = aws_iam_role.eks_node_role.name
}

# EKS Terraform - Cluster
resource "aws_eks_cluster" "eks_cluster" {
  depends_on = [ aws_iam_role_policy_attachment.eks_iam_policy_attachment ]
  name     = local.cluster_name
  role_arn = aws_iam_role.eks_service_role.arn
  vpc_config {
    subnet_ids = module.vpc.public_subnets
  }

  tags = {
    Name = local.cluster_name
    Owner = "longhorn-infra"
  }
}

# EKS Terraform - Creating the EKS Node Group
resource "aws_eks_node_group" "node_group" {
  depends_on = [
    aws_iam_role_policy_attachment.worker_node_policy_attachment,
    aws_iam_role_policy_attachment.cni_policy_attachment,
    aws_iam_role_policy_attachment.ecr_readonly_policy_attachment
  ]
  cluster_name    = aws_eks_cluster.eks_cluster.name
  node_group_name = "${local.resource_name_prefix}-ng"
  node_role_arn   = aws_iam_role.eks_node_role.arn
  subnet_ids      = module.vpc.public_subnets
  ami_type       = var.arch == "amd64" ? "AL2_x86_64" : "AL2_ARM_64"
  capacity_type  = "ON_DEMAND"
  instance_types = [var.arch == "amd64" ? "t2.xlarge" : "a1.xlarge"]
  disk_size      = 40
  scaling_config {
    desired_size = 3
    max_size     = 6
    min_size     = 1
  }
  update_config {
    max_unavailable = 1
  }
  tags = {
    "k8s.io/cluster-autoscaler/${local.cluster_name}" = "owned"
    "k8s.io/cluster-autoscaler/enabled" = "true"
    Name = "${local.resource_name_prefix}-ng"
    Owner = "longhorn-infra"
  }
}

data "aws_eks_cluster_auth" "eks_cluster_auth" {
  depends_on = [ aws_eks_cluster.eks_cluster ]
  name = local.cluster_name
}
