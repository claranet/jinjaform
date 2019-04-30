import os
import subprocess
import sys

from jinjaform import aws, git, log, rc, terraform, workspace, __version__
from jinjaform.config import args, cmd, cwd, env, project_root, terraform_bin, workspace_dir


commands_bypassed = (
    'fmt',
    'help', '-h', '-help', '--help',
    'version', '-v', '-version', '--version',
)

commands_forbidden = (
    'push',
)


def main():

    if cmd == 'create':
        sys.exit(rc.create())

    if cmd in ('version', '-v', '-version', '--version'):
        log.ok('version: {}'.format(__version__))

    workspace_required = False

    if cmd:

        if cmd in commands_forbidden:
            log.bad('{} is disabled in jinjaform', cmd)
            sys.exit(1)

        if cmd not in commands_bypassed:

            if not project_root:
                log.bad('could not find .jinjaformrc file in current or parent directories')
                log.bad('to start a new jinjaform project in the current directory, run "jinjaform create"')
                sys.exit(1)

            workspace_required = True

    if workspace_required:

        if cwd == project_root:
            log.bad('cannot run from the jinjaform project root directory, aborting')
            sys.exit(1)

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

                aws.credentials_setup()

                if cmd == 'init':
                    aws.backend_setup()

            else:

                log.bad('configuration: {} is not a valid command', rc_cmd)
                sys.exit(1)

    else:

        log.ok('run: terraform')
        returncode = terraform.execute(terraform_bin, args, env)
        if returncode != 0:
            sys.exit(returncode)


if __name__ == '__main__':
    main()
