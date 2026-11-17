resource "aws_vpc" "course" { cidr_block = "10.43.0.0/16" }
resource "aws_subnet" "app" {
  vpc_id     = aws_vpc.course.id
  cidr_block = "10.43.1.0/24"
}
resource "aws_security_group" "app" {
  name_prefix = "tf004-${var.attempt_id}-app-"
  description = "Disposable course security group"
  vpc_id      = aws_vpc.course.id
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["10.43.0.0/16"]
  }
  lifecycle { create_before_destroy = true }
}
output "security_group_id" { value = aws_security_group.app.id }
