import os
import sys
import subprocess

from jinjaform import log
from jinjaform.config import args


def abort():
    if os.environ.get('GIT_CHECK') == '0':
        pass
    else:
        log.bad('git: refusing to continue')
        log.ok('hint: set GIT_CHECK=0 to bypass git checks')
        sys.exit(1)


def check_branch(desired):

    if 'apply' not in args:
        return

    branch = subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD']).rstrip().decode('utf-8')
    if branch != desired:
        log.bad('git: working in branch {}', branch)
        log.bad('git: should be in branch {}', desired)
        abort()


def check_clean():

    if 'apply' not in args:
        return

    diff = subprocess.check_output(['git', 'status', '--porcelain']).rstrip().decode('utf-8')
    if diff:
        log.bad('git: working directory not clean')
        for line in diff.splitlines():
            log.bad('git: {}', line)
        abort()


def check_remote():

    if 'apply' not in args:
        return

    log.ok('git: checking remote')
    subprocess.check_output(['git', 'remote', 'update'])
    local = subprocess.check_output(['git', 'rev-parse', 'HEAD']).rstrip().decode('utf-8')

    try:
        remote = subprocess.check_output(
            ['git', 'rev-parse', '@{upstream}'],
            stderr=subprocess.STDOUT,
        ).rstrip().decode('utf-8')
    except subprocess.CalledProcessError as error:
        # There may not be any upstream configured for the branch.
        output = error.output.rstrip().decode('utf-8')
        log.bad('git: {}', output)
        abort()
    else:
        if local != remote:
            status = subprocess.check_output(['git', 'status']).rstrip().decode('utf-8')
            for line in status.splitlines():
                if 'branch' in line and ('ahead' in line or 'behind' in line):
                    log.bad('git: {}', line.lower())
                    break
            else:
                log.bad('git: out of date')
            abort()
