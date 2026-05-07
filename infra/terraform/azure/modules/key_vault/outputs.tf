output "name" {
  description = "Key Vault name."
  value       = azurerm_key_vault.this.name
}

output "id" {
  description = "Key Vault ID."
  value       = azurerm_key_vault.this.id
}
