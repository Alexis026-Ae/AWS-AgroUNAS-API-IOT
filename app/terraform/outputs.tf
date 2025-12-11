output "ecr_repository_url" {
  value       = aws_ecr_repository.iot_api.repository_url
  description = "URL del repositorio ECR donde se sube la imagen de la API."
}

output "db_endpoint" {
  value       = aws_db_instance.iot_db.address
  description = "Endpoint de la base de datos PostgreSQL (RDS)."
}

output "api_service_name" {
  value       = "iot-api-service"
  description = "Nombre del Service de Kubernetes que expone la API."
}
