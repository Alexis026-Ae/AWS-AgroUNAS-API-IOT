variable "aws_region" {
  type        = string
  description = "Región de AWS donde se desplegará la infra"
  default     = "us-east-1"
}

variable "db_username" {
  type        = string
  description = "Usuario maestro de la BD"
}

variable "db_password" {
  type        = string
  description = "Password maestro de la BD"
  sensitive   = true
}

variable "cluster_name" {
  type        = string
  description = "Nombre del cluster EKS"
  default     = "iot-suelo-cluster"
}
