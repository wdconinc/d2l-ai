resource "azurerm_user_assigned_identity" "this" {
  for_each = var.names

  name                = each.value
  location            = var.location
  resource_group_name = var.resource_group_name
  tags                = var.tags
}
