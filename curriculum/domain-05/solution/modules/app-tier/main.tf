terraform {
  required_version = "= 1.12.2"
  required_providers { aws = { source = "hashicorp/aws", version = "= 5.92.0" } }
}
variable "network" { type = object({ cidr = string, subnet_cidr = string }) }
variable "environment" { type = string }
variable "attempt_id" { type = string }
resource "aws_vpc" "app" {
  cidr_block = var.network.cidr
  tags       = { Environment = var.environment }
}
resource "aws_subnet" "app" {
  vpc_id     = aws_vpc.app.id
  cidr_block = var.network.subnet_cidr
  tags       = { Environment = var.environment }
}
resource "aws_security_group" "app" {
  name_prefix = "tf004-${var.attempt_id}-${var.environment}-"
  description = "Disposable module lab security group"
  vpc_id      = aws_vpc.app.id
  tags        = { Environment = var.environment }
}
output "vpc_id" { value = aws_vpc.app.id }
output "subnet_id" { value = aws_subnet.app.id }
