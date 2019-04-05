import hcl
import importlib
import os
import pkgutil
import shutil
import sys

from collections import defaultdict
from contextlib import suppress

from itertools import chain

from jinja2 import Environment, StrictUndefined
from jinja2.exceptions import UndefinedError

from jinjaform import log, config
from jinjaform.config import cwd, env, jinjaform_root, project_root, terraform_dir, workspace_dir

from threading import current_thread, Event, Lock, Thread


class VarStore(object):

    def __init__(self, threads):

        self._threads = threads

        self._lock = Lock()
        self._waiters = defaultdict(list)

        self._defined = set()
        self._defaults = dict()
        self._values = dict()

        self._unresolved = dict()

    def __getitem__(self, key):
        """
        Returns a variable value. If the variable has not been defined
        then this will block and wait for it.

        """

        # Wait if the variable has not been defined yet.
        self._wait_for_variable(key)

        # Return the value if the variable has been defined
        # with a specific value or a default value.
        if key in self._defined:
            if key in self._values:
                return self._values[key]
            if key in self._defaults:
                return self._defaults[key]

        # The variable was not defined, or it was defined without a value,
        # or it was defined but there was a deadlock when resolving it.
        self._unresolved[current_thread()] = key
        raise KeyError(key)

    def _check_deadlock(self):
        """
        Checks if all threads are waiting for a variable to be defined.
        This means that the variable is not defined, or there is a circular
        dependency between files that define and use variables.

        If this is the case, then this function will unblock the threads,
        allowing them to continue executing without their variable. They
        would then have an error because the variable isn't defined.

        """

        waiters = list(chain.from_iterable(self._waiters.values()))
        all_threads_blocked = len(waiters) == len(self._threads)
        if all_threads_blocked:
            for event in waiters:
                event.set()

    def _define_variable(self, name, default):
        """
        Adds a variable definition and unblocks any waiting threads.

        """

        with self._lock:
            self._defined.add(name)
            if default is not None:
                self._defaults[name] = default
                for event in self._waiters.pop(name, []):
                    event.set()

    def _get_unresolved_variable(self):
        return self._unresolved.get(current_thread())

    def _set_variable_value(self, name, value):
        self._values[name] = value

    def _thread_done(self):
        """
        Removes the current thread and checks for any deadlocks.

        """

        with self._lock:
            self._threads.remove(current_thread())
            self._check_deadlock()

    def _wait_for_variable(self, name):
        """
        Waits for a variable to be defined.
        Returns immediately if it has already been defined.

        """

        with self._lock:
            if name in self._defined:
                return
            event = Event()
            self._waiters[name].append(event)
            self._check_deadlock()
        event.wait()


class MultiTemplateRenderer(object):

    def __init__(self):
        self._threads = set()
        self._var_store = VarStore(self._threads)
        self._errors = []
        self._rendered = {}
        self._jinja_environment = self._create_jinja_environment()

    def _create_jinja_environment(self):

        # Create a Jina2 Environment.
        env = Environment(
            undefined=StrictUndefined,
            keep_trailing_newline=True,
            extensions=[
                'jinja2.ext.do',
                'jinja2.ext.loopcontrols',
            ],
        )

        # Load custom Jinja2 filters and tests.
        jinja_path = os.path.join(project_root, '.jinja')
        if os.path.exists(jinja_path):
            sys.path.insert(0, jinja_path)

            filters_path = os.path.join(jinja_path, 'filters')
            for module_finder, name, ispkg in pkgutil.iter_modules(path=[filters_path]):
                module = importlib.import_module('filters.'+ name)
                for name in getattr(module, '__all__', []):
                    env.filters[name] = getattr(module, name)

            tests_path = os.path.join(jinja_path, 'tests')
            for module_finder, name, ispkg in pkgutil.iter_modules(path=[tests_path]):
                module = importlib.import_module('tests.'+ name)
                for name in getattr(module, '__all__', []):
                    env.tests[name] = getattr(module, name)

        return env

    def _render(self, source):
        try:

            # Create a variables context for the template to use.
            # Include environment variables and the var store which
            # exposes the `var.some_name` Terraform variables.
            context = os.environ.copy()
            context['var'] = self._var_store

            # Render the template.
            with open(source) as open_file:
                template = self._jinja_environment.from_string(open_file.read())
            try:
                rendered = template.render(**context)
            except UndefinedError as error:
                name = self._var_store._get_unresolved_variable()
                if name:
                    error = "'var.{}' cannot be resolved".format(name)
                self._errors.append('{} in {}'.format(error, source))
                return

            # Save rendered templates.
            self._rendered[source] = rendered

            # Parse config.
            try:
                parsed = hcl.loads(rendered)
            except ValueError:
                parsed = {}
                in_comment = False
                for line in rendered:
                    line = line.lstrip()
                    if not line:
                        continue
                    if line.startswith('/*'):
                        in_comment = True
                    elif in_comment:
                        if line.startswith('*/'):
                            in_comment = False
                        elif line.startswith('#'):
                            continue
                        else:
                            log.bad('error parsing {}', source)
                            break

            # Process variables.
            variables = parsed.get('variable', {})
            for name, data in variables.items():
                default = data.get('default', None)
                self._var_store._define_variable(name, default)

            # Process AWS providers.
            provider = parsed.get('provider')
            if provider:
                aws = provider.get('aws')
                if aws:
                    config.aws_provider.update(aws)

            # Process S3 backents.
            terraform = parsed.get('terraform')
            if terraform:
                backend = terraform.get('backend')
                if backend:
                    s3 = backend.get('s3')
                    if s3:
                        config.s3_backend.update(s3)

        finally:
            self._var_store._thread_done()

    def add_template(self, source):
        self._threads.add(Thread(
            target=self._render,
            kwargs={'source': source},
        ))

    def set_variable_value(self, name, value):
        self._var_store._set_variable_value(name, value)

    def start(self):
        threads = self._threads.copy()
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        for error in self._errors:
            log.bad(error)
        success = not bool(self._errors)
        return (success, self._rendered)


