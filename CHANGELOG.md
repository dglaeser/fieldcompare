<!--SPDX-FileCopyrightText: 2023 Dennis Gläser <dennis.glaeser@iws.uni-stuttgart.de>-->
<!--SPDX-License-Identifier: GPL-3.0-or-later-->

# `fieldcompare` 0.5.0 (unreleased)

# `fieldcompare` 0.4.0

## New features

- __CLI__: The default behaviour for files that have an unsupported file format has been changed. So far, such file comparisons were treated as skipped, which could lead to unexpected false positives. These files are now treated as failures, and a new option '--ignore-unsupported-file-formats'  has been added to recover the old behaviour.

## Interface changes

- __FieldComparison__: the `__bool__` operator of `FieldComparisonStatus` has been removed (raises an exception now), and only three states are now distinguished: `failed`, `passed` and `skipped`. The possible reasons for failure or skipping have been moved to a separate data structure. The default behaviour is now also stricter; skipped comparisons where the source or reference fields are missing are no longer considered to be successful per default. The `FieldDataComparator` and/or the `MeshFieldsComparator` classes expose a customization point via  the `missing_sources_is_error` or `missing_references_is_error` options in their constructors. Moreover, the provided field comparison callback is invoked with any filtered or skipped fields when comparing two files.

- __FieldComparisonSuite__: the `status` interface has been removed as it's behaviour is identical to the `__bool__` operator.

# `fieldcompare` 0.3.0

## New features

- __CLI__: An `--exclude-files` option was added to the cli directory mode, that allows for discarding certain files from the comparisons. In use cases where only a few files should be neglected, this is easier than constructing an inclusion pattern that these files would _not_ match.
- __CLI__: A final info line was added to the cli directory mode, which displays how many files with missin reference/source files have been discarded due to the given inclusion/exclusion patterns.
- __CLI__: An intermediate verbosity level has been introduced for the cli directory mode which only prints the directories that are compared and a final summary.

# `fieldcompare` 0.2.2

## Bugfixes

- __Setup__: the setup configuration was modified such that an upper bound (the next major version) is specified for the dependencies. This ensures that compatible dependency versions are installed also after incompatible new major releases have been released.
- __Setup__: `fieldcompare` is now compatible with the new major release of `numpy` (v2.0).

# `fieldcompare` 0.2.1

## Bugfixes

- __Structured Mesh__: the ordering of corners for pixels and voxels was fixed to be in line with the VTK ordering for these cell types. The previously differing connectivity led to erroneous VTU files when writing out a read structured mesh as unstructured grid.
- __Structured Mesh__: works in 3d now after fixing the computation of the number of cell corners depending on the grid dimension.

# `fieldcompare` 0.2.0

## New Features

- __I/O__: output capabilities for tabular and mesh field data was added. The former is written into `.csv` files, while for the latter a writer for the `.vtu` file format was added.
- __FieldData__: The `FieldData` protocol was enhanced by a `diff_to` function that computes the difference to given data. That is, `my_field_data.diff_to(reference)` returns a `FieldData` object that contains the differences `reference_${FIELD} - my_field_data_${FIELD}`.
Both `MeshFields` and `TabularFields` have been enhanced by corresponding implementations. An example for computing and writing the diff between to `FieldData` instances may look like this:
```py
from fieldcompare.io import write, read_field_data
from fieldcompare.mesh import sort

source = read_field_data("../test/data/test_mesh.vtu")
reference = read_field_data("../test/data/test_mesh_permutated_perturbed.vtu")
# sorting is NOT done implicitly, so we do it manually here since a diff can
# only be computed on (fuzzy-)equal meshes (and the two used here are not equal)
diff = sort(source).diff(sort(reference))
write(diff, "diff_file")
```
- __CLI__: The cli (both `file` and `dir` mode) was enhanced to take a `--diff` flag. If used, the difference between the fields for each pair of compared files is written to disk next to the source fields file (with prefix `diff_`).
- __I/O__: readers for the structured grid VTK file formats (`.vti`/`.pvti`, `.vtr`/`.pvtr`, `.vts`/`.pvts`) are now available.
