terraform {
  required_version = "= 1.12.2"
}

variable "replicas" {
  description = "Number of service replicas in the local model."
  type        = number
  default     = 2
  validation {
    condition     = var.replicas >= 1 && floor(var.replicas) == var.replicas
    error_message = "replicas must be a positive whole number."
  }
}

module "service" {
  source   = "./modules/service"
  replicas = var.replicas
}

output "service_id" {
  value = module.service.id
}