def _populate():

    # Create a template renderer that can handle multiple files
    # with variable references between files.
    template_renderer = MultiTemplateRenderer()

    # Discover files to create in the workspace. Files in multiple
    # levels of the project directory tree with the same name will
    # be combined into a single file in the workspace.

    tfvars_files = defaultdict(set)
    tf_files = defaultdict(set)
    other_files = defaultdict(set)

    current = cwd
    while (current + '/').startswith(project_root + '/'):
        for name in sorted(os.listdir(current)):
            if name.startswith('.'):
                continue
            path = os.path.join(current, name)
            if os.path.isdir(path):
                continue
            name = name.lower()
            if name.endswith('.tfvars'):
                tfvars_files[name].add(path)
            elif name.endswith('.tf'):
                tf_files[name].add(path)
            else:
                other_files[name].add(path)
        current = os.path.dirname(current)

    # Process .tfvars files first, and read their variable values,
    # because they are required when rendering .tf files.

    for name in sorted(tfvars_files):

        source_paths = sorted(tfvars_files[name])
        target_path = os.path.join(workspace_dir, name)

        if len(source_paths) == 1:
            log.ok('copy: {}', name)
        else:
            log.ok('combine: {}', name)

        with open(target_path, 'w') as output_file:

            for source_path in source_paths:

                with open(source_path) as source_file:
                    source_file_contents = source_file.read()

                relative_source_path = os.path.relpath(source_path, project_root)
                output_file.write('# jinjaform: {}'.format(relative_source_path))
                output_file.write('\n\n')
                output_file.write(source_file_contents)
                output_file.write('\n')

                if name == 'terraform.tfvars':
                    for key, value in hcl.loads(source_file_contents).items():
                        template_renderer.set_variable_value(key, value)

    # Process .tf files as templates.

    for name in sorted(tf_files):

        source_paths = sorted(tf_files[name])

        log.ok('render: {}', name)

        for source_path in source_paths:
            template_renderer.add_template(source_path)

    success, rendered = template_renderer.start()
    if not success:
        sys.exit(1)

    for name in sorted(tf_files):

        source_paths = sorted(tf_files[name])
        target_path = os.path.join(workspace_dir, name)

        with open(target_path, 'w') as output_file:

            for source_path in source_paths:

                relative_source_path = os.path.relpath(source_path, project_root)
                output_file.write('# jinjaform: {}'.format(relative_source_path))
                output_file.write('\n\n')
                output_file.write(rendered[source_path])
                output_file.write('\n')

    # Process remaining files. Do not add source comments because
    # the file format is unknown (e.g. json files would break with #).
    for name in sorted(other_files):

        source_paths = sorted(other_files[name])
        target_path = os.path.join(workspace_dir, name)

        if len(source_paths) == 1:
            log.ok('copy: {}', name)
        else:
            log.ok('combine: {}', name)

        with open(target_path, 'w') as output_file:
            for source_path in source_paths:
                with open(source_path) as source_file:
                    output_file.write(source_file.read())


def _remove(path):
    with suppress(FileNotFoundError):
        if os.path.islink(path):
            os.remove(path)
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)


def clean():
    if os.path.exists(workspace_dir):
        for name in os.listdir(workspace_dir):
            if name != '.terraform':
                _remove(os.path.join(workspace_dir, name))


def create():
    # Ensure the .jinjaform/.terraform directory exists.
    os.makedirs(terraform_dir, exist_ok=True)

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

    # Populate workspace with Terraform configuration files.
    _populate()
