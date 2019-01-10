import hcl
import os
import shutil
import sys

from collections import defaultdict, OrderedDict
from contextlib import suppress

from itertools import chain

from jinja2 import StrictUndefined, Template
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

    def _render(self, source, dest):
        try:

            # Create a variables context for the template to use.
            # Include environment variables and the var store which
            # exposes the `var.some_name` Terraform variables.
            context = os.environ.copy()
            context['var'] = self._var_store

            # Render the template.
            with open(source) as open_file:
                template = Template(
                    open_file.read(),
                    undefined=StrictUndefined,
                    keep_trailing_newline=True,
                )
            try:
                rendered = template.render(**context)
            except UndefinedError as error:
                name = self._var_store._get_unresolved_variable()
                if name:
                    error = "'var.{}' cannot be resolved".format(name)
                self._errors.append('{} in {}'.format(error, source))
                return

            # Write to disk.
            with open(dest, 'w') as open_file:
                open_file.write(rendered)

            # Parse config.
            parsed = hcl.loads(rendered)

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

    def add_template(self, source, dest):
        self._threads.add(Thread(
            target=self._render,
            kwargs={'source': source, 'dest': dest},
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
        return not bool(self._errors)


def _populate():

    template_renderer = MultiTemplateRenderer()

    # Discover files to create.
    files = defaultdict(OrderedDict)
    seen = set()
    current = cwd
    while (current + '/').startswith(project_root + '/'):
        for name in sorted(os.listdir(current)):
            if name in seen or name.startswith('.'):
                continue
            path = os.path.join(current, name)
            if os.path.isdir(path):
                continue
            _, ext = os.path.splitext(name)
            files[ext.lower()][name] = path
            seen.add(name)
        current = os.path.dirname(current)

    # Combine .tfvars files.
    tfvars_files = files.pop('.tfvars', None)
    if tfvars_files:
        with open(os.path.join(workspace_dir, 'terraform.tfvars'), 'w') as output_file:
            for name, source in reversed(tfvars_files.items()):
                log.ok('combine: {}', name)
                with open(source) as source_file:
                    content = source_file.read()
                output_file.write(content)
                output_file.write('\n')
                for key, value in hcl.loads(content).items():
                    template_renderer.set_variable_value(key, value)

    # Render .tf files.
    tf_files = files.pop('.tf', None)
    if tf_files:
        for name, source in tf_files.items():
            log.ok('render: {}', name)
            template_renderer.add_template(
                source=source,
                dest=os.path.join(workspace_dir, name),
            )
        success = template_renderer.start()
        if not success:
            sys.exit(1)

    # Link any other files.
    for ext in files:
        for name, source in files[ext].items():
            log.ok('link: {}', name)
            os.symlink(
                os.path.relpath(source, workspace_dir),
                os.path.join(workspace_dir, name),
            )


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

    # Create a .root symlink to the project root directory
    # so that Terraform code can access it using a relative path.
    root_link = os.path.join(workspace_dir, '.root')
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

    # Populate workspace with Terraform configuration files.
    _populate()
