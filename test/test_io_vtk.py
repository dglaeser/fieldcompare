# SPDX-FileCopyrightText: 2023 Dennis Gläser <dennis.glaeser@iws.uni-stuttgart.de>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for the I/O facilities for vtk files"""
from __future__ import annotations
from xml.etree import ElementTree
from os import chdir, getcwd
from os import walk, remove
from os.path import splitext
from pathlib import Path
from typing import List
from shutil import copyfile
from itertools import product
from math import sin, cos

import pytest
import numpy
from meshio import read as meshio_read, Mesh as MeshioMesh

from fieldcompare import FieldDataComparator, FieldComparisonResult, protocols
from fieldcompare.mesh import CellTypes, meshio_utils, protocols as mesh_protocols
from fieldcompare.io.vtk import read, PVTUReader, VTUWriter
from fieldcompare.io import read_as
from fieldcompare.mesh._structured_mesh import standard_basis


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
    assert _test(filename)
    chdir(cwd)


@pytest.mark.parametrize("filename", PVD_FILES)
def test_pvd_files(filename: str):
    cwd = getcwd()
    sequence = read(filename)
    assert isinstance(sequence, protocols.FieldDataSequence)
    times = _read_pvd_timesteps(filename)
    chdir(VTK_TEST_DATA_PATH)
    for i, step in enumerate(sequence):
        assert isinstance(step, mesh_protocols.MeshFields)
        assert _test_from_mesh(step, filename, step_multiplier=times[i])
    chdir(cwd)


@pytest.mark.parametrize("filename", VTP_FILES)
def test_vtp_files(filename: str):
    assert _test(filename)


@pytest.mark.parametrize("filename", VTS_FILES)
def test_vts_files(filename: str):
    assert _test(filename)


@pytest.mark.parametrize("filename", VTS_FILES)
def test_vts_extents(filename: str):
    domain = _read_mesh_fields(filename).domain
    assert isinstance(domain, mesh_protocols.StructuredMesh)
    _check_extents(domain, filename)


@pytest.mark.parametrize("filename", VTS_FILES)
def test_vts_cell_type(filename: str):
    fields = _read_mesh_fields(filename)
    dim = _get_mesh_dimension(filename)
    expected_cell_type = [CellTypes.line, CellTypes.quad, CellTypes.hexahedron][dim - 1]
    assert(sum(1 for _ in fields.domain.cell_types) == 1)
    assert(fields.domain.cell_types == [expected_cell_type])


@pytest.mark.parametrize("filename", VTS_FILES)
def test_vts_connectivity(filename: str):
    # assumes constant spacing between points
    fields = _read_mesh_fields(filename)
    extents = _get_extents(filename)
    extents = [extents[direction*2 + 1] - extents[direction*2] for direction in range(3)]
    dx = (fields.domain.points[-1] - fields.domain.points[0])/numpy.array([max(e, 1) for e in extents])
    _check_point_coordinates(fields.domain, dx)


@pytest.mark.parametrize("filename", VTR_FILES)
def test_vtr_files(filename: str):
    assert _test(filename)


@pytest.mark.parametrize("filename", VTR_FILES)
def test_vtr_extents(filename: str):
    domain = _read_mesh_fields(filename).domain
    assert isinstance(domain, mesh_protocols.StructuredMesh)
    _check_extents(domain, filename)


@pytest.mark.parametrize("filename", VTR_FILES)
def test_vtr_coordinates(filename: str):
    # assumes constant spacing
    ordinates = _get_vtr_ordinates(filename)
    dx = [(ords[1] - ords[0] if len(ords) > 1 else 0.0) for ords in ordinates]
    _check_point_coordinates(_read_mesh_fields(filename).domain, dx)


@pytest.mark.parametrize("filename", VTR_FILES)
def test_vtr_cell_types(filename: str):
    fields = _read_mesh_fields(filename)
    dim = _get_mesh_dimension(filename)
    expected_cell_type = [CellTypes.line, CellTypes.pixel, CellTypes.voxel][dim - 1]
    assert(sum(1 for _ in fields.domain.cell_types) == 1)
    assert(fields.domain.cell_types == [expected_cell_type])



@pytest.mark.parametrize("filename", VTR_FILES)
def test_vtr_connectivity(filename: str):
    # assumes constant spacing along axes
    fields = _read_mesh_fields(filename)
    dx = [(ords[1] - ords[0] if len(ords) > 1 else 0.) for ords in _get_vtr_ordinates(filename)]
    for corners in fields.domain.connectivity(CellTypes.quad):
        diagonal = fields.domain.points[corners[-2]] - fields.domain.points[corners[0]]
        assert(numpy.allclose(diagonal, numpy.array(dx)))


