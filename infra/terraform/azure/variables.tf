variable "project" {
  description = "Project short name."
  type        = string
  default     = "d2lai"
}

variable "environment" {
  description = "Environment name (for naming/tagging)."
  type        = string
  default     = "dev"
}

variable "location" {
  description = "Azure region for all resources."
  type        = string
  default     = "canadacentral"
}

variable "resource_group_name" {
  description = "Optional explicit resource group name override."
  type        = string
  default     = ""
}

variable "tenant_id" {
  description = "Entra ID tenant for Key Vault."
  type        = string
}

variable "tags" {
  description = "Additional tags applied to all resources."
  type        = map(string)
  default     = {}
}

variable "log_retention_days" {
  description = "Log Analytics retention in days."
  type        = number
  default     = 30
}

variable "postgres_administrator_login" {
  description = "PostgreSQL administrator login name."
  type        = string
  default     = "pgadmin"
}

variable "postgres_administrator_password" {
  description = "PostgreSQL administrator password."
  type        = string
  sensitive   = true
}

variable "postgres_sku_name" {
  description = "PostgreSQL Flexible Server SKU."
  type        = string
  default     = "B_Standard_B1ms"
}

variable "postgres_storage_mb" {
  description = "PostgreSQL storage in MB."
  type        = number
  default     = 32768
}

variable "postgres_version" {
  description = "PostgreSQL major version."
  type        = string
  default     = "16"
}

variable "postgres_delegated_subnet_id" {
  description = "Delegated subnet ID for private PostgreSQL access."
  type        = string
}

variable "postgres_private_dns_zone_id" {
  description = "Private DNS zone ID for PostgreSQL Flexible Server."
  type        = string
}

variable "postgres_public_network_access_enabled" {
  description = "Allow public access to PostgreSQL server. Keep false by default."
  type        = bool
  default     = false
}

variable "postgres_backup_retention_days" {
  description = "PostgreSQL backup retention in days."
  type        = number
  default     = 7
}

variable "postgres_zone" {
  description = "Availability zone for PostgreSQL."
  type        = string
  default     = "1"
}

variable "postgres_high_availability_mode" {
  description = "PostgreSQL HA mode (ZoneRedundant or SameZone)."
  type        = string
  default     = "ZoneRedundant"
}

variable "postgres_high_availability_standby_zone" {
  description = "Standby zone when HA is enabled."
  type        = string
  default     = "2"
}

variable "redis_sku_name" {
  description = "Redis SKU (Basic, Standard, Premium)."
  type        = string
  default     = "Basic"
}

variable "redis_family" {
  description = "Redis family (C for Basic/Standard, P for Premium)."
  type        = string
  default     = "C"
}

variable "redis_capacity" {
  description = "Redis capacity tier."
  type        = number
  default     = 0
}

variable "redis_public_network_access_enabled" {
  description = "Allow public access to Redis."
  type        = bool
  default     = false
}

variable "key_vault_sku_name" {
  description = "Key Vault SKU."
  type        = string
  default     = "standard"
}

variable "key_vault_public_network_access_enabled" {
  description = "Allow public network access to Key Vault."
  type        = bool
  default     = false
}

variable "key_vault_purge_protection_enabled" {
  description = "Enable purge protection for Key Vault."
  type        = bool
  default     = true
}

variable "container_image" {
  description = "Placeholder image for Container App skeleton."
  type        = string
  default     = "mcr.microsoft.com/k8se/quickstart:latest"
}

variable "container_target_port" {
  description = "Ingress target port for the container app placeholder."
  type        = number
  default     = 80
}

variable "container_cpu" {
  description = "Container app CPU for placeholder revision."
  type        = number
  default     = 0.25
}

variable "container_memory" {
  description = "Container app memory for placeholder revision (Gi)."
  type        = string
  default     = "0.5Gi"
}
