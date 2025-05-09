terraform {
  required_version = "~> 1.0"

  backend "s3" {
    bucket = "srhoton-tfstate"
    key    = "service-history-lambda/service-history.tfstate"
    region = "us-east-1"
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}
