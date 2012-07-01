#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

try:
    from setuptools import setup
    setup
except ImportError:
    from distutils.core import setup

if sys.argv[-1] == 'publish':
    os.system('python setup.py sdist upload')
    sys.exit()

execfile('pycaustic/version.py')

packages = ['pycaustic']

setup(
    name='pycaustic',
    version=__version__,
    description='Python adaptation of Caustic',
    long_description=open('README.md').read(),
    author='John Krauss',
    author_email='john@accursedware.com',
    url='http://github.com/talos/pycaustic',
    packages=packages,
    license='BSD',
    classifiers=(
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7'
    ),
)
