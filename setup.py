#!/usr/bin/env python

from distutils.core import setup
import os
import re
import sys


def read(filename):
    return open(os.path.join(os.path.dirname(__file__), filename)).read()


version = re.search(r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]', read('simple_elastic/__init__.py'), re.MULTILINE).group(1)

if sys.argv[-1] == 'publish':
    os.system("python setup.py sdist")
    os.system('twine upload dist/simple-elastic-{}.tar.gz -r pypi'.format(version))
    sys.exit()

setup(
    name='simple-elastic',
    packages=['simple_elastic'],
    version=version,
    description='A simple wrapper for the elasticsearch package.',
    author='Jonas Waeber',
    author_email='jonaswaeber@gmail.com',
    install_requires=['elasticsearch'],
    url='https://github.com/UB-UNIBAS/simple-elastic',
    download_url='https://github.com/UB-UNIBAS/simple-elastic/archive/v' + version + '.tar.gz',
    keywords=['elasticsearch', 'elastic'],
    classifiers=[],
    license='MIT'
)