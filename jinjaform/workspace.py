import jinja2
import os
import shutil


from contextlib import suppress

from jinjaform import log, config
from jinjaform.config import cwd, env, jinjaform_dir, jinjaform_root, project_root, terraform_dir, tf_vars


def _populate():

    # Discover files to create.
    seen = set()
    links = []
    templates = []
    current = cwd
    while (current + '/').startswith(project_root + '/'):
        for name in sorted(os.listdir(current)):

            basename, ext = os.path.splitext(name)

            if ext.lower() not in ('.j2', '.tf', '.tfvars'):
                continue

            source = os.path.join(current, name)

            if ext.lower() == '.j2':
                name = name[:-3]

            if name in seen or os.path.exists(os.path.join(jinjaform_dir, name)):
                continue

            if ext.lower() == '.j2':
                templates.append((name, source))
            else:
                links.append((name, source))

            seen.add(name)

        current = os.path.dirname(current)

    # Create the symlinks.
    links.sort()
    for name, source in links:
        log.ok('link: {}', name)
        os.symlink(os.path.relpath(source, jinjaform_dir), os.path.join(jinjaform_dir, name))

    # Read the config files to find variables for rendering.
    config.read()

    # Render the templates.
    templates.sort()
    for name, source in templates:

        log.ok('render: {}', name)

        with open(source) as open_file:
            template = jinja2.Template(
                open_file.read(),
                undefined=jinja2.StrictUndefined,
            )

        context = os.environ.copy()
        context['var'] = tf_vars

        rendered = template.render(**context)

        output = os.path.join(jinjaform_dir, name)

        with open(output, 'w') as open_file:
            open_file.write(rendered)

    # Read again in case variables were inside templates.
    config.read()


def _remove(path):
    with suppress(FileNotFoundError):
        if os.path.islink(path):
            os.remove(path)
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)


def clean():
    if os.path.exists(jinjaform_dir):
        jinjaform_empty = True
        for name in os.listdir(jinjaform_dir):
            path = os.path.join(jinjaform_dir, name)
            if name == '.terraform':
                terraform_empty = True
                for sub_name in os.listdir(path):
                    sub_path = os.path.join(path, sub_name)
                    if os.path.islink(sub_path):
                        os.remove(sub_path)
                    else:
                        terraform_empty = False
                if terraform_empty:
                    os.rmdir(path)
                else:
                    jinjaform_empty = False
            else:
                _remove(path)
        if jinjaform_empty:
            os.rmdir(jinjaform_dir)


def create():
    # Ensure the .jinjaform/.terraform directory exists.
    os.makedirs(terraform_dir, exist_ok=True)

    # Create a .root symlink to the project root directory
    # so that Terraform code can access it using a relative path.
    root_link = os.path.join(jinjaform_dir, '.root')
    os.symlink(project_root, root_link)

    # TODO: remove later:
    # Create a .terraform/root symlink too.
    root_link = os.path.join(terraform_dir, 'root')
    os.symlink(project_root, root_link)

    # Create a shared modules directory for the entire project.
    module_cache_dir = os.path.join(jinjaform_root, 'modules')
    os.makedirs(module_cache_dir, exist_ok=True)
    module_link = os.path.join(terraform_dir, 'modules')
    _remove(module_link)
    os.symlink(module_cache_dir, module_link)

    # Create a shared plugin cache directory for the entire project.
    plugin_cache_dir = os.path.join(jinjaform_root, 'plugins')
    os.makedirs(plugin_cache_dir, exist_ok=True)
    env['TF_PLUGIN_CACHE_DIR'] = plugin_cache_dir

    # Populates workspace with Terraform configuration files.
    _populate()
