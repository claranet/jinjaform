import jinja2
import os
import shutil

from jinjaform import log, config
from jinjaform.config import cwd, jinjaform_dir, project_root, tf_vars


def create():
    """
    Creates symlinks and render templates from parent directories
    into the current directory.

    """

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

            if name in seen or os.path.exists(name):
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
        os.symlink(os.path.relpath(source), name)

    # Read the config files to find variables for rendering.
    config.read()

    # Render the templates.
    templates.sort()
    os.makedirs(jinjaform_dir, exist_ok=True)
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

        os.symlink(os.path.relpath(output), name)

    # Read again in case variables were inside templates.
    config.read()


def delete():
    """
    Deletes symlinks and rendered templates from the current directory.

    """

    for name in sorted(os.listdir()):
        if os.path.islink(name):
            os.remove(name)

    if os.path.exists(jinjaform_dir):
        shutil.rmtree(jinjaform_dir)
