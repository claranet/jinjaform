import os

from jinjaform import log
from jinjaform.config import cwd, project_root


default = '''
# Check if the git checkout is clean.
# Only runs when using the "terraform apply" command.
GIT_CHECK_CLEAN

# Check if the master branch is checked out.
# Only runs when using the "terraform apply" command.
GIT_CHECK_BRANCH master

# Check if the local branch is up to date.
# Only runs when using the "terraform apply" command.
GIT_CHECK_REMOTE

# Create the Jinjaform workspace.
# Runs for all terraform commands except: help, fmt, version
WORKSPACE_CREATE

# Run terraform.
TERRAFORM_RUN
'''.lstrip()


def create():
    path = os.path.join(cwd, '.jinjaformrc')
    try:
        with open(path, 'x') as open_file:
            open_file.write(default)
    except FileExistsError:
        log.bad('.jinjaformrc file already exists')
        return 1
    else:
        log.ok('created {}', path)
        log.ok('your project root directory is {}', cwd)
        return 0


def read():

    rc_path = os.path.join(project_root, '.jinjaformrc')
    commands = []
    with open(rc_path) as open_file:
        for line in open_file:
            line = line.strip()
            if line and not line.startswith('#'):
                commands.append(line)

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
