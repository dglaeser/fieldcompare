#!/usr/bin/env python3

"""Installation procedure for fieldcompare"""

from distutils.core import setup

setup(
    name="fieldcompare",
    version="1.0",
    author="Dennis Gläser",
    author_email="dennis.glaeser@iws.uni-stuttgart.de",
    url="https://gitlab.com/dglaeser/fieldcompare",
    packages=["fieldcompare"],
    python_requires=">3.8.0",
    install_requires=["meshio[all]>=4.4"],
    entry_points = {
        'console_scripts': ['fieldcompare=fieldcompare._cli:main'],
    }
)
