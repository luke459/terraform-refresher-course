variable "environments" {
  type = map(object({ cidr = string, subnet_cidr = string }))
  default = {
    dev   = { cidr = "10.50.0.0/16", subnet_cidr = "10.50.1.0/24" }
    stage = { cidr = "10.51.0.0/16", subnet_cidr = "10.51.1.0/24" }
  }
}
module "app_tier" {
  source      = "./modules/app-tier"
  for_each    = var.environments
  network     = each.value
  environment = each.key
  attempt_id  = var.attempt_id
}
resource "aws_ssm_parameter" "summary" {
  name  = "/tf004/${var.attempt_id}/network-summary"
  type  = "String"
  value = jsonencode({ for name, tier in module.app_tier : name => tier.vpc_id })
}
output "summary_name" { value = aws_ssm_parameter.summary.name }
