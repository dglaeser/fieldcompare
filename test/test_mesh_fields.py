from os import remove
from numpy import array

try:
    import meshio
    from fieldcompare.mesh import meshio_utils
    _HAVE_MESHIO = True
except ImportError:
    _HAVE_MESHIO = False

from fieldcompare import FieldDataComparator
from fieldcompare.mesh import (
    Mesh, MeshFields,
    PermutedMesh, TransformedMeshFields,
    cell_types
)
from fieldcompare.mesh import sort_points, merge
from fieldcompare.predicates import ExactEquality


def test_mesh_fields():
    mesh = Mesh(
        points=[[float(i), 0.0] for i in range(3)],
        connectivity=([(cell_types.line, [[0, 1], [1, 2]])])
    )
    mesh_fields = MeshFields(
        mesh=mesh,
        point_data={"pd": [42.0, 43.0, 44.0]},
        cell_data={"cd": [[42.0, 43.0]]}
    )

    assert sum(1 for _ in mesh_fields) == 2
    for field in mesh_fields:
        if "pd" in field.name:
            assert ExactEquality()(field.values, [42.0, 43.0, 44.0])
        if "cd" in field.name:
            assert ExactEquality()(field.values, [42.0, 43.0])


def test_permuted_point_mesh_field():
    mesh = Mesh(
        points=[[4.0 - float(i), 0.0] for i in range(3)],
        connectivity=([(cell_types.line, [[0, 1], [1, 2]])])
    )
    mesh_fields = MeshFields(
        mesh=mesh,
        point_data={"pd": [42.0, 43.0, 44.0]}
    )
    for field in sort_points(mesh_fields):
        assert "pd" in field.name
        assert ExactEquality()(field.values, [44.0, 43.0, 42.0])


def test_permuted_cell_mesh_field():
    mesh = Mesh(
        points=[[4.0 - float(i), 0.0, 0.0] for i in range(3)],
        connectivity=([(cell_types.line, [[0, 1], [1, 2]])])
    )
    mesh_fields = MeshFields(
        mesh=mesh,
        cell_data={"cd": [[42.0, 43.0]]}
    )

    def _permutation(mesh):
        return PermutedMesh(
            mesh=mesh,
            cell_permutations={cell_types.line: [1, 0]}
        )

    for field in TransformedMeshFields(mesh_fields, _permutation):
        assert "cd" in field.name
        assert ExactEquality()(field.values, [43.0, 42.0])


def test_merge_mesh_fields():
    cell_type = cell_types.line
    point_data = array([42.0, 43.0, 44.0])
    cell_data = array([42.0, 43.0])
    mesh = Mesh(
        points=[[4.0 - float(i), 0.0, 0.0] for i in range(3)],
        connectivity=([(cell_type, array([[0, 1], [1, 2]]))])
    )
    mesh_fields = MeshFields(
        mesh=mesh,
        point_data={"pd": point_data},
        cell_data={"cd": [cell_data]}
    )

    result = merge(mesh_fields, mesh_fields)
    for i in range(len(result.domain.points)):
        assert all(a == b for a, b in zip(
            result.domain.points[i],
            mesh.points[i % 3]
        ))
    assert list(result.domain.cell_types) == [cell_type]
    for i in range(len(result.domain.connectivity(cell_type))):
        mesh_corners = mesh.connectivity(cell_type)[i % 2]
        result_corners = result.domain.connectivity(cell_type)[i]
        offset = 0 if i < 2 else 3
        assert [c for c in mesh_corners] == [c - offset for c in result_corners]

    for field in result.point_fields:
        for i, value in enumerate(field.values):
            assert value == point_data[i % 3]

    for field, _ in result.cell_fields_types:
        for i, value in enumerate(field.values):
            assert value == cell_data[i % 2]

    if _HAVE_MESHIO:
        tmp_file_name = "test_merge_mesh_fields_to_meshio.vtu"
        as_meshio = meshio_utils.to_meshio(result)
        as_meshio.write(tmp_file_name)
        as_meshio = meshio.read(tmp_file_name)
        as_fields = meshio_utils.from_meshio(as_meshio)
        comparator = FieldDataComparator(as_fields, result)
        print(comparator().domain_equality_check)
        assert comparator()
        remove(tmp_file_name)
