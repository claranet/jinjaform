module "account" {
  source = ".root/account"
}

module "account-{{ var.envtype }}" {
  source = ".root/account-{{ var.envtype }}"
}
