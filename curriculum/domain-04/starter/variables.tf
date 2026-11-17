variable "region" {
  type    = string
  default = "us-east-1"
  validation {
    condition     = contains(["us-east-1", "eu-west-1", "eu-west-2"], var.region)
    error_message = "Use eu-west-1 (Ireland), us-east-1 (N. Virginia), or eu-west-2 (London)."
  }
}

variable "account_id" {
  type = string
  validation {
    condition     = can(regex("^[0-9]{12}$", var.account_id))
    error_message = "An AWS account ID is required."
  }
}

variable "attempt_id" {
  type = string
  validation {
    condition     = can(regex("^[a-f0-9]{16}$", var.attempt_id))
    error_message = "Use the attempt ID supplied by tfprep."
  }
}

