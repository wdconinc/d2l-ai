output "hostname" {
  description = "Redis host name."
  value       = azurerm_redis_cache.this.hostname
}

output "id" {
  description = "Redis resource ID."
  value       = azurerm_redis_cache.this.id
}
