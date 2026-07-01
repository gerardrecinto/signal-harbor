terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.0"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.0"
    }
  }
}

provider "aws" {
  region = var.region
}

locals {
  tags = {
    project     = "signal-harbor"
    environment = var.environment
    managed-by  = "terraform"
  }
}

data "aws_availability_zones" "available" {
  state = "available"
}

# ---------------------------------------------------------------------------
# VPC
# ---------------------------------------------------------------------------
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "signalharbor-${var.environment}"
  cidr = var.vpc_cidr

  azs             = slice(data.aws_availability_zones.available.names, 0, 3)
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]

  enable_nat_gateway   = true
  single_nat_gateway   = var.environment != "prod"
  enable_dns_hostnames = true
  enable_dns_support   = true

  public_subnet_tags = {
    "kubernetes.io/cluster/signalharbor-${var.environment}" = "shared"
    "kubernetes.io/role/elb"                                = "1"
  }

  private_subnet_tags = {
    "kubernetes.io/cluster/signalharbor-${var.environment}" = "shared"
    "kubernetes.io/role/internal-elb"                       = "1"
  }

  tags = merge(local.tags, {
    "kubernetes.io/cluster/signalharbor-${var.environment}" = "shared"
  })
}

# ---------------------------------------------------------------------------
# EKS
# ---------------------------------------------------------------------------
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.0"

  cluster_name    = "signalharbor-${var.environment}"
  cluster_version = "1.29"

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  cluster_endpoint_public_access  = true
  cluster_endpoint_private_access = true

  enable_cluster_creator_admin_permissions = true

  eks_managed_node_groups = {
    default = {
      instance_types = ["t3.medium"]
      min_size       = 1
      max_size       = var.node_max
      desired_size   = var.node_desired

      labels = local.tags
      tags   = local.tags
    }
  }

  tags = local.tags
}

# ---------------------------------------------------------------------------
# RDS Security Group
# ---------------------------------------------------------------------------
resource "aws_security_group" "rds" {
  name        = "signalharbor-${var.environment}-rds"
  description = "Allow PostgreSQL access from EKS nodes"
  vpc_id      = module.vpc.vpc_id

  ingress {
    description     = "PostgreSQL from EKS nodes"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [module.eks.node_security_group_id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.tags, { Name = "signalharbor-${var.environment}-rds" })
}

resource "aws_db_subnet_group" "signalharbor" {
  name        = "signalharbor-${var.environment}"
  description = "Subnet group for Signal Harbor RDS"
  subnet_ids  = module.vpc.private_subnets

  tags = local.tags
}

# ---------------------------------------------------------------------------
# RDS PostgreSQL 16
# ---------------------------------------------------------------------------
resource "aws_db_instance" "signalharbor" {
  identifier        = "signalharbor-${var.environment}"
  engine            = "postgres"
  engine_version    = "16.3"
  instance_class    = var.db_instance_class
  allocated_storage = var.db_storage_gb
  storage_encrypted = true

  db_name  = "signalharbor"
  username = var.db_username
  password = var.db_password

  db_subnet_group_name   = aws_db_subnet_group.signalharbor.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  multi_az            = var.environment == "prod"
  publicly_accessible = false

  # Remove prevent_destroy for non-prod environments
  skip_final_snapshot       = var.environment != "prod"
  final_snapshot_identifier = var.environment == "prod" ? "signalharbor-${var.environment}-final" : null

  backup_retention_period = var.environment == "prod" ? 7 : 1
  deletion_protection     = var.environment == "prod"

  tags = local.tags

  lifecycle {
    prevent_destroy = true
  }
}

# ---------------------------------------------------------------------------
# ElastiCache Security Group
# ---------------------------------------------------------------------------
resource "aws_security_group" "redis" {
  name        = "signalharbor-${var.environment}-redis"
  description = "Allow Redis access from EKS nodes"
  vpc_id      = module.vpc.vpc_id

  ingress {
    description     = "Redis from EKS nodes"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [module.eks.node_security_group_id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.tags, { Name = "signalharbor-${var.environment}-redis" })
}

resource "aws_elasticache_subnet_group" "signalharbor" {
  name        = "signalharbor-${var.environment}"
  description = "Subnet group for Signal Harbor ElastiCache"
  subnet_ids  = module.vpc.private_subnets

  tags = local.tags
}

# ---------------------------------------------------------------------------
# ElastiCache Redis 7
# ---------------------------------------------------------------------------
resource "aws_elasticache_replication_group" "signalharbor" {
  replication_group_id = "signalharbor-${var.environment}"
  description          = "Signal Harbor risk summary cache"

  node_type                  = var.redis_node_type
  num_cache_clusters         = var.environment == "prod" ? 2 : 1
  automatic_failover_enabled = var.environment == "prod"
  multi_az_enabled           = var.environment == "prod"

  port                 = 6379
  parameter_group_name = "default.redis7"

  subnet_group_name  = aws_elasticache_subnet_group.signalharbor.name
  security_group_ids = [aws_security_group.redis.id]

  at_rest_encryption_enabled = true
  transit_encryption_enabled = true

  tags = local.tags
}

# ---------------------------------------------------------------------------
# Kubernetes provider — auth via EKS cluster
# ---------------------------------------------------------------------------
provider "kubernetes" {
  host                   = module.eks.cluster_endpoint
  cluster_ca_certificate = base64decode(module.eks.cluster_certificate_authority_data)

  exec {
    api_version = "client.authentication.k8s.io/v1beta1"
    command     = "aws"
    args        = ["eks", "get-token", "--cluster-name", module.eks.cluster_name, "--region", var.region]
  }
}

# ---------------------------------------------------------------------------
# Application module
# ---------------------------------------------------------------------------
module "app" {
  source = "../modules/k8s-app"

  namespace    = "signalharbor-${var.environment}"
  image        = "ghcr.io/gerardrecinto/signal-harbor:${var.app_version}"
  replicas     = var.environment == "prod" ? 3 : 2
  app_port     = 80
  ingress_host = var.ingress_host

  api_key      = var.api_key
  database_url = "postgresql://${var.db_username}:${var.db_password}@${aws_db_instance.signalharbor.address}:5432/signalharbor"
  redis_url    = "rediss://${aws_elasticache_replication_group.signalharbor.primary_endpoint_address}:6379"

  depends_on = [module.eks]
}
