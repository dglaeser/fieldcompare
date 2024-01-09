# SPDX-FileCopyrightText: 2023 Dennis Gläser <dennis.glaeser@iws.uni-stuttgart.de>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for the I/O facilities for vtk files"""

from xml.etree import ElementTree
from os import chdir, getcwd
from os import walk, remove
from os.path import splitext
from pathlib import Path
from typing import List
from shutil import copyfile
from itertools import product

import pytest
import numpy
from meshio import read as meshio_read, Mesh as MeshioMesh

from fieldcompare import FieldDataComparator, protocols
from fieldcompare.mesh import CellTypes, meshio_utils, protocols as mesh_protocols
from fieldcompare.io.vtk import read, PVTUReader, VTUWriter
from fieldcompare.io import read_as


try:
    import lz4
    _HAVE_LZ4 = True
except ImportError:
    _HAVE_LZ4 = False


VTK_TEST_DATA_PATH = Path(__file__).resolve().parent / Path("vtkfiles")

def _find(begin: str, ext: str, keys: List[str], exclude_keys: List[str] = []) -> List[str]:
    hits = []
    for root, _, files in walk(VTK_TEST_DATA_PATH):
        for filename in files:
            if filename.startswith(begin) and \
                    splitext(filename)[1] == ext and \
                    all(k in filename for k in keys) and \
                    not any(k in filename for k in exclude_keys) and \
                    "from_meshio" not in filename:
                hits.append(str(Path(root) / Path(filename)))
    return hits


VTU_ASCII_FILES = _find("vtu_", ".vtu", ["ascii"])

VTU_INLINE_BASE64 = _find("vtu_", ".vtu", ["base64", "inline"], ["lz4"])
VTU_INLINE_BASE64_LZ4_COMPRESSION = _find("vtu_", ".vtu", ["base64", "inline", "lz4"])

VTU_APPENDED_BASE64 = _find("vtu_", ".vtu", ["base64", "appended"], ["lz4"])
VTU_APPENDED_BASE64_LZ4_COMPRESSION = _find("vtu_", ".vtu", ["base64", "appended", "lz4"])

VTU_APPENDED_RAW = _find("vtu_", ".vtu", ["raw", "appended"], ["lz4"])
VTU_APPENDED_RAW_LZ4_COMPRESSION = _find("vtu_", ".vtu", ["raw", "appended", "lz4"])

VTP_FILES = _find("vtp_", ".vtp", [""])
VTS_FILES = _find("vts_", ".vts", [""])
VTR_FILES = _find("vtr_", ".vtr", [""])
VTI_FILES = _find("vti_", ".vti", [""])
PVD_FILES = _find("pvd_", ".pvd", [""])
PVTU_FILES = _find("pvtu_", ".pvtu", [""])
PVTP_FILES = _find("pvtp_", ".pvtp", [""])
PVTS_FILES = _find("pvts_", ".pvts", [""])
PVTR_FILES = _find("pvtr_", ".pvtr", [""])
PVTI_FILES = _find("pvti_", ".pvti", [""])


def test_parallel_against_sequential_vtk_file():
    par_fields = _read_mesh_fields(str(VTK_TEST_DATA_PATH / "pvtu_parallel.pvtu"))
    seq_fields = _read_mesh_fields(str(VTK_TEST_DATA_PATH / "pvtu_sequential_reference.vtu"))
    assert FieldDataComparator(par_fields, seq_fields)()


def test_parallel_against_sequential_vtk_file_fails_without_duplicates_removal():
    cwd = getcwd()
    chdir(VTK_TEST_DATA_PATH)
    par_fields = PVTUReader(filename="pvtu_parallel.pvtu", remove_duplicate_points=False).read()
    seq_fields = _read_mesh_fields("pvtu_sequential_reference.vtu")
    assert not FieldDataComparator(par_fields, seq_fields)()
    chdir(cwd)


