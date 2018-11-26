# Jinjaform example project

This example shows:

* Hierarchical project structure
    * Deploy from:
        * `stacks/account/nonprod`
        * `stacks/account/prod`
        * `stacks/site/dev`
        * `stacks/site/stage`
        * `stacks/site/prod`
* AWS provider
    * Defined once at the top level, uses variables to pick the relevant profile
* S3 + DynamoDB backend
    * Defined once at the top level, uses variables to pick the relevant details
* `.root` symlink used to reference modules
