locals {
  name_prefix              = "${var.project}-${var.environment}"
  key_vault_name_sanitized = replace(lower(local.name_prefix), "/[^0-9a-z]/", "")
  # Key Vault name max is 24 chars; reserve 6 chars for random_string.kv_suffix.
  key_vault_name_prefix = substr(
    length(local.key_vault_name_sanitized) > 0 ? local.key_vault_name_sanitized : "kv",
    0,
    18,
  )

  tags = merge(
    {
      environment = var.environment
      project     = var.project
      managed_by  = "terraform"
    },
    var.tags,
  )
}

module "resource_group" {
  source = "./modules/resource_group"

  name     = var.resource_group_name != "" ? var.resource_group_name : "rg-${local.name_prefix}"
  location = var.location
  tags     = local.tags
}

module "log_analytics" {
  source = "./modules/log_analytics"

  name                = "log-${local.name_prefix}"
  location            = module.resource_group.location
  resource_group_name = module.resource_group.name
  retention_in_days   = var.log_retention_days
  tags                = local.tags
}

module "identities" {
  source = "./modules/identities"

  resource_group_name = module.resource_group.name
  location            = module.resource_group.location
  names = {
    app    = "id-${local.name_prefix}-app"
    worker = "id-${local.name_prefix}-worker"
  }
  tags = local.tags
}

module "key_vault" {
  source = "./modules/key_vault"

  name                          = "${local.key_vault_name_prefix}${random_string.kv_suffix.result}"
  location                      = module.resource_group.location
  resource_group_name           = module.resource_group.name
  tenant_id                     = var.tenant_id
  sku_name                      = var.key_vault_sku_name
  enable_rbac_authorization     = true
  purge_protection_enabled      = var.key_vault_purge_protection_enabled
  public_network_access_enabled = var.key_vault_public_network_access_enabled
  tags                          = local.tags
}

module "redis" {
  source = "./modules/redis"

  name                          = "redis-${local.name_prefix}"
  location                      = module.resource_group.location
  resource_group_name           = module.resource_group.name
  capacity                      = var.redis_capacity
  family                        = var.redis_family
  sku_name                      = var.redis_sku_name
  minimum_tls_version           = "1.2"
  public_network_access_enabled = var.redis_public_network_access_enabled
  tags                          = local.tags
}

module "postgres" {
  source = "./modules/postgres"

  name                           = "psql-${local.name_prefix}"
  location                       = module.resource_group.location
  resource_group_name            = module.resource_group.name
  administrator_login            = var.postgres_administrator_login
  administrator_password         = var.postgres_administrator_password
  sku_name                       = var.postgres_sku_name
  storage_mb                     = var.postgres_storage_mb
  postgres_version               = var.postgres_version
  delegated_subnet_id            = var.postgres_delegated_subnet_id
  private_dns_zone_id            = var.postgres_private_dns_zone_id
  public_network_access_enabled  = var.postgres_public_network_access_enabled
  backup_retention_days          = var.postgres_backup_retention_days
  zone                           = var.postgres_zone
  high_availability_mode         = var.postgres_high_availability_mode
  high_availability_standby_zone = var.postgres_high_availability_standby_zone
  tags                           = local.tags
}

module "container_apps" {
  source = "./modules/container_apps"

  environment_name           = "cae-${local.name_prefix}"
  app_name                   = "app-${local.name_prefix}"
  location                   = module.resource_group.location
  resource_group_name        = module.resource_group.name
  log_analytics_workspace_id = module.log_analytics.id
  container_image            = var.container_image
  target_port                = var.container_target_port
  external_enabled           = var.container_external_enabled
  cpu                        = var.container_cpu
  memory                     = var.container_memory
  tags                       = local.tags
}

resource "random_string" "kv_suffix" {
  length  = 6
  special = false
  upper   = false
}
