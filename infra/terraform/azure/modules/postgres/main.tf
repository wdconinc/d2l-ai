resource "azurerm_postgresql_flexible_server" "this" {
  name                   = var.name
  resource_group_name    = var.resource_group_name
  location               = var.location
  version                = var.postgres_version
  delegated_subnet_id    = var.delegated_subnet_id
  private_dns_zone_id    = var.private_dns_zone_id
  administrator_login    = var.administrator_login
  administrator_password = var.administrator_password
  zone                   = var.zone
  storage_mb             = var.storage_mb
  sku_name               = var.sku_name

  public_network_access_enabled = var.public_network_access_enabled
  backup_retention_days         = var.backup_retention_days

  dynamic "high_availability" {
    for_each = var.high_availability_mode == "Disabled" ? [] : [1]
    content {
      mode                      = var.high_availability_mode
      standby_availability_zone = var.high_availability_standby_zone
    }
  }

  tags = var.tags
}
