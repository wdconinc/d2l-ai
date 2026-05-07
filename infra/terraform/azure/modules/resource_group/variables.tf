variable "name" {
  description = "Resource group name."
  type        = string
}

variable "location" {
  description = "Azure location."
  type        = string
}

variable "tags" {
  description = "Resource tags."
  type        = map(string)
  default     = {}
}
