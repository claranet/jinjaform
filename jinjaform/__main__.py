import os
import sys

from jinjaform import aws, files, git, log, root, terraform
from jinjaform.config import args, cwd, env, project_root, terraform_bin


commands_bypassed = (
    'fmt',
    'help',
    '-help',
    'version',
    '-version',
)

commands_forbidden_inside_target = (
    'push',
)

commands_using_backend = (
    'apply',
    'console',
    'debug'
    'destroy',
    'force-unlock',
    'graph',
    'import',
    'init',
    'output',
    'plan',
    'refresh',
    'show',
    'state',
    'taint',
    'untaint',
)

clean_after = False

try:

    if args:

        if not set(commands_bypassed).intersection(args):

            in_project_root = (cwd + '/').startswith(project_root + '/')
            in_target_path = in_project_root and os.path.exists('terraform.tfvars')

            if in_target_path:

                for command in commands_forbidden_inside_target:
                    if command in args:
                        log.bad('{} not allowed', command)
                        sys.exit(1)

                clean_after = True

                git.check()
                root.setup()
                files.delete()
                files.create()

                if set(commands_using_backend).intersection(args):
                    aws.credentials_setup()
                    if 'init' in args:
                        aws.backend_setup()

            else:

                log.bad('not in deployment target directory, aborting')
                sys.exit(1)

    log.ok('running terraform')
    sys.exit(terraform.execute(terraform_bin, args, env))

finally:

    if clean_after:
        files.delete()
