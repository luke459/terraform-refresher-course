terraform {
  required_version = "= 1.12.2"
}

variable "replicas" {
  description = "Desired replica count in the local model."
  type        = number
}

resource "terraform_data" "service" {
  input = {
    replicas = var.replicas
  }
}

output "id" {
  value = terraform_data.service.id
}
