import os
import sys

from jinjaform import aws, git, log, terraform, workspace
from jinjaform.config import args, cwd, env, jinjaform_dir, project_root, terraform_bin


commands_bypassed = (
    'fmt',
    'help',
    '-help',
    'version',
    '-version',
)

commands_forbidden = (
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

workspace_enabled = False

if args:

    if not set(commands_bypassed).intersection(args):

        if cwd != project_root and (cwd + '/').startswith(project_root + '/'):

            for command in commands_forbidden:
                if command in args:
                    log.bad('{} not allowed', command)
                    sys.exit(1)

            git.check()

            workspace.clean()
            workspace_enabled = True
            workspace.create()

            if set(commands_using_backend).intersection(args):
                aws.credentials_setup()
                if 'init' in args:
                    aws.backend_setup()

        else:

            log.bad('not in deployment target directory, aborting')
            sys.exit(1)

if workspace_enabled:
    os.chdir(jinjaform_dir)

log.ok('running terraform')
sys.exit(terraform.execute(terraform_bin, args, env))
