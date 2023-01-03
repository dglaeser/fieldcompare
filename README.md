[![fieldcompare Logo](https://gitlab.com/dglaeser/fieldcompare/-/raw/9018885c0c8675c63c051ae5119a5ecba465a517/logo/logo.svg)](https://dglaeser.gitlab.io/fieldcompare/)

# FieldCompare

[![Project Status: Active – The project has reached a stable, usable state and is being actively developed.](https://www.repostatus.org/badges/latest/active.svg)](https://www.repostatus.org/#active)
[![Test Pipelines.](https://gitlab.com/dglaeser/fieldcompare/badges/main/pipeline.svg)](https://gitlab.com/dglaeser/fieldcompare/-/pipelines?page=1&scope=all&ref=main)
[![Coverage Report.](https://gitlab.com/dglaeser/fieldcompare/badges/main/coverage.svg)](https://dglaeser.gitlab.io/fieldcompare/coverage)
[![API Documentation.](https://img.shields.io/badge/doc-API-ff69b4)](https://dglaeser.gitlab.io/fieldcompare/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)


`fieldcompare` is a python package with command-line interface (CLI) that can be used to compare
datasets for (fuzzy) equality. It was designed mainly to serve as a tool to realize regression tests
for research software, and in particular research software that deals with numerical simulations.
In regression tests, the output of a software is compared to reference data that was produced by
the same software at an earlier time, in order to detect if changes to the code cause unexpected
changes to the behavior of the software.

Simulations typically produce discrete field data defined on computational grids, and there exists
a variety of standard and widely-used file formats. `fieldcompare` supports a number of
[VTK file formats](https://kitware.github.io/vtk-examples/site/VTKFileFormats/) out-of-the box,
a variety of further formats can be used with the help of [meshio](https://github.com/nschloe/meshio).
Besides mesh files, `csv` files are also supported, a format that is widely used in simulation
frameworks to write out secondary data such as e.g. error norms and convergence rates.

Independent of the file type and format, `fieldcompare` reads all _fields_ from those files and allows
you to then check all entries of the fields for equality with custom absolute and relative tolerances.
Programmatically, you can provide and use custom predicates (e.g. "smaller-than"), while the
CLI is currently hardwired to (fuzzy) equality checks, which is the most common use case.

A common issue with regression testing of grid files is that the grid may be written with a different
ordering of points or cells, while the actual field data on the grid may be the same. To this end,
`fieldcompare` provides the option to make the fields read from a grid unique by sorting the grid
by its point coordinates and cell connectivity. Moreover, one can choose to strip the grid from
ghost points, that may occur, for instance, upon merging the data from multiple grid partitions
distributed over different processors.


# GitHub Action

If you want to use `fieldcompare` in your GitHub actions, you may want to check out our
[fieldcompare action](https://github.com/dglaeser/action-field-compare), which allows you to easily
perform regression tests within your GitHub workflows.


# Getting started

## Installation

Via `pip`, you can install `fieldcompare` directly from the git repository with

```sh
pip install "git+https://gitlab.com/dglaeser/fieldcompare#egg=fieldcompare[all]
```

The suffix `[all]` instructs `pip` to also install all optional dependencies (for instance `meshio`).
Omit this suffix if you want to install only the required dependencies.

For an installation from a local copy, navigate to the top folder of this repository and type
`pip install .`, or , `pip install .[all]` for an installation with all optional dependencies.

## First steps & examples

The following code snippet reads the fields from two files (assuming their format is supported)
and prints a message depending on if the success of their comparison:

```py
from fieldcompare import FieldDataComparator
from fieldcompare.io import read_field_data

fields1 = read_field_data("FILENAME1")
fields2 = read_field_data("FILENAME2")
comparator = FieldDataComparator(fields1, fields2)

if comparator():
    print("Comparison PASSED")
else:
    print("Comparison failed")
```

There are many more options you may use, and infos you can collect on performed comparisons. In the
folder [examples/api](examples/api) you can find examples with instructions on how to use the API of
`fieldcompare`.


## Command-line interface

The CLI exposes two subcommands, namely `file` and `dir`, where the former is used to compare two files
for equality, and the latter can be used to compare all files with matching names in two given directories.
That is, type

```sh
fieldcompare file PATH_TO_FILE --reference PATH_TO_REFERENCE_FILE
```

to compare two files, and


```sh
fieldcompare dir PATH_TO_DIR --reference PATH_TO_REFERENCE_DIR
```

for comparing two directories. The latter command will scan both folders for files with matching names,
and then run a file comparison on pairs of matching files. This can be useful if your simulation produces
a number of files for which you have references stored in some reference folder, and you want to compare
them all in a single command. For more info on the CLI options available, type in

```sh
fieldcompare file --help
fieldcompare dir --help
```


# Contribution Guidelines

Contributions are highly welcome! For bug reports, please file an [issue](https://gitlab.com/dglaeser/fieldcompare/-/issues).
If you want to contribute with features, improvements or bug fixes please fork this project and open
a merge request into the main branch of this repository.


# License

`fieldcompare` is licensed under the terms and conditions of the GNU General
Public License (GPL) version 3 or - at your option - any later version. The GPL
can be [read online](https://www.gnu.org/licenses/gpl-3.0.en.html) or in the
[LICENSE.txt](LICENSE.txt) file in this repository. See [LICENSE.txt](LICENSE.txt)
for full copying permissions.
