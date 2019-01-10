# Jinjaform

Jinjaform is a transparent Terraform wrapper written in Python that adds Jinja2 template rendering and other features aimed at making Terraform projects easier to use.

## Features

* Jinja2 template rendering with access to Terraform and environment variables
    * Allows variable usage where Terraform normally does not, e.g. backends and module source
* Hierarchical project structure allows for code reuse and deployment-specific files
    * `.tfvars` files are combined into single `terraform.tfvars` for variable value composition
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

# Configuration

Jinjaform can optionally be configured by adding a `.jinjaformrc` file in the Terraform project root directory. This file defines the entire Jinjaform workflow.

If this file does not exist, Jinjaform will use the following configuration:

```bash
# Check if the master branch is checked out.
# Only runs when using the "terraform apply" command.
GIT_CHECK_BRANCH master

# Check if the git checkout is clean.
# Only runs when using the "terraform apply" command.
GIT_CHECK_CLEAN

# Check if the local branch is up to date.
# Only runs when using the "terraform apply" command.
GIT_CHECK_REMOTE

# Create the Jinjaform workspace.
# Runs for all terraform commands except: help, fmt, version
WORKSPACE_CREATE

# Run terraform.
TERRAFORM_RUN
```

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

## Gotchas

### Maximum of 1 AWS profile

Terraform seems to have a bug where it ignores AWS provider profiles when there are multiple provider blocks with different profiles. To work around this limitation, ensure that each deployment uses only 1 AWS profile.

### S3 + DynamoDB backend AWS profile

If the Terraform backend uses S3 + DynamoDB, Jinjaform will create the S3 bucket and DynamoDB table if they do not already exist. Jinjaform will use the AWS profile from the AWS provider block.
