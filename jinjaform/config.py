import os
import re
import sys

from jinjaform import log, terraform


args = sys.argv[1:]
cwd = os.getcwd()
env = os.environ.copy()

for name in ('JINJAFORM_PROJECT_ROOT', 'JINJAFORM_TERRAFORM_BIN'):
    if not env.get(name):
        log.bad('{} environment variable missing', name)
        sys.exit(1)

project_root = os.environ['JINJAFORM_PROJECT_ROOT']
jinjaform_dir = os.path.join(cwd, '.jinjaform')
jinjaform_root = os.path.join(project_root, '.jinjaform')
terraform_bin = os.environ['JINJAFORM_TERRAFORM_BIN']
terraform_dir = os.path.join(cwd, '.terraform')

aws_profiles = set()
tf_vars = {}
s3_backend = {}
sessions = {}


def read(_done=set()):
    """
    Reads configuration from *.tf and *.tfvars files.

    """

    default_vars = {}

    for name in os.listdir():

        if name in _done:
            continue

        if name.lower().endswith('.tf'):

            inside_aws_provider = False
            inside_s3_backend = False
            inside_terraform = False
            inside_variable = None

            for line in terraform.fmt(terraform_bin, name).splitlines():

                if inside_aws_provider:
                    if line == '}':
                        inside_aws_provider = False
                    else:
                        match = re.match(r'\s+profile\s+=\s+"(.+)"$', line)
                        if match:
                            aws_profile = match.group(1)
                            aws_profiles.add(aws_profile)
                elif inside_terraform:
                    if inside_s3_backend:
                        if line == '  }':
                            inside_s3_backend = False
                        else:
                            match = re.match(r'\s+(.+?)\s+=\s+"?(.+?)"?$', line)
                            if match:
                                name = match.group(1)
                                value = match.group(2)
                                s3_backend[name] = value
                    else:
                        if line == '}':
                            inside_terraform = False
                        elif line == '  backend "s3" {':
                            inside_s3_backend = True
                elif inside_variable:
                    if line == '}':
                        inside_variable = None
                    else:
                        match = re.match(r'^\s+default\s+=\s+"?(.*?)"?$', line)
                        if match:
                            default_vars[inside_variable] = match.group(1)
                elif line == 'provider "aws" {':
                    inside_aws_provider = True
                elif line == 'terraform {':
                    inside_terraform = True
                else:
                    match = re.match(r'^variable "(.+)" {$', line)
                    if match:
                        inside_variable = match.group(1)

            _done.add(name)

        elif name.lower().endswith('.tfvars'):

            for line in terraform.fmt(terraform_bin, name).splitlines():
                match = re.match(r'^([^\s]+)\s+=\s+"?(.*?)"?$', line)
                if match:
                    name = match.group(1)
                    value = match.group(2)
                    tf_vars[name] = value

            _done.add(name)

    # Use default variable values if not specified in tfvars.
    for name in default_vars:
        if name not in tf_vars:
            tf_vars[name] = default_vars[name]
