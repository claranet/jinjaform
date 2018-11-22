# jinjaform

Features:

* Deployment target directories - "terraform init/plan/apply" is run from these
* Symlinks files from parent directories into current target directory
* Renders Jinja2 templates with Terraform and environment variables
* AWS credentials taken from AWS provider block, adds MFA support
* Creates S3 + DynamoDB Terraform backend automatically
* Checks for clean Git status before applying changes
* Shares/caches modules and plugins between deployment targets

Assumptions:

* The "terraform init/plan/apply/etc" command only needs to run from "target" directories
* Each deployment target directory has a "terraform.tfvars" file
* Maximum of 1 AWS profile per target directory (multiple AWS provider blocks can still be used but they must use the same AWS profile)
* S3 + Dynamodb Terraform backend can be created with same AWS profile as the AWS provider
* Terraform normally runs from the Git "master" branch
