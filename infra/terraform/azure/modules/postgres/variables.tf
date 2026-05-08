variable "name" {
  description = "PostgreSQL server name."
  type        = string
}

variable "resource_group_name" {
  description = "Resource group name."
  type        = string
}

variable "location" {
  description = "Azure location."
  type        = string
}

variable "postgres_version" {
  description = "PostgreSQL major version."
  type        = string
  default     = "16"
}

variable "delegated_subnet_id" {
  description = "Delegated subnet for private access."
  type        = string
}

variable "private_dns_zone_id" {
  description = "Private DNS zone ID."
  type        = string
}

variable "administrator_login" {
  description = "Administrator login."
  type        = string
}

variable "administrator_password" {
  description = "Administrator password."
  type        = string
  sensitive   = true

  validation {
    # Azure Flexible Server requires >= 8 chars AND at least 3 of: uppercase,
    # lowercase, digits, non-alphanumeric. This check catches obviously short
    # passwords; the full complexity requirement is enforced by Azure at apply time.
    condition     = length(var.administrator_password) >= 8
    error_message = "PostgreSQL administrator password must be at least 8 characters (Azure also requires character complexity — see Azure Flexible Server documentation)."
  }
}

variable "zone" {
  description = "Primary availability zone."
  type        = string
  default     = "1"
}

variable "storage_mb" {
  description = "Storage size (MB)."
  type        = number
  default     = 32768
}

variable "sku_name" {
  description = "PostgreSQL SKU name."
  type        = string
  default     = "B_Standard_B1ms"
}

variable "public_network_access_enabled" {
  description = "Enable public network access."
  type        = bool
  default     = false
}

variable "backup_retention_days" {
  description = "Backup retention in days."
  type        = number
  default     = 7
}

variable "high_availability_mode" {
  description = "HA mode."
  type        = string
  default     = "ZoneRedundant"

  validation {
    condition = contains(
      ["Disabled", "ZoneRedundant", "SameZone"],
      var.high_availability_mode
    )
    error_message = "high_availability_mode must be one of: Disabled, ZoneRedundant, SameZone."
  }
}

variable "high_availability_standby_zone" {
  description = "Standby zone."
  type        = string
  default     = "2"
}

variable "tags" {
  description = "Resource tags."
  type        = map(string)
  default     = {}
}
