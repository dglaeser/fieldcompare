# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys
sys.path.insert(0, os.path.abspath('../..'))


# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'fieldcompare'
copyright = '2022, Dennis Gläser'
author = 'Dennis Gläser'
release = '1.0.0'


# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
    'sphinx_mdinclude',
    'sphinx.ext.napoleon'
]

templates_path = ['_templates']
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'pydata_sphinx_theme'
html_logo = "https://gitlab.com/dglaeser/fieldcompare/-/raw/main/logo/logo.svg"
html_theme_options = {
    "logo": {
        "image_light": "https://gitlab.com/dglaeser/fieldcompare/-/raw/main/logo/logo.svg",
        "image_dark": "https://gitlab.com/dglaeser/fieldcompare/-/raw/main/logo/logo_white.svg"
    }
}

# -- Options for extensions ---
# typehints_fully_qualified = True
autodoc_typehints = "description"
autodoc_type_aliases = {
    'ArrayLike': 'numpy.ArrayLike'
}
autodoc_preserve_defaults = True
autodoc_default_options = {
    'member-order': 'bysource',
    'undoc-members': True,
    'show-inheritance': False,
    'special-members': '__call__, __bool__, __iter__'
}
