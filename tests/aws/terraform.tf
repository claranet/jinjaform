terraform {
  backend "s3" {
    region         = "eu-west-1"
    bucket         = "jinjaform-tests-tfstate"
    key            = "aws/terraform.tfstate"
    dynamodb_table = "jinjaform-tests-tfstate"
    encrypt        = "true"
  }

  required_version = "0.11.11"
}
