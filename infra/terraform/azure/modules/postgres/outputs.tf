output "id" {
  description = "PostgreSQL resource ID."
  value       = azurerm_postgresql_flexible_server.this.id
}

output "fqdn" {
  description = "PostgreSQL server FQDN."
  value       = azurerm_postgresql_flexible_server.this.fqdn
}

output "pgvector_enablement_sql" {
  description = "SQL statements for pgvector enablement path."
  value = [
    "CREATE EXTENSION IF NOT EXISTS vector;",
  ]
}
