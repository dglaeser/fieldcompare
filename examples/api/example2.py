# SPDX-FileCopyrightText: 2023 Dennis Gläser <dennis.glaeser@iws.uni-stuttgart.de>
# SPDX-License-Identifier: GPL-3.0-or-later

"""In this example, we use fieldcompare to compare fields on computational meshes"""

# we use meshio here to show how to achieve interoperability
from meshio import read as meshio_read

from fieldcompare import FieldDataComparator

# Convenience function to read fields from files
from fieldcompare.io import read_field_data

# Sorting function to yield a unique permutation of mesh fields
from fieldcompare.mesh import sort, sort_points, sort_cells, strip_orphan_points, MeshFieldsComparator

# Protocols you can use for type hints
from fieldcompare.mesh import protocols

# Compatibility functions for meshio
from fieldcompare.mesh import meshio_utils


def read_as_mesh_fields(filename: str) -> protocols.MeshFields:
    # The read function can read different kinds of field data.
    # In this example we are working with mesh fields, and for
    # the sake of type hints, let us verify that.
    fields = read_field_data(filename)
    assert isinstance(fields, protocols.MeshFields)
    return fields


mesh_file = "mesh_data.vtu"
mesh_file_permuted = "mesh_data_permuted.vtu"

fields: protocols.MeshFields = read_as_mesh_fields(mesh_file)
fields_permuted: protocols.MeshFields = read_as_mesh_fields(mesh_file_permuted)

# The two meshes contain the same data, but in different order,
# thus, the meshes are not equal. In such case, the field data
# comparison exits early, yielding a "failed" comparison:
comparator = FieldDataComparator(fields, fields_permuted)
result = comparator()

assert not result
print(f"Comparison failed! Report: '{result.report}'")
print("Domain equality check report:")
print(result.domain_equality_check.report)
print()

# We can solve this in this case by sorting the mesh in a unique way:
fields_sorted = sort(fields)
fields_permuted_sorted = sort(fields_permuted)
comparator = FieldDataComparator(fields_sorted, fields_permuted_sorted)

print("Retrying with sorted meshes")
result = comparator(fieldcomp_callback=lambda _: None)
assert result
print("Domain equality check passed!")
print("Printing comparisons:")
for comparison in result:
    print(f"Field '{comparison.name}': {comparison.status}")

# The sort function is shorthand for removing unconnected points,
# then sorting the points and finally sorting the cells:
def _manual_sort(_fields: protocols.MeshFields) -> protocols.MeshFields:
    return sort_cells(sort_points(strip_orphan_points(_fields)))

fields_sorted = _manual_sort(fields)
fields_permuted_sorted = _manual_sort(fields_permuted)

print("\nRetrying with manually sorted meshes")
assert FieldDataComparator(fields_sorted, fields_permuted_sorted)(
    fieldcomp_callback=lambda _: None
)
print("Passed!")

# In our case here, sorting only the points does not yield equal meshes:
fields_sorted = sort_points(fields)
fields_permuted_sorted = sort_points(fields_permuted)
print("\nRerunning with sorting only the points of the meshes")
result = FieldDataComparator(fields_sorted, fields_permuted_sorted)(
    fieldcomp_callback=lambda _: None
)
print(f"As expected, the domain equality check failed: {result.domain_equality_check.report}")

# But we don't have to do all that manually, we can reuse the comparator
# class specific to meshes, which (per default), sorts the meshes in
# case they do not compare equal.
print("\nUsing unsorted meshes with 'MeshFieldsComparator'")
assert MeshFieldsComparator(fields, fields_permuted)(fieldcomp_callback=lambda _: None)
print("Passed!")

# The 'MeshFieldsComparator' automatically retries the comparisons with sorted
# meshes in case they are not equal. In order to extract information about the
# sorting attempts it does, you can pass a callback function that will be invoked
# with info on detected deviations and the next attempt made...
print("\nUsing 'MeshFieldsComparator' with full output")
assert MeshFieldsComparator(fields, fields_permuted)(
    reordering_callback=lambda msg: print(f"Reording info: '{msg}'")
)
print("Passed!")

# Note that if you already have an analysis pipeline that uses meshio to read
# in meshes, you can use the provided conversion functions from and to meshio
# instead of using fieldcompare's I/O facilities:
mesh = meshio_read(mesh_file)
mesh_permuted = meshio_read(mesh_file_permuted)

# you can convert the meshes to fieldcompare's "MeshFields" ...
fields = meshio_utils.from_meshio(mesh)
fields_permuted = meshio_utils.from_meshio(mesh_permuted)

# ... sort the fields ...
fields = sort(fields)
fields_permuted = sort(fields_permuted)

# ... and convert them back to meshio
mesh = meshio_utils.to_meshio(fields)
mesh_permuted = meshio_utils.to_meshio(fields_permuted)
