from fieldcompare.mesh import Mesh, MeshFields, PermutedMesh
from fieldcompare.mesh import permutations
from fieldcompare.predicates import ExactEquality


def test_mesh_fields():
    mesh = Mesh(
        points=[[float(i), 0.0] for i in range(3)],
        connectivity=([("line", [[0, 1], [1, 2]])])
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
        connectivity=([("line", [[0, 1], [1, 2]])])
    )
    mesh_fields = MeshFields(
        mesh=mesh,
        point_data={"pd": [42.0, 43.0, 44.0]}
    )
    for field in mesh_fields.permuted(permutations.sort_points):
        assert "pd" in field.name
        assert ExactEquality()(field.values, [44.0, 43.0, 42.0])


def test_permuted_cell_mesh_field():
    mesh = Mesh(
        points=[[4.0 - float(i), 0.0] for i in range(3)],
        connectivity=([("line", [[0, 1], [1, 2]])])
    )
    mesh_fields = MeshFields(
        mesh=mesh,
        cell_data={"cd": [[42.0, 43.0]]}
    )

    def _permutation(mesh):
        return PermutedMesh(
            mesh=mesh,
            cell_permutations={"line": [1, 0]}
        )

    for field in mesh_fields.permuted(_permutation):
        assert "cd" in field.name
        assert ExactEquality()(field.values, [43.0, 42.0])
