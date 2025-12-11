terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.0"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Obtener dinámicamente tu ID de cuenta AWS (para no ponerlo a mano)
data "aws_caller_identity" "current" {}

# ---------------------------
#  RED (VPC Default)
# ---------------------------
# Obtener la VPC por defecto
data "aws_vpc" "default" {
  default = true
}

# Obtener TODAS las subnets de la VPC
data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# Obtener info de cada subnet
data "aws_subnet" "default" {
  for_each = toset(data.aws_subnets.default.ids)
  id       = each.value
}

# Filtrar solo subnets válidas para EKS
locals {
  valid_azs = ["us-east-1a", "us-east-1b", "us-east-1c", "us-east-1d", "us-east-1f"]

  subnets = [
    for subnet_id in data.aws_subnets.default.ids :
    subnet_id
    if contains(local.valid_azs, data.aws_subnet.default[subnet_id].availability_zone)
  ]

  ecr_registry = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.aws_region}.amazonaws.com"
}


# ---------------------------
#  1. ECR: REPOSITORIO
# ---------------------------
resource "aws_ecr_repository" "iot_api" {
  name                 = "iot-suelo-api"
  image_tag_mutability = "MUTABLE"
  force_delete         = true # Permite destruir terraform aunque tenga imágenes

  image_scanning_configuration {
    scan_on_push = true
  }
}

# ---------------------------
#  2. RDS: BASE DE DATOS
# ---------------------------
resource "aws_security_group" "db_sg" {
  name        = "iot-db-sg"
  description = "Permite acceso al RDS desde la VPC"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = [data.aws_vpc.default.cidr_block]
  }
}

resource "aws_db_subnet_group" "iot_db_subnets" {
  name       = "iot-db-subnet-group"
  subnet_ids = local.subnets
}

resource "aws_db_instance" "iot_db" {
  identifier        = "iot-suelo-db"
  engine            = "postgres"
  #engine_version    = "16.1" # Fijamos una versión estable
  instance_class    = "db.t3.micro"
  allocated_storage = 20
  storage_type      = "gp2"
  
  db_name  = "iot_suelo"
  username = var.db_username
  password = var.db_password
  port     = 5432

  db_subnet_group_name   = aws_db_subnet_group.iot_db_subnets.name
  vpc_security_group_ids = [aws_security_group.db_sg.id]
  
  publicly_accessible    = true # Para que sea fácil depurar (opcional)
  skip_final_snapshot    = true
}

# ---------------------------
#  3. EKS: CLUSTER KUBERNETES
# ---------------------------
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "20.8.5"

  cluster_name    = var.cluster_name
  cluster_version = "1.29"
  vpc_id          = data.aws_vpc.default.id
  subnet_ids      = local.subnets

  cluster_endpoint_public_access           = true
  enable_cluster_creator_admin_permissions = true

  create_kms_key              = false
  create_cloudwatch_log_group = false

  # FIX IMPORTANTE
  cluster_encryption_config = []

  eks_managed_node_groups = {
    default = {
      min_size      = 1
      max_size      = 3
      desired_size  = 2
      instance_types = ["t3.micro"]
    }
  }
}


# ---------------------------
#  4. DOCKER BUILD & PUSH
# ---------------------------
resource "null_resource" "build_and_push_image" {
  depends_on = [aws_ecr_repository.iot_api]

  triggers = {
    always_run = timestamp()
  }

  provisioner "local-exec" {
    working_dir = "${path.module}/.."
    interpreter = ["PowerShell", "-Command"]

    command = <<EOT
      $ErrorActionPreference = "Stop"

      # Ya estás logueado en ECR (lo hicimos a mano),
      # así que aquí SOLO construimos, tageamos y hacemos push.

      docker build -t iot-suelo-api:latest .
      docker tag iot-suelo-api:latest ${aws_ecr_repository.iot_api.repository_url}:latest
      docker push ${aws_ecr_repository.iot_api.repository_url}:latest
    EOT
  }
}


# ---------------------------
#  PROVEEDOR KUBERNETES
# ---------------------------
data "aws_eks_cluster" "this" {
  name       = module.eks.cluster_name
  depends_on = [module.eks]
}

data "aws_eks_cluster_auth" "this" {
  name       = module.eks.cluster_name
  depends_on = [module.eks]
}

provider "kubernetes" {
  host                   = data.aws_eks_cluster.this.endpoint
  cluster_ca_certificate = base64decode(data.aws_eks_cluster.this.certificate_authority[0].data)
  token                  = data.aws_eks_cluster_auth.this.token
}

# ---------------------------
#  5. DEPLOYMENT & SERVICE
# ---------------------------
resource "kubernetes_deployment" "iot_api" {
  depends_on = [
    module.eks,
    aws_db_instance.iot_db,
    null_resource.build_and_push_image
  ]

  metadata {
    name = "iot-api-deployment"
    labels = {
      app = "iot-api"
    }
  }

  spec {
    replicas = 2
    selector {
      match_labels = {
        app = "iot-api"
      }
    }
    template {
      metadata {
        labels = {
          app = "iot-api"
        }
      }
      spec {
        container {
          name  = "iot-api-container"
          image = "${aws_ecr_repository.iot_api.repository_url}:latest"
          
          # Política para forzar descarga de imagen nueva
          image_pull_policy = "Always"

          port {
            container_port = 8000
          }

          env {
            name  = "DB_USER"
            value = var.db_username
          }
          env {
            name  = "DB_PASSWORD"
            value = var.db_password
          }
          env {
            name  = "DB_HOST"
            value = aws_db_instance.iot_db.address
          }
          env {
            name  = "DB_NAME"
            value = "iot_suelo"
          }
        }
      }
    }
  }
}

resource "kubernetes_service" "iot_api_svc" {
  depends_on = [kubernetes_deployment.iot_api]
  metadata {
    name = "iot-api-service"
  }
  spec {
    selector = {
      app = "iot-api"
    }
    # Esto crea un Classic Load Balancer en AWS automáticamente
    type = "LoadBalancer"
    port {
      port        = 80
      target_port = 8000
    }
  }
}