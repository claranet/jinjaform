import os
import shutil
import sys

from jinjaform import log


shim_template = '''
#!/usr/bin/env sh
export JINJAFORM_PROJECT_ROOT={project_root}
export JINJAFORM_TERRAFORM_BIN={terraform_bin}
python -m jinjaform $*
'''


def install():

    if len(sys.argv) > 2:
        log.bad('usage: python -m jinjaform.direnv [project_root]')
        sys.exit(1)

    if len(sys.argv) == 2:
        project_root = os.path.abspath(sys.argv[1])
    else:
        project_root = os.getcwd()

    terraform_bin = shutil.which('terraform')
    if not terraform_bin:
        log.bad('usage: could not find terraform in path')
        sys.exit(1)

    jinjaform_root = os.path.join(project_root, '.jinjaform')

    for name in ('bin', 'modules', 'plugins'):
        os.makedirs(os.path.join(jinjaform_root, name), exist_ok=True)

    shim_path = os.path.join(jinjaform_root, 'bin', 'terraform')

    with open(shim_path, 'w') as open_file:
        open_file.write(shim_template.format(
            project_root=project_root,
            terraform_bin=terraform_bin,
        ))

    os.chmod(shim_path, 0o755)

    # Print the path to use with Direnv's PATH_add function.
    print(os.path.dirname(shim_path))


if __name__ == '__main__':
    install()
