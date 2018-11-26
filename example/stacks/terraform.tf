terraform {
  backend "s3" {
    region         = "{{ var.aws_region }}"
    bucket         = "{{ var.project }}-tfstate-{{ var.envtype }}"
    key            = "{{ var.stack }}/{{ var.env }}/terraform.tfstate"
    dynamodb_table = "{{ var.project }}-tfstate"
    encrypt        = "true"
  }

  required_version = "0.11.10"
}
