import os
import sys

from jinjaform import log


args = sys.argv[1:]
cwd = os.getcwd()
env = os.environ.copy()


def find_project_root():
    current = cwd
    while True:
        path = os.path.join(current, '.jinjaformrc')
        if os.path.exists(path):
            return current
        current = os.path.dirname(current)
        if current == os.path.sep:
            return ''


def find_terraform_bin():
    for path in os.environ['PATH'].split(os.pathsep):
        terraform_path = os.path.join(path, 'terraform')
        if not os.path.exists(terraform_path):
            continue
        if not os.access(terraform_path, os.X_OK):
            continue
        real_name = os.path.basename(os.path.realpath(terraform_path))
        if real_name == 'jinjaform':
            continue
        return terraform_path
    log.bad('terraform: command not found')
    sys.exit(1)


project_root = find_project_root()
jinjaform_root = os.path.join(project_root, '.jinjaform')
terraform_bin = find_terraform_bin()
workspace_dir = os.path.join(cwd, '.jinjaform')
terraform_dir = os.path.join(workspace_dir, '.terraform')

aws_provider = {}
s3_backend = {}
sessions = {}

env['JINJAFORM_PROJECT_ROOT'] = project_root
env['JINJAFORM_WORKSPACE'] = workspace_dir
