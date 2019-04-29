#!/usr/bin/env python

from setuptools import setup

import jinjaform


setup(
    name='jinjaform',
    version=jinjaform.__version__,
    description='Jinja2 Terraform wrapper',
    author='Raymond Butcher',
    author_email='ray.butcher@claranet.uk',
    url='https://github.com/claranet/jinjaform',
    license='MIT License',
    packages=(
        'jinjaform',
    ),
    entry_points = {
        'console_scripts': (
            'jinjaform=jinjaform.__main__:main',
        ),
    },
    install_requires=(
        'boto-source-profile-mfa>=0.0.4'
        'boto3',
        'botocore>=1.8.14',
        'colorama',
        'Jinja2',
        'pyhcl',
    ),
)
