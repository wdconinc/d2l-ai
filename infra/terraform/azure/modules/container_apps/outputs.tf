output "environment_id" {
  description = "Container app environment ID."
  value       = azurerm_container_app_environment.this.id
}

output "app_endpoint" {
  description = "Container app ingress endpoint."
  value       = "https://${azurerm_container_app.this.latest_revision_fqdn}"
}
