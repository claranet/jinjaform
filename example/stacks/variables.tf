variable "aws_account_ids" {
  default = {
    nonprod = "111111111111"
    prod    = "222222222222"
  }
}

variable "aws_region" {
  default = "eu-west-1"
}

variable "env" {
  type = "string"
}

variable "envtype" {
  type = "string"
}

variable "project" {
  default = "jinjaform"
}

variable "stack" {
  type = "string"
}
