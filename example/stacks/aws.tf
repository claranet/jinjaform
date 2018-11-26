provider "aws" {
  allowed_account_ids = ["${lookup(var.aws_account_ids, var.envtype)}"]
  profile             = "{{ var.project }}-{{ var.envtype }}"
  region              = "{{ var.aws_region }}"
  version             = "{{ var.aws_version }}"
}
