module "account" {
  source = "modules/account"
}

module "account-{{ var.envtype }}" {
  source = "modules/account-{{ var.envtype }}"
}
