"""Tests for the I/O facilities for vtk files"""

from os import chdir, getcwd
from os import walk, remove
from os.path import splitext, exists
from pathlib import Path
from typing import List

import pytest
from meshio import read as meshio_read

from fieldcompare import FieldDataComparator, protocols
from fieldcompare.mesh import meshio_utils, protocols as mesh_protocols
from fieldcompare.io.vtk import read

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
PVD_FILES = _find("pvd_", ".pvd", [""])
PVTU_FILES = _find("pvtu_", ".pvtu", [""])
PVTP_FILES = _find("pvtp_", ".pvtp", [""])


@pytest.mark.parametrize("filename", PVTU_FILES + PVTP_FILES)
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


def _test(filename: str) -> bool:
    mesh_fields = _read_mesh_fields(filename)
    tmp_filename = f"{splitext(filename)[0]}_from_meshio.vtk"
    if splitext(filename) == ".vtu":
        meshio_read_mesh = meshio_read(filename)
    else:
        meshio_mesh = meshio_utils.to_meshio(mesh_fields)

        # meshio seems to fail when meshes consist of e.g. polygons
        # with differing numbers of corners and the shape of the array
        # is not fully determined
        if any(block.data.dtype == "object" for block in meshio_mesh.cells):
            meshio_read_mesh = meshio_mesh
        else:
            meshio_mesh.write(tmp_filename)
            meshio_read_mesh = meshio_read(tmp_filename)

    meshio_mesh_fields = meshio_utils.from_meshio(meshio_read_mesh)
    comparator = FieldDataComparator(mesh_fields, meshio_mesh_fields)
    if exists(tmp_filename):
        remove(tmp_filename)
    return bool(comparator())


def _test_from_mesh(mesh_fields: mesh_protocols.MeshFields) -> bool:
    meshio_mesh = meshio_utils.to_meshio(mesh_fields)
    tmp_filename = "_temporary_test_to_meshio.vtu"
    meshio_mesh.write(tmp_filename)
    meshio_mesh = meshio_read(tmp_filename)
    meshio_mesh_fields = meshio_utils.from_meshio(meshio_mesh)
    comparator = FieldDataComparator(mesh_fields, meshio_mesh_fields)
    remove(tmp_filename)
    return bool(comparator())


def _read_mesh_fields(filename: str) -> mesh_protocols.MeshFields:
    mesh_fields = read(filename)
    assert isinstance(mesh_fields, mesh_protocols.MeshFields)
    return mesh_fields
