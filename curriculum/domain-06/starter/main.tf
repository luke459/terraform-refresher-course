resource "aws_ssm_parameter" "legacy" {
  name  = "/tf004/${var.attempt_id}/drift"
  type  = "String"
  value = "desired"
  tags  = { Stage = "desired" }
}
resource "aws_ssm_parameter" "detached" {
  name  = "/tf004/${var.attempt_id}/detached"
  type  = "String"
  value = "Remove from state without deleting, then clean up explicitly."
}
output "parameter_name" { value = aws_ssm_parameter.legacy.name }
