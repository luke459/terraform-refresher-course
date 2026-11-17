resource "aws_sns_topic" "course" { name = "tf004-${var.attempt_id}-incorrect" }
output "topic_arn" { value = aws_sns_topic.course.arn }
