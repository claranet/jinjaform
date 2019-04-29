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

        self._running = True
        self._lock = Lock()
        self._threads = threads
        self._threads_waiting = defaultdict(dict)
        self._variables_waiting = defaultdict(list)

        self._defined = set()
        self._defaults = dict()
        self._values = dict()

        self._unresolved = defaultdict(set)

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
        self._unresolved[current_thread()].add(key)
        raise KeyError(key)

    def _cancel(self):
        """
        This function will unblock all threads waiting on a variable,
        allowing them to continue executing without their variable.
        They will then have an error because the variable isn't defined.

        """

        self._running = False
        for event in chain.from_iterable(self._variables_waiting.values()):
            event.set()

    def _check_deadlock(self):
        """
        Checks if there are any free threads. If all threads are blocked
        waiting for variables to be defined, then no more variables will
        be defined and the threads will never finish rendering. In that
        case, cancel rendering and allow errors to be raised.

        """

        for thread in self._get_free_threads():
            break
        else:
            self._cancel()

    def _define_variable(self, name, default):
        """
        Adds a variable definition and unblocks any waiting threads.

        """

        with self._lock:
            self._defined.add(name)
            if default is not None:
                self._defaults[name] = default
            for event in self._variables_waiting.pop(name, []):
                event.set()

    def _get_free_threads(self):
        """
        Returns all threads which are not currently waiting for a variable
        to be defined. These are important when determining if there is
        a deadlock; if all threads are blocked waiting for variables to
        be defined, then no more variables will be define and the threads
        will never unblock by themselves.

        """

        # Return nothing if the rendering has been cancelled.
        if not self._running:
            return

        # Check all running threads.
        for thread in self._threads:
            for name in self._threads_waiting[thread].values():
                if name not in self._defined:
                    # This thread is waiting on a variable which hasn't been
                    # defined yet, so it is not free.
                    break
            else:
                # This thread is no waiting on any variables that haven't
                # been defined yet, so it is free.
                yield thread

    def _get_unresolved_variables(self):
        return sorted(self._unresolved.get(current_thread(), set()))

    def _set_variable_value(self, name, value):
        self._values[name] = value

    def _thread_done(self):
        """
        Removes the current thread and checks for a deadlock.

        """

        with self._lock:
            self._threads.remove(current_thread())
            self._check_deadlock()

    def _wait_for_variable(self, name):
        """
        Waits for a variable to be defined in another template being rendered
        by another thread. Returns immediately if it is already defined.

        """

        with self._lock:

            if name in self._defined:
                return

            # Check if there are any other threads that aren't waiting on
            # a variable. These other threads may end up defining this
            # variable, or they may not. If there are no free threads
            # then there is no way for the variable to be defined, so
            # cancel the rendering and allow an error to be raised.
            for thread in self._get_free_threads():
                if thread != current_thread():
                    break
            else:
                self._cancel()
                return

            # Create an event that will be used to block execution
            # in this thread until another thread unblocks it.
            event = Event()

            # Add a reference to the event by the variable name.
            # This allows another thread that defines the variable
            # to find this thread and unblock it.
            self._variables_waiting[name].append(event)

            # Add a reference to the event by the thread.
            # This allows other threads to check if this
            # thread is blocked or not.
            self._threads_waiting[current_thread()][event] = name

        # Wait for the variable to be defined,
        # or for rendering to be cancelled.
        event.wait()

        with self._lock:

            # Remove the reference so this thread can be seen as free.
            self._threads_waiting[current_thread()].pop(event)

            # Check if the rendering is in a deadlock.
            self._check_deadlock()


class MultiTemplateRenderer(object):

    def __init__(self):
        self._threads = set()
        self._var_store = VarStore(self._threads)
        self._errors = []
        self._rendered = {}
        self._jinja_context = {}
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

        # Create a context for the template to use.
        # Include environment variables and the var store which
        # exposes the `var.some_name` Terraform variables.
        # Custom context values will be added below too.
        self._jinja_context.update(os.environ)
        self._jinja_context['var'] = self._var_store

        # Load Jinja2 extensions.
        jinja_path = os.path.join(project_root, '.jinja')
        if os.path.exists(jinja_path):
            sys.path.insert(0, jinja_path)

            context_path = os.path.join(jinja_path, 'context')
            for module_finder, name, ispkg in pkgutil.iter_modules(path=[context_path]):
                module = importlib.import_module('context.' + name)
                for name in getattr(module, '__all__', []):
                    self._jinja_context[name] = getattr(module, name)

            filters_path = os.path.join(jinja_path, 'filters')
            for module_finder, name, ispkg in pkgutil.iter_modules(path=[filters_path]):
                module = importlib.import_module('filters.' + name)
                for name in getattr(module, '__all__', []):
                    env.filters[name] = getattr(module, name)

            tests_path = os.path.join(jinja_path, 'tests')
            for module_finder, name, ispkg in pkgutil.iter_modules(path=[tests_path]):
                module = importlib.import_module('tests.' + name)
                for name in getattr(module, '__all__', []):
                    env.tests[name] = getattr(module, name)

        return env

    def _render(self, source):
        try:

            # Render the template.
            with open(source) as open_file:
                template = self._jinja_environment.from_string(open_file.read())
            try:
                rendered = template.render(**self._jinja_context)
            except UndefinedError as error:
                for name in self._var_store._get_unresolved_variables():
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