@pytest.mark.parametrize("filename", VTI_FILES)
def test_vti_files(filename: str):
    assert _test(filename)


@pytest.mark.parametrize("filename", VTI_FILES)
def test_vti_extents(filename: str):
    domain = _read_mesh_fields(filename).domain
    assert isinstance(domain, mesh_protocols.StructuredMesh)
    _check_extents(domain, filename)


@pytest.mark.parametrize("filename", VTI_FILES)
def test_vti_coordinates(filename: str):
    _check_point_coordinates(
        _read_mesh_fields(filename).domain, _get_spacing(filename), _get_vti_basis(filename), _get_origin(filename)
    )


@pytest.mark.parametrize("filename", VTI_FILES)
def test_vti_cell_types(filename: str):
    fields = _read_mesh_fields(filename)
    dim = _get_mesh_dimension(filename)
    expected_cell_type = [CellTypes.line, CellTypes.pixel, CellTypes.voxel][dim - 1]
    assert(sum(1 for _ in fields.domain.cell_types) == 1)
    assert(fields.domain.cell_types == [expected_cell_type])


@pytest.mark.parametrize("filename", VTI_FILES)
def test_vti_connectivity(filename: str):
    fields = _read_mesh_fields(filename)
    dx = _get_spacing(filename)
    for corners in fields.domain.connectivity(CellTypes.quad):
        diagonal = fields.domain.points[corners[-2]] - fields.domain.points[corners[0]]
        assert(numpy.allclose(diagonal, numpy.array(dx)))


@pytest.mark.parametrize("filename", VTU_ASCII_FILES)
def test_vtu_ascii_files(filename: str):
    assert _test(filename)


@pytest.mark.parametrize("filename", VTU_INLINE_BASE64)
def test_vtu_inline_base64_files(filename: str):
    assert _test(filename)


@pytest.mark.parametrize("filename", VTU_INLINE_BASE64_LZ4_COMPRESSION)
def test_vtu_inline_base64_files_lz4_compressed(filename: str):
    if not _HAVE_LZ4:
        pytest.skip("LZ4 not found. Skipping tests...")
    else:
        assert _test(filename)


@pytest.mark.parametrize("filename", VTU_APPENDED_BASE64)
def test_vtu_appended_base64_files(filename: str):
    assert _test(filename)


@pytest.mark.parametrize("filename", VTU_APPENDED_BASE64_LZ4_COMPRESSION)
def test_vtu_appended_base64_files_lz4_compressed(filename: str):
    if not _HAVE_LZ4:
        pytest.skip("LZ4 not found. Skipping tests...")
    else:
        assert _test(filename)


@pytest.mark.parametrize("filename", VTU_APPENDED_RAW)
def test_vtu_appended_raw_files(filename: str):
    assert _test(filename)


@pytest.mark.parametrize("filename", VTU_APPENDED_RAW_LZ4_COMPRESSION)
def test_vtu_appended_raw_files_lz4_compressed(filename: str):
    if not _HAVE_LZ4:
        pytest.skip("LZ4 not found. Skipping tests...")
    else:
        assert _test(filename)


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
    times = _read_pvd_timesteps(filename)
    for i, step in enumerate(sequence):
        assert isinstance(step, mesh_protocols.MeshFields)
        assert _test_from_mesh(step, new_filename, times[i])
    remove(new_filename)


@pytest.mark.parametrize("filename", VTU_INLINE_BASE64)
def test_vtu_writer(filename: str):
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
        check = _test_from_mesh(fields, filename)
    except Exception as e:
        check = False
        print(f"Exception raised: {e}")
    remove(new_filename)
    return check


def _test(filename: str, step_multiplier: float = 1.0) -> bool:
    return _test_from_mesh(
        _read_mesh_fields(filename),
        basefilename=f"{splitext(filename)[0]}_from_meshio.vtk",
        step_multiplier=step_multiplier
    )


def _test_from_mesh(mesh_fields: mesh_protocols.MeshFields, basefilename: str = "", step_multiplier: float = 1.0) -> bool:
    _test_field_functions(mesh_fields, step_multiplier)
    meshio_mesh = _get_alternative_with_meshio(mesh_fields, f"{basefilename}_test_from_meshio.vtk")
    meshio_mesh_fields = meshio_utils.from_meshio(meshio_mesh)
    result = FieldDataComparator(mesh_fields, meshio_mesh_fields)()
    return not any(r.result == FieldComparisonResult.unequal for r in result)


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


