resource "aws_ssm_parameter" "metadata" {
  name  = "/tf004/${var.attempt_id}/drift"
  type  = "String"
  value = "desired"
  tags  = { Stage = "desired" }
}
moved {
  from = aws_ssm_parameter.legacy
  to   = aws_ssm_parameter.metadata
}
removed {
  from = aws_ssm_parameter.detached
  lifecycle { destroy = false }
}
output "parameter_name" { value = aws_ssm_parameter.metadata.name }