@pytest.mark.parametrize("filename", PVTU_FILES + PVTP_FILES + PVTS_FILES + PVTR_FILES + PVTI_FILES)
def test_parallel_vtk_files(filename: str):
    cwd = getcwd()
    chdir(VTK_TEST_DATA_PATH)
    _test(filename)
    chdir(cwd)


@pytest.mark.parametrize("filename", PVD_FILES)
def test_pvd_files(filename: str):
    cwd = getcwd()
    sequence = read(filename)
    assert isinstance(sequence, protocols.FieldDataSequence)
    chdir(VTK_TEST_DATA_PATH)
    for step in sequence:
        assert isinstance(step, mesh_protocols.MeshFields)
        _test_from_mesh(step)
    chdir(cwd)


@pytest.mark.parametrize("filename", VTP_FILES)
def test_vtp_files(filename: str):
    _test(filename)


@pytest.mark.parametrize("filename", VTS_FILES)
def test_vts_files(filename: str):
    _test(filename)


@pytest.mark.parametrize("filename", VTS_FILES)
def test_vts_unit(filename: str):
    fields = _read_mesh_fields(filename)
    _check_extents(fields.domain, filename)

    # test cell type
    dim = _get_mesh_dimension(filename)
    expected_cell_type = [CellTypes.line, CellTypes.quad, CellTypes.hexahedron][dim - 1]
    assert(sum(1 for _ in fields.domain.cell_types) == 1)
    assert(fields.domain.cell_types == [expected_cell_type])

    # test connectivity (assumes constant spacing between points)
    extents = _get_extents(filename)
    extents = [extents[direction*2 + 1] - extents[direction*2] for direction in range(3)]
    dx = (fields.domain.points[-1] - fields.domain.points[0])/numpy.array([max(e, 1) for e in extents])
    for corners in fields.domain.connectivity(CellTypes.quad):
        diagonal = fields.domain.points[corners[-2]] - fields.domain.points[corners[0]]
        assert(numpy.allclose(diagonal, numpy.array(dx)))

@pytest.mark.parametrize("filename", VTR_FILES)
def test_vtr_files(filename: str):
    _test(filename)


@pytest.mark.parametrize("filename", VTR_FILES)
def test_vtr_unit(filename: str):
    fields = _read_mesh_fields(filename)
    _check_extents(fields.domain, filename)
    if "ascii" in filename:
        dom = ElementTree.parse(filename)
        coords_element = dom.find("./RectilinearGrid/Piece/Coordinates")
        assert(coords_element is not None)
        assert(len(coords_element.findall("DataArray")) == 3)

        def _to_ordinates(ordinate_string):
            ordinate_string = ordinate_string.strip(" \n")
            if ordinate_string == "":
                return [0.0]
            return [float(c) for c in ordinate_string.split(" ")]

        ordinates = [_to_ordinates(ords.text) for ords in coords_element.findall("DataArray")]
        _check_point_coordinates(fields.domain, ordinates)

        # test cell type
        dim = _get_mesh_dimension(filename)
        expected_cell_type = [CellTypes.line, CellTypes.quad, CellTypes.hexahedron][dim - 1]
        assert(sum(1 for _ in fields.domain.cell_types) == 1)
        assert(fields.domain.cell_types == [expected_cell_type])

        # test connectivity (assumes constant dx along ordinates)
        dx = [(ords[1] - ords[0] if len(ords) > 1 else 0.) for ords in ordinates]
        for corners in fields.domain.connectivity(CellTypes.quad):
            diagonal = fields.domain.points[corners[-2]] - fields.domain.points[corners[0]]
            assert(numpy.allclose(diagonal, numpy.array(dx)))


@pytest.mark.parametrize("filename", VTI_FILES)
def test_vti_files(filename: str):
    _test(filename)


