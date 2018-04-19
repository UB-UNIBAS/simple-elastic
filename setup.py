#!/usr/bin/env python

from distutils.core import setup
from .selastic import __version__

setup(
    name='simple-elastic',
    packages=['selastic'],
    version=__version__,
    description='A simple wrapper for the elasticsearch package.',
    author='Jonas Waeber',
    author_email='jonaswaeber@gmail.com',
    install_requires=['elasticsearch'],
    url='https://github.com/UB-UNIBAS/simple-elastic',
    download_url='https://github.com/UB-UNIBAS/simple-elastic/archive/v' + __version__ + '.tar.gz',
    keywords=['elasticsearch', 'elastic'],
    classifiers=[],
    license='MIT'
)