def _read_pvd_timesteps(filename: str) -> list[float]:
    return [
        float(e.attrib["timestep"])
        for e in ElementTree.parse(filename).find("Collection").findall("DataSet")
    ]


def _read_mesh_fields(filename: str) -> mesh_protocols.MeshFields:
    mesh_fields = read(filename)
    assert isinstance(mesh_fields, mesh_protocols.MeshFields)
    return mesh_fields


def _check_point_coordinates(
        structured_mesh, _dx: List[float], basis = standard_basis(), _origin: List[float] = [0.0, 0.0, 0.0]
) -> None:
    assert(len(_dx) == 3)
    dx = numpy.array(_dx)
    origin = numpy.array(_origin)
    expected_points = [  # reverse extents to get expected point ordering
        origin + basis.dot(dx * numpy.array([i for i in reversed(ituple)]))
        for ituple in product(*list(reversed(list(range(e + 1) for e in structured_mesh.extents))))
    ]
    assert(len(expected_points) == len(structured_mesh.points))
    for mesh_point, expected_point in zip(structured_mesh.points, expected_points):
        assert(numpy.allclose(mesh_point, expected_point))


def _check_extents(structured_mesh, filename: str) -> None:
    file_extents = _get_extents(filename)
    assert(structured_mesh.extents[0] == file_extents[1] - file_extents[0])
    assert(structured_mesh.extents[1] == file_extents[3] - file_extents[2])
    assert(structured_mesh.extents[2] == file_extents[5] - file_extents[4])


def _get_extents(filename: str) -> List[int]:
        return _get("WholeExtent", filename, int)


def _get_spacing(filename: str) -> List[float]:
    return _get("Spacing", filename, float)


def _get_origin(filename: str) -> List[float]:
    return _get("Origin", filename, float)


def _get_vti_basis(filename: str) -> numpy.ndarray:
    vtk_basis = _get("Direction", filename, float)
    result = numpy.eye(3, 3)
    for i in range(3):
        result[i] = vtk_basis[i * 3 : (i + 1)*3]
    return result


def _get(keyword: str, filename: str, dtype):
    return [
        dtype(c) for c in
        open(filename).read().split(f'{keyword}="')[1].split('"')[0].split(" ")
    ]


def _get_mesh_dimension(filename: str) -> int:
    before, _ = filename.split("d_in_")
    return int(before[-1])


def _get_vtr_ordinates(filename: str) -> List[List[float]]:
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

        return [_to_ordinates(ords.text) for ords in coords_element.findall("DataArray")]
    raise RuntimeError("Can only read ordinates from ascii vtr files")


def _test_field_functions(mesh_fields: mesh_protocols.MeshFields, step_multiplier: float = 1.0) -> None:
    _test_point_field_functions(mesh_fields, step_multiplier)
    _test_cell_field_functions(mesh_fields, step_multiplier)


def _test_point_field_functions(mesh_fields: mesh_protocols.MeshFields, step_multiplier: float = 1.0) -> None:
    for field in mesh_fields.point_fields:
        for i, point in enumerate(mesh_fields.domain.points):
            expected = _evaluate_test_function(point, step_multiplier)
            found = _extract_first_entry(field.values[i])
            assert numpy.isclose(expected, found)


def _test_cell_field_functions(mesh_fields: mesh_protocols.MeshFields, step_multiplier: float = 1.0) -> None:
    for field, ct in mesh_fields.cell_fields_types:
        points = mesh_fields.domain.points
        assert len(mesh_fields.domain.connectivity(ct)) == len(field.values)
        for cell_idx, connectivity in enumerate(mesh_fields.domain.connectivity(ct)):
            center = sum(points[c] for c in connectivity)/float(len(connectivity))
            assert isinstance(center, numpy.ndarray)
            expected = _evaluate_test_function(center, step_multiplier)
            found = _extract_first_entry(field.values[cell_idx])
            assert numpy.isclose(expected, found)


def _extract_first_entry(entry):
    if isinstance(entry, numpy.ndarray):
        if len(entry.shape) > 0:
            return _extract_first_entry(entry[0])
    return entry


# all point/cell fields in the vtk test files represent this function
def _evaluate_test_function(point: list[float] | numpy.ndarray, step_multiplier: float = 1.0) -> float:
    result = 10.0*sin(point[0])
    if len(point) > 1:
        result *= cos(point[1])
    if len(point) > 2:
        result *= point[2] + 1.0
    return result*step_multiplier