@pytest.mark.parametrize("filename", VTI_FILES)
def test_vti_unit(filename: str):
    fields = _read_mesh_fields(filename)
    _check_extents(fields.domain, filename)
    extents = _get_extents(filename)
    origin = _get_origin(filename)
    dx = _get_spacing(filename)
    ordinates = [
        [origin[direction] + i*dx[direction] for i in range(extents[direction*2 + 1] + 1)]
        for direction in range(len(dx))
    ]
    _check_point_coordinates(fields.domain, ordinates)

    # test cell type
    dim = _get_mesh_dimension(filename)
    expected_cell_type = [CellTypes.line, CellTypes.quad, CellTypes.hexahedron][dim - 1]
    assert(sum(1 for _ in fields.domain.cell_types) == 1)
    assert(fields.domain.cell_types == [expected_cell_type])

    # test connectivity
    for corners in fields.domain.connectivity(CellTypes.quad):
        diagonal = fields.domain.points[corners[-2]] - fields.domain.points[corners[0]]
        assert(numpy.allclose(diagonal, numpy.array(dx)))


@pytest.mark.parametrize("filename", VTU_ASCII_FILES)
def test_vtu_ascii_files(filename: str):
    _test(filename)


@pytest.mark.parametrize("filename", VTU_INLINE_BASE64)
def test_vtu_inline_base64_files(filename: str):
    _test(filename)


@pytest.mark.parametrize("filename", VTU_INLINE_BASE64_LZ4_COMPRESSION)
def test_vtu_inline_base64_files_lz4_compressed(filename: str):
    if not _HAVE_LZ4:
        pytest.skip("LZ4 not found. Skipping tests...")
    else:
        _test(filename)


@pytest.mark.parametrize("filename", VTU_APPENDED_BASE64)
def test_vtu_appended_base64_files(filename: str):
    _test(filename)


@pytest.mark.parametrize("filename", VTU_APPENDED_BASE64_LZ4_COMPRESSION)
def test_vtu_appended_base64_files_lz4_compressed(filename: str):
    if not _HAVE_LZ4:
        pytest.skip("LZ4 not found. Skipping tests...")
    else:
        _test(filename)


@pytest.mark.parametrize("filename", VTU_APPENDED_RAW)
def test_vtu_appended_raw_files(filename: str):
    _test(filename)


@pytest.mark.parametrize("filename", VTU_APPENDED_RAW_LZ4_COMPRESSION)
def test_vtu_appended_raw_files_lz4_compressed(filename: str):
    if not _HAVE_LZ4:
        pytest.skip("LZ4 not found. Skipping tests...")
    else:
        _test(filename)


def test_vtu_reading_from_different_extension():
    assert _test_with_different_extension(VTU_APPENDED_RAW[0])
    assert _test_read_as_mesh(VTU_APPENDED_RAW[0])


def test_vtp_reading_from_different_extension():
    assert _test_with_different_extension(VTP_FILES[0])
    assert _test_read_as_mesh(VTP_FILES[0])


def test_pvtp_reading_from_different_extension():
    assert _test_with_different_extension(PVTP_FILES[0])
    assert _test_read_as_mesh(PVTP_FILES[0])


def test_pvtu_reading_from_different_extension():
    assert _test_with_different_extension(PVTU_FILES[0])
    assert _test_read_as_mesh(PVTU_FILES[0])


def test_pvd_reading_from_different_extension():
    filename = PVD_FILES[0]
    new_filename = f"{splitext(filename)[0]}.wrongext"
    copyfile(filename, new_filename)
    sequence = read(new_filename)
    for step in sequence:
        assert isinstance(step, mesh_protocols.MeshFields)
        _test_from_mesh(step)
    remove(new_filename)


@pytest.mark.parametrize("filename", VTU_INLINE_BASE64)
def test_vtu_writer(filename: str):
    print(f"Reading, writing and testing {filename}")
    fields = _read_mesh_fields(filename)
    writer = VTUWriter(fields)
    writer.write("_temp")
    written_fields = _read_mesh_fields("_temp.vtu")
    result = bool(FieldDataComparator(fields, written_fields)())
    remove("_temp.vtu")
    assert result


