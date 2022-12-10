"""Test the mesh field i/o mechanisms"""
from pathlib import Path
from meshio import read

from fieldcompare import FieldDataComparison
from fieldcompare.mesh import meshio_utils, permutations

TEST_DATA_PATH = Path(__file__).resolve().parent / Path("data")


def test_mesh_io_interoperability():
    mesh = read(TEST_DATA_PATH / Path("test_mesh.vtu"))
    mesh_fields = meshio_utils.from_meshio(mesh)
    mesh_fields_permuted = mesh_fields.permuted(permutations.permute_uniquely)
    assert not FieldDataComparison(mesh_fields, mesh_fields_permuted)()

    mesh_permuted = meshio_utils.to_meshio(mesh_fields_permuted)
    mesh_fields_converted_permuted = meshio_utils.from_meshio(mesh_permuted)
    assert FieldDataComparison(mesh_fields_converted_permuted, mesh_fields_permuted)()
