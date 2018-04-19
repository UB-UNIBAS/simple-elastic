#!/usr/bin/env python

from distutils.core import setup

setup(
    name='selastic',
    packages=['selastic'],
    version='v0.1',
    description='A simple wrapper for the elasticsearch package.',
    author='Jonas Waeber',
    author_email='jonaswaeber@gmail.com',
    install_requires=['elasticsearch'],
    url='https://github.com/UB-UNIBAS/simple-elastic',
    download_url='https://github.com/UB-UNIBAS/simple-elastic/archive/v0.1.tar.gz',
    keywords=['elasticsearch', 'elastic'],
    classifiers=[],
    license='MIT'
)