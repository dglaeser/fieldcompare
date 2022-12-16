"""Check the I/O facilities for vtk files"""

from os import walk, remove
from os.path import splitext, exists
from pathlib import Path
from typing import List

import pytest
from meshio import read as meshio_read

from fieldcompare import FieldDataComparison
from fieldcompare.mesh import meshio_utils
from fieldcompare.mesh._vtk import read
from fieldcompare.mesh._vtk._compressors import _HAVE_LZ4


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

VTU_INLINE_BASE64_UNCOMPRESSED = _find("vtu_", ".vtu", ["base64", "inline"], ["_compression_"])
VTU_INLINE_BASE64_ZLIB_COMPRESSION = _find("vtu_", ".vtu", ["base64", "inline", "zlib"])
VTU_INLINE_BASE64_LZMA_COMPRESSION = _find("vtu_", ".vtu", ["base64", "inline", "lzma"])
VTU_INLINE_BASE64_LZ4_COMPRESSION = _find("vtu_", ".vtu", ["base64", "inline", "lz4"])

VTU_APPENDED_BASE64_UNCOMPRESSED = _find("vtu_", ".vtu", ["base64", "appended"], ["_compression_"])
VTU_APPENDED_BASE64_ZLIB_COMPRESSION = _find("vtu_", ".vtu", ["base64", "appended", "zlib"])
VTU_APPENDED_BASE64_LZMA_COMPRESSION = _find("vtu_", ".vtu", ["base64", "appended", "lzma"])
VTU_APPENDED_BASE64_LZ4_COMPRESSION = _find("vtu_", ".vtu", ["base64", "appended", "lz4"])


@pytest.mark.parametrize("filename", VTU_ASCII_FILES)
def test_vtu_ascii_files(filename: str):
    _test(filename)


@pytest.mark.parametrize("filename", VTU_INLINE_BASE64_UNCOMPRESSED)
def test_vtu_inline_base64_files_uncompressed(filename: str):
    _test(filename)


@pytest.mark.parametrize("filename", VTU_INLINE_BASE64_ZLIB_COMPRESSION)
def test_vtu_inline_base64_files_zlib_compressed(filename: str):
    _test(filename)


@pytest.mark.parametrize("filename", VTU_INLINE_BASE64_LZMA_COMPRESSION)
def test_vtu_inline_base64_files_lzma_compressed(filename: str):
    _test(filename)


@pytest.mark.parametrize("filename", VTU_INLINE_BASE64_LZ4_COMPRESSION)
def test_vtu_inline_base64_files_lz4_compressed(filename: str):
    if not _HAVE_LZ4:
        pytest.skip("LZ4 not found. Skipping tests...")
    else:
        _test(filename)

@pytest.mark.parametrize("filename", VTU_APPENDED_BASE64_UNCOMPRESSED)
def test_vtu_appended_base64_files_uncompressed(filename: str):
    _test(filename)


@pytest.mark.parametrize("filename", VTU_APPENDED_BASE64_ZLIB_COMPRESSION)
def test_vtu_appended_base64_files_zlib_compressed(filename: str):
    _test(filename)


@pytest.mark.parametrize("filename", VTU_APPENDED_BASE64_LZMA_COMPRESSION)
def test_vtu_appended_base64_files_lzma_compressed(filename: str):
    _test(filename)


@pytest.mark.parametrize("filename", VTU_APPENDED_BASE64_LZ4_COMPRESSION)
def test_vtu_appended_base64_files_lz4_compressed(filename: str):
    if not _HAVE_LZ4:
        pytest.skip("LZ4 not found. Skipping tests...")
    else:
        _test(filename)


def _test(filename: str) -> bool:
    mesh_fields = read(filename)
    tmp_filename = f"{splitext(filename)[0]}_from_meshio.vtu"
    if splitext(filename) == ".vtu":
        meshio_read_mesh = meshio_read(filename)
    else:
        meshio_mesh = meshio_utils.to_meshio(mesh_fields)
        meshio_mesh.write(tmp_filename)
        meshio_read_mesh = meshio_read(tmp_filename)
    meshio_mesh_fields = meshio_utils.from_meshio(meshio_read_mesh)
    comparator = FieldDataComparison(mesh_fields, meshio_mesh_fields)
    if exists(tmp_filename):
        remove(tmp_filename)
    return bool(comparator())
