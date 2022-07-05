[![Project Status: Active – The project has reached a stable, usable state and is being actively developed.](https://www.repostatus.org/badges/latest/active.svg)](https://www.repostatus.org/#active)

[![Test Pipelines.](https://gitlab.com/dglaeser/fieldcompare/badges/main/pipeline.svg)](https://gitlab.com/dglaeser/fieldcompare/-/pipelines?page=1&scope=all&ref=main)

[![Coverage Report.](https://gitlab.com/dglaeser/fieldcompare/badges/main/coverage.svg)](https://dglaeser.gitlab.io/fieldcompare/)


# FieldCompare

`fieldcompare` is a python package with command-line interface (CLI) that can be used, generally, to compare
datasets with a focus on checking for fuzzy equality. It was designed mainly to serve as a tool to realize
regression tests for research software, and in particular research software that deals with numerical
simulations. An easy and widely-used approach to verify that simulation software still produces the same
results as prior to a particular change in the code is to compare newly obtained results with stored
reference data. Therefore, `fieldcompare` uses [meshio](https://github.com/nschloe/meshio) under the
hood to read in data from a variety of mesh files into the data structures that can be used for comparisons
with `fieldcompare`. Besides those, `csv` files are also supported, a format that is widely used in
simulation frameworks to write out secondary data such as e.g. error norms and convergence rates.

Independent of the file type and format, `fieldcompare` reads all "fields" from those files and allows
you to then check all entries of the fields for equality with custom absolute and relative tolerances.
Programmatically, you can also use predicates different from equality (e.g. "smaller-than"), while the
CLI is currently hardwired to equality checks, which is the most common use case.

A common issue with regression testing of mesh files is that the mesh may be written with a different
ordering of points or cells, while the actual field data on the mesh may be the same. To this end,
`fieldcompare` provides the option to make the fields read from a mesh unique by sorting the mesh
after its point coordinates and cell connectivity. Moreover, one can choose to strip the mesh from
ghost points,that may occur, for instance, upon merging the data from multiple grid partitions
distributed over different processors.


# Installation

After cloning this repository, you can simply install `fieldcompare` via pip by navigating to the top
folder of this repository and then typing `python -m pip install .`. In case you don't want to install
into your system, you can simply create a virtual environment beforehand using [venv](https://docs.python.org/3/library/venv.html).
This will also install the CLI, which is then available as the `fieldcompare` command.


# Command-line interface

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

The latter command will scan both folders for files with matching names, and then run a file comparison on
pairs of matching files. This can be useful if your simulation produces a number of files for which you
have references stored in some reference folder, and you want to compare them all in a single command.
For more info on the CLI options available, type in

```sh
fieldcompare file --help
fieldcompare dir --help
```


# Examples

In [examples/api] you can find a few examples with instructions on how to use the API of `fieldcompare`.
However, the examples do not cover some of the more advanced functions and classes, but we are planning
to add more examples soon.


# Contribution Guidelines

Contributions are highly welcome! For bug reports, please file an [issue](https://gitlab.com/dglaeser/fieldcompare/-/issues).
If you want to contribute with features, improvements or bug fixes please fork this project and open
a merge request into the main branch of this repository.


# License

`fieldcompare` is licensed under the terms and conditions of the GNU General
Public License (GPL) version 3 or - at your option - any later version. The GPL
can be [read online][https://www.gnu.org/licenses/gpl-3.0.en.html] or in the
[LICENSE.md](LICENSE.txt) file in this repository. See [LICENSE.md](LICENSE.md)
for full copying permissions.

