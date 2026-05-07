variable "environment_name" {
  description = "Container Apps environment name."
  type        = string
}

variable "app_name" {
  description = "Container app name."
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

variable "log_analytics_workspace_id" {
  description = "Log Analytics workspace ID."
  type        = string
}

variable "container_image" {
  description = "Container image."
  type        = string
}

variable "target_port" {
  description = "Ingress target port."
  type        = number
}

variable "cpu" {
  description = "Container CPU allocation."
  type        = number
}

variable "memory" {
  description = "Container memory allocation (Gi)."
  type        = string
}

variable "tags" {
  description = "Resource tags."
  type        = map(string)
  default     = {}
}
