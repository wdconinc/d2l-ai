variable "name" {
  description = "Redis instance name."
  type        = string
}

variable "location" {
  description = "Azure location."
  type        = string
}

variable "resource_group_name" {
  description = "Resource group name."
  type        = string
}

variable "capacity" {
  description = "Redis capacity."
  type        = number
  default     = 0
}

variable "family" {
  description = "Redis family."
  type        = string
  default     = "C"
}

variable "sku_name" {
  description = "Redis SKU."
  type        = string
  default     = "Basic"
}

variable "minimum_tls_version" {
  description = "Minimum TLS version."
  type        = string
  default     = "1.2"
}

variable "public_network_access_enabled" {
  description = "Enable public network access."
  type        = bool
  default     = true
}

variable "tags" {
  description = "Resource tags."
  type        = map(string)
  default     = {}
}
