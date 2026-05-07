output "identity_ids" {
  description = "Managed identity IDs keyed by logical name."
  value       = { for k, v in azurerm_user_assigned_identity.this : k => v.id }
}

output "principal_ids" {
  description = "Managed identity principal IDs keyed by logical name."
  value       = { for k, v in azurerm_user_assigned_identity.this : k => v.principal_id }
}
