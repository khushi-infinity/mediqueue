terraform {
  required_version = ">= 1.11, < 2.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.95"
    }
  }
}

provider "aws" {
  region = var.region
  default_tags {
    tags = {
      Project = "MediQueue"
      Student = "Khushi Sarawagi"
      Roll    = "24BCS10361"
      Managed = "Terraform"
    }
  }
}
