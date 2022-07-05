"""In this example, we use fieldcompare to read in fields defined on a mesh"""

from fieldcompare import DefaultEquality, read_fields, is_mesh_file, make_mesh_field_reader


mesh_file = "mesh_data.vtu"
mesh_file_permuted = "mesh_data_permuted.vtu"

# we can reuse the "read_fields" function to obtain all fields
# defined on the mesh. Let's print these fields, and we will
# see that there are fields that describes the coordinates
# of the mesh points and the cell corner indices (each cell
# type is stored as a separate field), plus data fields associated
# with points and cells
mesh_fields = read_fields(mesh_file)
for field_name in mesh_fields.field_names:
    print(f"Contains the field {field_name}")

# mesh files are somewhat special, and there are further options
# that can be enabled/disabled for reading mesh files. If you
# know you have a mesh file at hand, you can ask for a field
# reader from mesh files
mesh_field_reader = make_mesh_field_reader(mesh_file)

# on mesh field readers, you have the option to filter out ghost
# points (and all data associated with them), i.e. points that
# are not connected to any elements. In the example mesh there
# are no ghost points.
mesh_field_reader.remove_ghost_points = True

# moreover, you can tell the reader to permute the points and
# point indices such that a unique representation of the grid
# is obtained. This is useful when you want to test two mesh
# files for equality without caring what the exact ordering is
mesh_field_reader.permute_uniquely = True

# if we read in the fields with these options, the fields from
# the permuted and the non-permuted files should evaluate to
# being equal
mesh_fields = mesh_field_reader.read(mesh_file)
mesh_fields_permuted = mesh_field_reader.read(mesh_file_permuted)

equal = DefaultEquality()
for field_name in mesh_fields.field_names:
    print(f"Checking field {field_name} for equality")
    assert equal(
        mesh_fields.get(field_name).values,
        mesh_fields_permuted.get(field_name).values
    )

# without this option, there will be fields that are not equal
mesh_field_reader.permute_uniquely = False
mesh_fields = mesh_field_reader.read(mesh_file)
mesh_fields_permuted = mesh_field_reader.read(mesh_file_permuted)
assert any(
    not equal(
        mesh_fields.get(n).values,
        mesh_fields_permuted.get(n).values
    )
    for n in mesh_fields.field_names
)

# You can check whether a file has a supported mesh file format
# to verify if you can obtain a mesh_field_reader for it.
assert is_mesh_file(mesh_file)
