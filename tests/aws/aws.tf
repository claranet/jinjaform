provider "aws" {
  allowed_account_ids = ["{{ PLAYGROUND_ACCOUNT_ID }}"]
  profile             = "{{ PLAYGROUND_ACCOUNT_PROFILE}}"
  region              = "eu-west-1"
}

# {% set internal_session = aws.session(profile_name=INTERNAL_ACCOUNT_PROFILE) %}
# {% set internal_creds = internal_session.get_credentials().get_frozen_credentials() %}

provider "aws" {
  alias               = "internal"
  allowed_account_ids = ["{{ INTERNAL_ACCOUNT_ID }}"]
  access_key          = "{{ internal_creds.access_key }}"
  secret_key          = "{{ internal_creds.secret_key }}"
  token               = "{{ internal_creds.token }}"
  region              = "eu-west-1"
}
