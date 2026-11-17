variable "services" {
  type = map(object({ port = number, cidr = string }))
  default = {
    web = { port = 443, cidr = "10.44.0.0/16" }
    ssh = { port = 22, cidr = "10.44.1.0/24" }
  }
  validation {
    condition     = alltrue([for service in values(var.services) : service.port >= 1 && service.port <= 65535 && can(cidrhost(service.cidr, 0))])
    error_message = "Each service needs a valid CIDR and port in 1..65535."
  }
}
variable "secret_version" {
  type    = number
  default = 1
}
resource "aws_vpc" "course" { cidr_block = "10.44.0.0/16" }
resource "aws_security_group" "service" {
  for_each    = var.services
  name_prefix = "tf004-${var.attempt_id}-${each.key}-"
  description = "Disposable service contract example"
  vpc_id      = aws_vpc.course.id
  ingress {
    from_port   = each.value.port
    to_port     = each.value.port
    protocol    = "tcp"
    cidr_blocks = [each.value.cidr]
  }
  lifecycle {
    precondition {
      condition     = each.value.port != 22 || each.value.cidr != "0.0.0.0/0"
      error_message = "SSH must not be open to the entire internet."
    }
    postcondition {
      condition     = self.vpc_id == aws_vpc.course.id
      error_message = "The security group must belong to the lab VPC."
    }
  }
}
check "service_count" {
  data "aws_security_groups" "course" {
    filter {
      name   = "tag:Attempt"
      values = [var.attempt_id]
    }
    filter {
      name   = "vpc-id"
      values = [aws_vpc.course.id]
    }
    depends_on = [aws_security_group.service]
  }
  assert {
    condition     = length(data.aws_security_groups.course.ids) == length(var.services)
    error_message = "AWS must contain one security group per service."
  }
}
ephemeral "random_password" "password" {
  length  = 24
  special = true
}
resource "aws_secretsmanager_secret" "password" {
  name                    = "tf004-${var.attempt_id}-password"
  recovery_window_in_days = 0
}
resource "aws_secretsmanager_secret_version" "password" {
  secret_id                = aws_secretsmanager_secret.password.id
  secret_string_wo         = ephemeral.random_password.password.result
  secret_string_wo_version = var.secret_version
}
output "secret_arn" { value = aws_secretsmanager_secret.password.arn }
