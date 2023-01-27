# SPDX-FileCopyrightText: 2023 Dennis Gläser <dennis.glaeser@iws.uni-stuttgart.de>
# SPDX-License-Identifier: GPL-3.0-or-later

"""I/O facilities to read field data from files."""

from os.path import splitext
from typing import Union, Dict
from warnings import warn

from .. import protocols
from . import vtk
from ._csv_reader import CSVFieldReader
from ._mesh_io import _read as _meshio_read, _is_supported as _supported_by_meshio, _HAVE_MESHIO


__all__ = ["read_field_data", "read", "read_as", "is_supported"]


_AVAILABLE_FILE_TYPES = ["mesh", "dsv"]


def read_field_data(filename: str, options: Dict[str, dict] = {}) -> protocols.FieldData:
    """
    Read the field data from the given file

    Args:
        filename: Path to the file from which to read.
        options: further options (see :meth:`.read`)
    """
    result = read(filename, options)
    assert isinstance(result, protocols.FieldData)
    return result


def read(filename: str, options: Dict[str, dict] = {}) -> Union[protocols.FieldData, protocols.FieldDataSequence]:
    """
    Read the field data or field data sequence from the given file

    Args:
        filename: Path to the file from which to read.
        options: Dictionary containing further options to be passed to the field readers.
                 Depending on the file type deduced from filename, the options passed to the
                 associated reader are extracted from `options` by accessing it via the file type
                 key ("mesh", "dsv", ...).
    """
    if _is_supported_mesh_file(filename):
        return _read_mesh_file(filename, **options["mesh"]) if "mesh" in options else _read_mesh_file(filename)
    if splitext(filename)[1] in [".csv", ".dsv"]:
        return _read_dsv_file(filename, **options["dsv"]) if "dsv" in options else _read_dsv_file(filename)
    raise IOError(_unsupported_file_error_message(filename))


def read_as(file_type: str, filename: str, **kwargs) -> Union[protocols.FieldData, protocols.FieldDataSequence]:
    """
    Read the field data or field data sequence from the given file, specifying its type.

    Args:
        file_type: The type of the file (currently available: 'mesh', 'dsv')
        filename: Path to the file from which to read.
        kwargs: Further arguments to be forwarded to the field readers.
    """
    if file_type == "mesh":
        return _read_mesh_file(filename, **kwargs)
    if file_type == "dsv":
        return _read_dsv_file(filename, **kwargs)
    raise ValueError(f"Unknown file type '{file_type}' (available options: {', '.join(_AVAILABLE_FILE_TYPES)})")


def is_supported(filename: str) -> bool:
    """
    Return true if the given file is supported for field-I/O.

    Args:
        filename: Path to the file for which to check if it is supported.
    """
    return vtk.is_supported(filename) or splitext(filename)[1] == ".csv" or _supported_by_meshio(filename)


def _unsupported_file_error_message(filename: str) -> str:
    return f"Unsupported file '{filename}'{_meshio_info_message()}"


def _meshio_info_message() -> str:
    return "" if _HAVE_MESHIO else " (consider installing 'meshio' to have access to more file formats)"


def _is_supported_mesh_file(filename: str) -> bool:
    return vtk.is_supported(filename) or (_HAVE_MESHIO and _supported_by_meshio(filename))


def _read_mesh_file(filename: str, **kwargs) -> Union[protocols.FieldData, protocols.FieldDataSequence]:
    if kwargs:
        warn("Options are ignored when reading from mesh file")

    if vtk.is_supported(filename):
        return vtk.read(filename)
    if _HAVE_MESHIO and _supported_by_meshio(filename):
        try:
            return _meshio_read(filename)
        except Exception as e:
            raise IOError(f"Error reading with meshio: '{e}'")
    raise IOError(f"Could not read '{filename}' as mesh file{_meshio_info_message()}")


def _read_dsv_file(filename: str, **kwargs) -> protocols.FieldData:
    return CSVFieldReader(**kwargs).read(filename)
