"""In this example, we use fieldcompare to compare fields on computational meshes"""

# we use meshio here to show how to achieve interoperability
from meshio import read as meshio_read

from fieldcompare import FieldDataComparison

# Convenience function to read fields from files
from fieldcompare.field_io import read

# Sorting function to yield a unique permutation of mesh fields
from fieldcompare.mesh import sort

# Further available permutations for fields on meshes
from fieldcompare.mesh import permutations

# Protocols you can use for type hints
from fieldcompare.mesh import protocols

# Compatibility functions for meshio
from fieldcompare.mesh import meshio_utils


def read_as_mesh_fields(filename: str) -> protocols.MeshFields:
    # The read function can read different kinds of field data,
    # as well as field data sequences. Thus in this case and for
    # the sake of type hints, we have to verify that we obtained
    # # something that fulfills our required interface
    fields = read(filename)
    assert isinstance(fields, protocols.MeshFields)
    return fields


mesh_file = "mesh_data.vtu"
mesh_file_permuted = "mesh_data_permuted.vtu"

fields: protocols.MeshFields = read_as_mesh_fields(mesh_file)
fields_permuted: protocols.MeshFields = read_as_mesh_fields(mesh_file_permuted)

# The two meshes contain the same data, but in different order,
# thus, the meshes are not equal. In such case, the field data
# comparison exits early, yielding a "failed" comparison:
comparator = FieldDataComparison(fields, fields_permuted)
result = comparator()

assert not result
print("Comparison failed! Domain equality check report:")
print(result.domain_equality_check.report)
print()

# We can solve this in this case by sorting the mesh in a unique way:
fields_sorted = sort(fields)
fields_permuted_sorted = sort(fields_permuted)
comparator = FieldDataComparison(fields_sorted, fields_permuted_sorted)
result = comparator()

assert result
print("Domain equality check passed!")
for comparison in comparator():
    print(f"Field '{comparison.name}': {comparison.status}")

# The sort function is shorthand for removing unconnected points,
# then sorting the points and finally sorting the cells:
def _manual_sort(_fields: protocols.MeshFields) -> protocols.MeshFields:
    return _fields.transformed(
        permutations.remove_unconnected_points
    ).transformed(
        permutations.sort_points
    ).transformed(
        permutations.sort_cells
    )
fields_sorted = _manual_sort(fields)
fields_permuted_sorted = _manual_sort(fields_permuted)
assert FieldDataComparison(fields_sorted, fields_permuted_sorted)()

# In our case here, sorting only the points does not yield equal meshes:
fields_sorted = fields.transformed(permutations.sort_points)
fields_permuted_sorted = fields_permuted.transformed(permutations.sort_points)
assert not FieldDataComparison(fields_sorted, fields_permuted_sorted)()

# Note that there are conversion functions available for meshio meshes
# such that you can integrate fieldcompare into an existing pipeline
# that relies on meshio.
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
