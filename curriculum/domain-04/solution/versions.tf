terraform {
  required_version = "= 1.12.2"
  required_providers {
    random = {
      source  = "hashicorp/random"
      version = "= 3.7.2"
    }
    aws = {
      source  = "hashicorp/aws"
      version = "= 5.92.0"
    }
  }
}

