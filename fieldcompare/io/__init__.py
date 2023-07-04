# SPDX-FileCopyrightText: 2023 Dennis Gläser <dennis.glaeser@iws.uni-stuttgart.de>
# SPDX-License-Identifier: GPL-3.0-or-later

"""I/O facilities to read field data from files."""

from __future__ import annotations
from os.path import splitext
from warnings import warn

from .. import protocols
from . import vtk
from ._csv_reader import CSVFieldReader
from ._mesh_io import _read as _meshio_read, _is_supported as _supported_by_meshio, _HAVE_MESHIO

from ..tabular import TabularFields
from ..mesh.protocols import MeshFields


__all__ = ["read_field_data", "read", "read_as", "is_supported"]


_AVAILABLE_FILE_TYPES = ["mesh", "dsv"]


def read_field_data(filename: str, options: dict[str, dict] | None = None) -> protocols.FieldData:
    """
    Read the field data from the given file

    Args:
        filename: Path to the file from which to read.
        options: further options (see :meth:`.read`)
    """
    result = read(filename, options or {})
    assert isinstance(result, protocols.FieldData)
    return result


def write(fields: protocols.FieldData, filename: str) -> str:
    """
    Write the given field data into a file with the given base name and return the name of the written file.

    Args:
        fields: The fields to be written out
        filename: The name of the file in which to write the fields (without file extension).
    """
    if isinstance(fields, MeshFields):
        return _write_mesh(fields, filename)
    if isinstance(fields, TabularFields):
        return _write_table(fields, filename)
    raise NotImplementedError("no write function implemented for given field data type")


def read(filename: str, options: dict[str, dict] | None = None) -> protocols.FieldData | protocols.FieldDataSequence:
    """
    Read the field data or field data sequence from the given file

    Args:
        filename: Path to the file from which to read.
        options: Dictionary containing further options to be passed to the field readers.
                 Depending on the file type deduced from filename, the options passed to the
                 associated reader are extracted from `options` by accessing it via the file type
                 key ("mesh", "dsv", ...).
    """
    options = options or {}
    if _is_supported_mesh_file(filename):
        return _read_mesh_file(filename, **options["mesh"]) if "mesh" in options else _read_mesh_file(filename)
    if splitext(filename)[1] in [".csv", ".dsv"]:
        return _read_dsv_file(filename, **options["dsv"]) if "dsv" in options else _read_dsv_file(filename)
    raise IOError(_unsupported_file_error_message(filename))


def read_as(file_type: str, filename: str, **kwargs) -> protocols.FieldData | protocols.FieldDataSequence:
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
    return splitext(filename)[1] == ".csv" or _is_supported_mesh_file(filename)


def _unsupported_file_error_message(filename: str) -> str:
    return f"Unsupported file '{filename}'{_meshio_info_message()}"


def _meshio_info_message() -> str:
    return "" if _HAVE_MESHIO else " (consider installing 'meshio' to have access to more file formats)"


def _is_supported_mesh_file(filename: str) -> bool:
    return vtk.is_supported(filename) or (_HAVE_MESHIO and _supported_by_meshio(filename))


def _read_mesh_file(filename: str, **kwargs) -> protocols.FieldData | protocols.FieldDataSequence:
    if kwargs:
        warn("Options are ignored when reading from mesh file", stacklevel=3)

    if vtk.is_supported(filename):
        return vtk.read(filename)
    if _HAVE_MESHIO and _supported_by_meshio(filename):
        try:
            return _meshio_read(filename)
        except Exception as err:
            raise IOError("Error reading with meshio") from err
    raise IOError(f"Could not read '{filename}' as mesh file{_meshio_info_message()}")


def _read_dsv_file(filename: str, **kwargs) -> protocols.FieldData:
    return CSVFieldReader(**kwargs).read(filename)


def _write_mesh(fields: MeshFields, filename: str) -> str:
    return vtk.VTUWriter(fields).write(filename)


def _write_table(fields: TabularFields, filename: str) -> str:
    filename_with_ext = f"{filename}.csv"
    with open(filename_with_ext, "w") as csv_file:
        field_map = {f.name: f.values for f in fields}
        csv_file.write(",".join(field_map.keys()) + "\n")
        for row in range(fields.domain.number_of_rows):
            csv_file.write(",".join(str(field_map[key][row]) for key in field_map) + "\n")
    return filename_with_ext
