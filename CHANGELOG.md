<!--SPDX-FileCopyrightText: 2023 Dennis Gläser <dennis.glaeser@iws.uni-stuttgart.de>-->
<!--SPDX-License-Identifier: GPL-3.0-or-later-->


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
