from fieldcompare.mesh import Mesh, PermutedMesh
from fieldcompare.mesh import permutations


def _check_mesh_identity(mesh1, mesh2) -> None:
    for a, b in zip(mesh1.points, mesh2.points):
        assert all(ai == bi for ai, bi in zip(a, b))

    assert set(list(mesh1.cell_types)) == set(list(mesh2.cell_types))

    for cell_type in mesh1.cell_types:
        assert all(
            aii == bii
            for ai, bi in zip(
                mesh1.connectivity(cell_type),
                mesh2.connectivity(cell_type)
            ) for aii, bii in zip(ai, bi)
        )


def test_mesh_construction():
    mesh = Mesh(
        points=[[float(i), 0.0] for i in range(3)],
        connectivity=([("line", [[0, 1], [1, 2]])])
    )
    assert mesh.points[0][0] == 0.0
    assert mesh.points[0][1] == 0.0
    assert mesh.points[1][0] == 1.0
    assert mesh.points[1][1] == 0.0
    assert mesh.points[2][0] == 2.0
    assert mesh.points[2][1] == 0.0

    assert len(list(mesh.cell_types)) == 1
    connectivity = mesh.connectivity(list(mesh.cell_types)[0])
    assert connectivity[0][0] == 0
    assert connectivity[0][1] == 1
    assert connectivity[1][0] == 1
    assert connectivity[1][1] == 2


def test_identity_permuted_mesh():
    mesh = Mesh(
        points=[[float(i), 0.0] for i in range(3)],
        connectivity=([("line", [[0, 1], [1, 2]])])
    )

    permuted_mesh = PermutedMesh(mesh=mesh)
    _check_mesh_identity(mesh, permuted_mesh)


def test_uniquely_permuted_mesh():
    mesh = Mesh(
        points=[[4.0 - float(i), 0.0] for i in range(5)],
        connectivity=([("line", [[2, 1], [0, 1]])])
    )

    unique = permutations.permute_uniquely(mesh)
    unique_2 = permutations.sort_cells(
        permutations.sort_points(
            permutations.remove_unconnected_points(mesh)
        )
    )

    assert len(unique.points) == 3
    assert len(unique_2.points) == 3
    _check_mesh_identity(unique, unique_2)
