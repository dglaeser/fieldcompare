#!/usr/bin/env python3

"""Installation procedure for fieldcompare"""

from distutils.core import setup
from setuptools import find_packages

setup(
    name="fieldcompare",
    version="1.0",
    author="Dennis Gläser",
    author_email="dennis.glaeser@iws.uni-stuttgart.de",
    url="https://gitlab.com/dglaeser/fieldcompare",
    packages=find_packages(where="."),
    python_requires=">3.8.0",
    install_requires=["meshio[all]>=4.4", "colorama>=0.4.3"],
    entry_points={
        'console_scripts': ['fieldcompare=fieldcompare._cli:main'],
    }
)
