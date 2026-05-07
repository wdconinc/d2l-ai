output "app_endpoint" {
  description = "Container App placeholder endpoint URL."
  value       = module.container_apps.app_endpoint
}

output "database_host" {
  description = "PostgreSQL Flexible Server FQDN."
  value       = module.postgres.fqdn
}

output "redis_host" {
  description = "Azure Redis host name."
  value       = module.redis.hostname
}

output "key_vault_name" {
  description = "Azure Key Vault name."
  value       = module.key_vault.name
}

output "managed_identity_ids" {
  description = "Managed identity resource IDs."
  value       = module.identities.identity_ids
}

output "pgvector_enablement_sql" {
  description = "SQL commands to run after provisioning for pgvector enablement path."
  value       = module.postgres.pgvector_enablement_sql
}
