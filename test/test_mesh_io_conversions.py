# SPDX-FileCopyrightText: 2023 Dennis Gläser <dennis.glaeser@iws.uni-stuttgart.de>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Test the mesh field i/o mechanisms"""
from pathlib import Path
from meshio import read

from fieldcompare import FieldDataComparator
from fieldcompare.mesh import meshio_utils, sort

TEST_DATA_PATH = Path(__file__).resolve().parent / Path("data")


def test_mesh_io_interoperability():
    mesh = read(TEST_DATA_PATH / Path("test_mesh.vtu"))
    mesh_fields = meshio_utils.from_meshio(mesh)
    mesh_fields_permuted = sort(mesh_fields)
    assert not FieldDataComparator(mesh_fields, mesh_fields_permuted)()

    mesh_permuted = meshio_utils.to_meshio(mesh_fields_permuted)
    mesh_fields_converted_permuted = meshio_utils.from_meshio(mesh_permuted)
    assert FieldDataComparator(mesh_fields_converted_permuted, mesh_fields_permuted)()
