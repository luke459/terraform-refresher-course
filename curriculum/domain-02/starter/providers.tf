provider "aws" {
  region              = "us-east-1"
  allowed_account_ids = [var.account_id]
  default_tags {
    tags = {
      Project   = "tf-004-prep"
      ManagedBy = "terraform"
      Learner   = "local"
      Lab       = "02"
      Attempt   = var.attempt_id
    }
  }
}


provider "aws" {
  alias               = "uk"
  region              = "eu-west-2"
  allowed_account_ids = [var.account_id]
  default_tags {
    tags = {
      Project    = "tf-004-prep"
      ManagedBy  = "terraform"
      Learner    = "local"
      Lab        = "02"
      Attempt    = var.attempt_id
      RegionRole = "uk"
    }
  }
}
