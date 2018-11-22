import os
import sys
import subprocess

from jinjaform import log
from jinjaform.config import args


def abort():
    if os.environ.get('GIT_FORCE') == '1':
        pass
    else:
        log.bad('git: refusing to continue')
        log.ok('hint: set GIT_FORCE=1 to bypass git checks')
        sys.exit(1)


def check():

    if 'apply' not in args:
        return

    branch = subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD']).rstrip().decode('utf-8')
    if branch != 'master':
        log.bad('git: working in branch {}', branch)
        abort()
        return

    diff = subprocess.check_output(['git', 'status', '--porcelain']).rstrip().decode('utf-8')
    if diff:
        log.bad('git: working directory not clean')
        for line in diff.splitlines():
            log.bad('git: {}', line)
        abort()
        return

    log.ok('git: checking origin')
    subprocess.check_output(['git', 'remote', 'update'])
    local = subprocess.check_output(['git', 'rev-parse', 'master']).rstrip().decode('utf-8')
    remote = subprocess.check_output(['git', 'rev-parse', 'origin/master']).rstrip().decode('utf-8')
    if local != remote:
        status = subprocess.check_output(['git', 'status']).rstrip().decode('utf-8')
        for line in status.splitlines():
            if 'branch' in line and ('ahead' in line or 'behind' in line):
                log.bad('git: {}', line.lower())
                break
        else:
            log.bad('git: master is out of date')
        abort()
        return
