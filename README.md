# Jinjaform

Jinjaform is a transparent Terraform wrapper written in Python that adds Jinja2 template rendering and other features aimed at making Terraform projects easier to use.

## Features

* Jinja2 template rendering with access to Terraform and environment variables
    * Allows variable usage where Terraform normally does not, e.g. backends and module source
* Hierarchical project structure allows for code reuse and deployment-specific files
    * `.tfvars` files are combined into single `terraform.tfvars` for variable value composition
    * `.root` symlink to Terraform project root directory for relative paths to top level directory, e.g. `.root/modules/module-name` for module sources
* MFA support for AWS profiles
* S3 + DynamoDB Terraform backend creation
* Git checks
    * Checks for clean and up-to-date branch before applying changes
* Modules shared between all deployments in project
    * Faster `terraform init/get`
* Plugin cache enabled by default
    * Faster `terraform init`

## Requirements

* Python 3
* Terraform

## Setup with Direnv

If you're using [Direnv](https://direnv.net/) then add something like this to your `.envrc` file:

```sh
layout python3
pip install -q jinjaform==0.2.0
PATH_add $(python -m jinjaform.direnv $(pwd)/terraform)
```

This will install a `terraform` shim that runs Jinjaform instead of Terraform. The above assumes that you have a `terraform` directory which is considered your "Terraform project root" directory.

## Setup manually

Manual set up has not been fully considered yet.

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

If you run `terraform plan` from the `terraform/site/dev` directory, Jinjaform will combine the files from each level (`terraform`, `site`, `dev`) into a single working directory before it executes Terraform.

All `.tf` files will be rendered with Jinja2.

All `.tfvars` are combined into a single `terraform.tfvars` file which Terraform uses by default.

See the [example](./example) directory for a more complete example of how a project could be structured.

## Gotchas

### Maximum of 1 AWS profile

Terraform seems to have a bug where it ignores AWS provider profiles when there are multiple provider blocks with different profiles. To work around this limitation, ensure that each deployment uses only 1 AWS profile.

### S3 + DynamoDB backend AWS profile

If the Terraform backend uses S3 + DynamoDB, Jinjaform will create the S3 bucket and DynamoDB table if they do not already exist. Jinjaform will use the AWS profile from the AWS provider block.

### Git checks

It is assumed that the project's Git workflow is to apply Terraform changes from a clean, up-to-date master branch, and it will error if that is not the case. Other workflows are not currently supported but if the Git check fails, instructions for bypassing it are displayed along with the error message.
