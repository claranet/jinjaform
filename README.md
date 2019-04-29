# Jinjaform

Jinjaform is a transparent Terraform wrapper written in Python that adds Jinja2 template rendering and other features aimed at making Terraform projects easier to use.

## Features

* Jinja2 template rendering with access to Terraform and environment variables
    * Allows variable usage where Terraform normally does not, e.g. backends and module source
* Hierarchical project structure allows for files to be used across multiple environments or specific environments depending on their location
* MFA support for AWS profiles
* S3 + DynamoDB Terraform backend creation
* Git checks
    * Checks for clean and up-to-date branch before applying changes
* Modules shared between all deployments in project
    * Faster `terraform init/get`
* Plugin cache enabled by default
    * Faster `terraform init`
* Hooks for running arbitrary commands
    * See the [Configuration](#configuration) section
* Custom Jinja2 filters and tests
    * See the [Customise](#customise) section

## Requirements

* Python 3
* Terraform

## Setup

Install Jinjaform with Python pip, .e.g. `pip install jinjaform`.

Jinjaform requires a `.jinjaformrc` file in the root directory of your Terraform project. When you run `jinjaform` it will look for this file in the current or parent directories. If `.jinjaformrc` is not found in the directory tree, it will suggest running `jinjaform create` to create one. This will create a file that will suit most projects. This file can be [edited to suit your project](#configuration) and should be committed to version control.

If you are using Direnv, and want Jinjaform to run instead of Terraform, add this to your `.envrc` file:

```
# Run Jinjaform instead of Terraform.
JINJAFORM_PROJECT_ROOT=terraform
PATH_add "$(mkdir -p "${JINJAFORM_PROJECT_ROOT}/.jinjaform/bin" && cd $_ && ln -fs $(which jinjaform) terraform && pwd)"
```

The above assumes that `/.envrc` is in the root of your Git repository, and there is a `.jinjaformrc` file in the `/terraform` directory.

## Project structure

Jinjaform does not dictate any particular project structure, but it will flatten the directory tree, up to the Terraform project root, into a working directory when it runs.

For example, given the following project structure:

```
terraform/
    *.tf
    *.tfvars
    account/
        *.tf
        *.tfvars
        nonprod/
            *.tf
            *.tfvars
        prod/
            *.tf
            *.tfvars
    management/
        *.tf
        *.tfvars
        nonprod/
            *.tf
            *.tfvars
        prod/
            *.tf
            *.tfvars
    site/
        *.tf
        *.tfvars
        dev/
            *.tf
            *.tfvars
        stage/
            *.tf
            *.tfvars
        prod/
            *.tf
            *.tfvars
```

If you run `jinjaform plan` from the `terraform/site/dev` directory, Jinjaform will combine the files from each level (`terraform`, `site`, `dev`) into a single working directory before it executes Terraform.

All `.tf` files will be rendered with Jinja2.

Files in multiple levels of the directory tree with the same name are combined into a single file in the working directory.

See the [example](./example) directory for a more complete example of how a project could be structured.

## Configuration

Jinjaform can configured by editing the `.jinjaformrc` file. This file defines the entire Jinjaform workflow.

Run `jinjaform create` to create a new `.jinjaformrc` file with default commands and then edit the file to suit your project.

The follow commands can be used:

* `GIT_CHECK_BRANCH <name>`
    * Errors if the current Git branch is not the one specified.
* `GIT_CHECK_CLEAN`
    * Errors if the current Git branch is not clean.
* `GIT_CHECK_REMOTE`
    * Errors if the current Git branch is not up to date.
* `RUN <command>`
    * Runs a shell command.
    * Environment variables of note:
        * `JINJAFORM_PROJECT_ROOT`
        * `JINJAFORM_WORKSPACE`
* `TERRAFORM_RUN`
    * Runs Terraform using the arguments passed into Jinjaform in the workspace directory created by Jinjaform.
* `WORKSPACE_CREATE`
    * Creates a workspace directory to be used by Terraform.
        * Flattens the directory tree.
        * Renders `.tf` files as Jinja2 templates.

An example of a custom configuration is included in the [example](./example) directory.

## Customise

You use [Custom Jinja2 Filters](http://jinja.pocoo.org/docs/2.10/api/#custom-filters) and [Custom Jinja2 Tests](http://jinja.pocoo.org/docs/2.10/api/#custom-tests) and custom context functions/variables in templates.

Create a `.jinja` directory next to your `.jinjaformrc` file. Jinjaform will load custom context values from `.jina/context/*.py`, custom filters from `.jinja/filters/*.py`, and custom tests from `.jinja/tests/*.py`. Function/variable names must be included in the `__all__` list of the containing file for it to be made available in your templates.

### Example custom context functions/variables:

```py
# .jinja/context/example.py

from jinja2 import contextfunction


@contextfunction
def get_var(ctx, name):
    """
    Returns a Terraform variable from the context.
    This is unnecessary as `var` is already in the context,
    but it shows how to access Terraform variables from a Python function.

    Usage: "{{ get_var(name) }}"
    Output: the value of the Terraform variable

    """

    return ctx['var'][name]


def range(limit):
    """
    Returns every number from 0 to the limit.

    Usage: "{% for num in range(10) %}{{ num }}{% endfor %}"
    Output: [0, 1, 2, ..., limit]

    """

    return range(limit)


animals = ['cat', 'dog', 'buffalo']


__all__ = ['animals', 'get_var', 'range']
```

### Example custom filters:

```py
# .jinja/filters/example.py

def double(value):
    """
    Doubles the value.

    Usage: "{{ 2 | double }}"
    Output: "4"

    """

    return value * 2


def tf(value):
    """
    Wraps the value with Terraform interpolation syntax.

    Usage: "{{ 'module.example.arn' | tf }}"
    Output: "${module.example.arn}"

    """

    return '${' + value + '}'


__all__ = ['double', 'tf']
```

### Example custom tests:

```py
# .jinja/tests/example.py

def even(value):
    """
    Tests if a number is even.

    Usage: {% if 123 is even %}{% endif %}

    """

    return value % 2 == 0


def odd(value):
    """
    Tests if a number is odd.

    Usage: {% if 123 is odd %}{% endif %}

    """

    return not even(value)


__all__ = ['even', 'odd']
```

## AWS accounts and credentials

### Simple setup

The simplest way to set AWS credentials is like so:

```tf
provider "aws" {
  allowed_account_ids = ["111111111111"]
  profile             = "claranet-prod"
  region              = "eu-west-1"
}

terraform {
  backend "s3" {
    region         = "eu-west-1"
    bucket         = "your-tfstate-bucket"
    key            = "terraform.tfstate"
    dynamodb_table = "tfstate"
    encrypt        = "true"
  }

  required_version = "0.11.11"
}

resource "aws_sqs_queue" "prod" {
  name = "jinjaform-test-prod"
}
```

This works because:

* Jinjaform finds the default AWS provider, uses the profile to get AWS credentials, and then exports them as environment variables.
* Terraform ignores the `profile` argument when credentials are set with environment variables.

Terraform does not ordinarily support profiles with MFA prompts, but Jinjaform does. It also uses [boto-source-profile-mfa](https://github.com/claranet/boto-source-profile-mfa) to cache and reuse MFA tokens.

### Advanced usage

The helper function `aws.session()` is available in templates to work with AWS. This function is mostly a wrapper for [boto3.Session](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/core/session.html) and accepts the same keyword arguments.

The session object returned by this function can be used to get AWS credentials, or even interact with the AWS APIs directly.

Below is an example of how to use `aws.session()` to work with multiple AWS accounts.

```tf
# Use the production account as the default provider.

provider "aws" {
  allowed_account_ids = ["111111111111"]
  profile             = "claranet-prod"
  region              = "eu-west-1"
}

terraform {
  backend "s3" {
    region         = "eu-west-1"
    bucket         = "your-tfstate-bucket"
    key            = "terraform.tfstate"
    dynamodb_table = "tfstate"
    encrypt        = "true"
  }

  required_version = "0.11.11"
}

resource "aws_sqs_queue" "prod" {
  name = "jinjaform-test-prod"
}

# Create another provider to use the nonprod account.
# {% set nonprod_session = aws.session(profile_name='claranet-nonprod') %}
# {% set nonprod_creds = nonprod_session.get_credentials().get_frozen_credentials() %}

provider "aws" {
  alias               = "nonprod"
  allowed_account_ids = ["222222222222"]
  access_key          = "{{ nonprod_creds.access_key }}"
  secret_key          = "{{ nonprod_creds.secret_key }}"
  token               = "{{ nonprod_creds.token }}"
  region              = "eu-west-1"
}

resource "aws_sqs_queue" "nonprod" {
  provider = "aws.nonprod"
  name     = "jinjaform-test-nonprod"
}
```
