provider "aws" {
  region              = var.region
  allowed_account_ids = [var.account_id]
  default_tags {
    tags = {
      Project   = "tf-004-prep"
      ManagedBy = "terraform"
      Learner   = "local"
      Lab       = "01"
      Attempt   = var.attempt_id
    }
  }
}

