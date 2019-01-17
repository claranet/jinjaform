import os
import subprocess
import sys

from jinjaform import aws, git, log, rc, terraform, workspace
from jinjaform.config import args, cwd, env, project_root, terraform_bin, workspace_dir


if 'create' in args:
    sys.exit(rc.create())

if not project_root:
    log.bad('could not find .jinjaformrc file in current or parent directories')
    log.bad('to start a new jinjaform project in the current directory, run "jinjaform create"')
    sys.exit(1)

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
    'providers',
    'refresh',
    'show',
    'state',
    'taint',
    'untaint',
)

workspace_required = False

if args:

    if not set(commands_bypassed).intersection(args):

        if cwd != project_root and (cwd + '/').startswith(project_root + '/'):

            for command in commands_forbidden:
                if command in args:
                    log.bad('{} not allowed', command)
                    sys.exit(1)

            workspace_required = True

        else:

            log.bad('not in deployment target directory, aborting')
            sys.exit(1)

if workspace_required:

    for rc_cmd, rc_arg in rc.read():

        if rc_cmd == 'GIT_CHECK_BRANCH':

            git.check_branch(desired=rc_arg)

        elif rc_cmd == 'GIT_CHECK_CLEAN':

            git.check_clean()

        elif rc_cmd == 'GIT_CHECK_REMOTE':

            git.check_remote()

        elif rc_cmd == 'RUN':

            log.ok('run: {}'.format(rc_arg))
            returncode = subprocess.call(rc_arg, env=env, shell=True)
            if returncode != 0:
                sys.exit(returncode)

        elif rc_cmd == 'TERRAFORM_RUN':

            log.ok('run: terraform')
            os.chdir(workspace_dir)
            returncode = terraform.execute(terraform_bin, args, env)
            if returncode != 0:
                sys.exit(returncode)

        elif rc_cmd == 'WORKSPACE_CREATE':

            workspace.clean()
            workspace.create()

            if set(commands_using_backend).intersection(args):
                aws.credentials_setup()
                if 'init' in args:
                    aws.backend_setup()

        else:

            log.bad('configuration: {} is not a valid command', rc_cmd)
            sys.exit(1)

else:

    log.ok('run: terraform')
    returncode = terraform.execute(terraform_bin, args, env)
    if returncode != 0:
        sys.exit(returncode)
