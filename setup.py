#!/usr/bin/env python
import sys
import os
import re
from setuptools import setup

try:
    from semantic_release import setup_hook
    setup_hook(sys.argv)
except ImportError:
    pass


def read(filename):
    return open(os.path.join(os.path.dirname(__file__), filename)).read()


version = re.search(r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]', read('simple_elastic/__init__.py'), re.MULTILINE).group(1)

long_description = read('README.rst')

setup(
    name='simple-elastic',
    packages=['simple_elastic'],
    version=version,
    description='A simple wrapper for the elasticsearch package.',
    author='Jonas Waeber',
    author_email='jonaswaeber@gmail.com',
    install_requires=['elasticsearch'],
    url='https://github.com/UB-UNIBAS/simple-elastic',
    long_description=long_description,
    download_url='https://github.com/UB-UNIBAS/simple-elastic/archive/v' + version + '.tar.gz',
    keywords=['elasticsearch', 'elastic'],
    classifiers=[],
    license='MIT'
)