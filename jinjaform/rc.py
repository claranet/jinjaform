import os

from jinjaform import log, config, git


default_commands = (
    'GIT_CHECK_CLEAN',
    'GIT_CHECK_BRANCH master',
    'GIT_CHECK_REMOTE',
    'WORKSPACE_CREATE',
    'TERRAFORM_RUN',
)


def read():
    rc_path = os.path.join(config.project_root, '.jinjaformrc')
    if os.path.exists(rc_path):
        commands = []
        with open(rc_path) as open_file:
            for line in open_file:
                line = line.strip()
                if line and not line.startswith('#'):
                    commands.append(line)
    else:
        commands = default_commands

    if commands.count('WORKSPACE_CREATE') != 1:
        log.bad('configuration: WORKSPACE_CREATE must be defined once')

    if commands.count('TERRAFORM_RUN') != 1:
        log.bad('configuration: TERRAFORM_RUN must be defined once')

    if commands.index('TERRAFORM_RUN') < commands.index('WORKSPACE_CREATE'):
        log.bad('configuration: WORKSPACE_CREATE must be defined before TERRAFORM_RUN')

    for command in commands:
        parts = command.split(None, 1)
        if len(parts) == 2:
            yield parts
        else:
            yield command, None
