import errno
import os
import subprocess
import sys


def execute(terraform_bin, args, env):
    child_pid = os.fork()
    if child_pid == 0:
        os.execvpe(terraform_bin, [terraform_bin] + args, env)
    else:
        while True:
            try:
                _, exit_status = os.waitpid(child_pid, 0)
            except KeyboardInterrupt:
                pass
            except OSError as error:
                if error.errno == errno.ECHILD:
                    # No child processes.
                    # It has exited already.
                    break
                elif error.errno == errno.EINTR:
                    # Interrupted system call.
                    # This happens when resizing the terminal.
                    pass
                else:
                    # An actual error occurred.
                    raise
            else:
                return exit_status


def fmt(terraform_bin, name, _cache={}):
    """
    Runs `terraform fmt` on some input text and returns the result.

    """

    if name not in _cache:
        try:
            with open(name) as open_file:
                proc = subprocess.run(
                    [terraform_bin, 'fmt', '-'],
                    stdout=subprocess.PIPE,
                    input=open_file.read().encode('utf-8'),
                    check=True,
                )
        except subprocess.CalledProcessError as error:
            sys.exit(error.returncode)
        else:
            _cache[name] = proc.stdout.decode('utf-8')
    return _cache[name]
