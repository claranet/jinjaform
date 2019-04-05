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

You use [Custom Jinja2 Filters](http://jinja.pocoo.org/docs/2.10/api/#custom-filters) and [Custom Jinja2 Tests](http://jinja.pocoo.org/docs/2.10/api/#custom-tests) in templates.

Create a `.jinja` directory next to your `.jinjaformrc` file. Jinjaform will load custom filters from `.jinja/filters/*.py` and custom tests from `.jinja/tests/*.py`. Function names must be included in the `__all__` list of the containing file for it to be made available in your templates.

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

### Example custom test:

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

## Gotchas

### Maximum of 1 AWS profile

Terraform seems to have a bug where it ignores AWS provider profiles when there are multiple provider blocks with different profiles. To work around this limitation, ensure that each deployment uses only 1 AWS profile.

### S3 + DynamoDB backend AWS profile

If the Terraform backend uses S3 + DynamoDB, Jinjaform will create the S3 bucket and DynamoDB table if they do not already exist. Jinjaform will use the AWS profile from the AWS provider block.