def _test_with_different_extension(filename: str) -> bool:
    new_filename = f"{splitext(filename)[0]}.wrongext"
    copyfile(filename, new_filename)
    check = _test(new_filename)
    remove(new_filename)
    return check


def _test_read_as_mesh(filename: str) -> bool:
    new_filename = f"{splitext(filename)[0]}.unknown"
    copyfile(filename, new_filename)
    try:
        fields = read_as("mesh", new_filename)
        assert isinstance(fields, mesh_protocols.MeshFields)
        check = _test_from_mesh(fields)
    except Exception as e:
        check = False
        print(f"Exception raised: {e}")
    remove(new_filename)
    return check


def _test(filename: str) -> bool:
    mesh_fields = _read_mesh_fields(filename)
    meshio_mesh = _get_alternative_with_meshio(mesh_fields, f"{splitext(filename)[0]}_from_meshio.vtk")
    meshio_mesh_fields = meshio_utils.from_meshio(meshio_mesh)
    return bool(FieldDataComparator(mesh_fields, meshio_mesh_fields)())


def _test_from_mesh(mesh_fields: mesh_protocols.MeshFields) -> bool:
    meshio_mesh = _get_alternative_with_meshio(mesh_fields, "_test_from_meshio.vtk")
    meshio_mesh_fields = meshio_utils.from_meshio(meshio_mesh)
    return bool(FieldDataComparator(mesh_fields, meshio_mesh_fields)())


def _get_alternative_with_meshio(mesh_fields: mesh_protocols.MeshFields, tmp_filename: str) -> MeshioMesh:
    meshio_mesh = meshio_utils.to_meshio(mesh_fields)

    # meshio seems to fail writing vtk files when meshes consist of e.g. polygons
    # with differing numbers of corners and the shape of the array
    # is not fully determined. In this case, just return the converted mesh
    if any(block.data.dtype == "object" for block in meshio_mesh.cells):
        return meshio_mesh
    else:
        meshio_mesh.write(tmp_filename)
        meshio_read_mesh = meshio_read(tmp_filename)
        remove(tmp_filename)
        return meshio_read_mesh


def _read_mesh_fields(filename: str) -> mesh_protocols.MeshFields:
    mesh_fields = read(filename)
    assert isinstance(mesh_fields, mesh_protocols.MeshFields)
    return mesh_fields


def _check_point_coordinates(structured_mesh, ordinates: List[List[float]]) -> None:
    expected_points = [
        list(reversed(p))
        for p in product(*list(reversed(ordinates)))
    ]
    assert(len(ordinates) == 3)
    assert(len(expected_points) == len(structured_mesh.points))
    for mesh_point, expected_point in zip(structured_mesh.points, expected_points):
        assert(numpy.allclose(mesh_point, numpy.array(expected_point)))


def _check_extents(structured_mesh, filename: str) -> None:
    file_extents = _get_extents(filename)
    assert(structured_mesh.extents[0] == file_extents[1] - file_extents[0])
    assert(structured_mesh.extents[1] == file_extents[3] - file_extents[2])
    assert(structured_mesh.extents[2] == file_extents[5] - file_extents[4])


def _get_extents(filename: str) -> List[int]:
        return _get("WholeExtent", filename, int)


def _get_origin(filename: str) -> List[float]:
        return _get("Origin", filename, float)


def _get_spacing(filename: str) -> List[float]:
    return _get("Spacing", filename, float)


def _get(keyword: str, filename: str, dtype):
    return [
        dtype(c) for c in
        open(filename).read().split(f'{keyword}="')[1].split('"')[0].split(" ")
    ]


def _get_mesh_dimension(filename: str) -> int:
    print(filename)
    before, _ = filename.split("d_in_")
    return int(before[-1])
