# SPDX-FileCopyrightText: 2023 Dennis Gläser <dennis.glaeser@iws.uni-stuttgart.de>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations
from typing import Iterable
from xml.etree import ElementTree
from os.path import isabs, join, exists, dirname
from numpy import ndarray, array, unique, zeros

from ... import protocols
from ...mesh import MeshFields, merge, StructuredFieldMerger, protocols as mesh_protocols
from ...mesh import StructuredMesh, RectilinearMesh, ImageMesh
from ...mesh._mesh_fields import remove_cell_type_suffix

from ._vtu_reader import VTUReader
from ._vtp_reader import VTPReader
from ._vts_reader import VTSReader
from ._vtr_reader import VTRReader
from ._vti_reader import VTIReader
from ._reader_map import _VTKReader, _FieldDataReader, _VTK_EXTENSION_TO_READER, _VTK_TYPE_TO_EXTENSION
from ._helpers import _VTK_SPACE_DIM


class _PVTKReader:
    class _StructuredDecomposition:
        def __init__(self, cells_per_axis: list[list[int]], order: ndarray) -> None:
            self._cells_per_axis = cells_per_axis
            self._order = order

        def dimension(self) -> int:
            return sum(1 for _ in self.meshed_dimensions())

        def domain_id(self, location: tuple[int, ...]) -> int:
            return self._order[location]

        def decomposition_along(self, direction: int) -> list[int]:
            return self._cells_per_axis[direction]

        def meshed_dimensions(self) -> Iterable[int]:
            return (i for i in range(_VTK_SPACE_DIM) if self.is_meshed_dimension(i))

        def is_meshed_dimension(self, direction: int) -> bool:
            return self._cells_per_axis[direction][0] > 0

        def merged_extents(self) -> tuple[int, ...]:
            return tuple(sum(n for n in sizes) for sizes in self._cells_per_axis)

    def __init__(
        self, vtk_grid_type: str, piece_reader: _VTKReader, filename: str, remove_duplicate_points: bool = True
    ) -> None:
        self._grid_type = vtk_grid_type
        self._piece_elements = self._get_piece_elements(filename)
        self._piece_reader = piece_reader
        self._remove_duplicate_points = remove_duplicate_points
        self._dirname = dirname(filename)
        self._is_structured_format = hasattr(self._piece_reader, "extents")
        try:
            self._piece_files = [c.attrib["Source"] for c in self._piece_elements]
        except Exception as e:
            raise IOError(
                f"Could not process '{filename}'. One or more <Piece> elements do "
                "not define the mandatory 'Source' attribute."
            ) from e

    def read(self) -> protocols.FieldData:
        if not self._piece_files:
            raise IOError("No pieces found in the given parallel vtk file")
        return self._merge_pieces()

    def _get_piece_elements(self, filename: str) -> list[ElementTree.Element]:
        xml_tree = ElementTree.parse(filename).getroot()
        grid = xml_tree.find(f"P{self._grid_type}")
        assert grid is not None
        return list(c for c in filter(lambda c: c.tag == "Piece", grid))

    def _read_piece(self, idx: int) -> mesh_protocols.MeshFields:
        return self._read_from(self._make_piece_reader(idx))

    def _make_piece_reader(self, idx: int) -> _FieldDataReader:
        piece = self._piece_files[idx]
        if not exists(piece) and not isabs(piece) and exists(join(self._dirname, piece)):
            piece = join(self._dirname, piece)
        return self._piece_reader(piece)

    def _read_from(self, piece_reader: _FieldDataReader) -> mesh_protocols.MeshFields:
        result = piece_reader.read()
        assert isinstance(result, mesh_protocols.MeshFields)
        return result

    def _merge_pieces(self) -> protocols.FieldData:
        # structured merging always removes duplicates, so don't do it if explicitly requested not to
        if self._is_structured_format and self._remove_duplicate_points:
            return self._merge_structured()
        return self._merge_unstructured()

    def _merge_unstructured(self) -> mesh_protocols.MeshFields:
        result = self._read_piece(0)
        for piece_idx in range(1, len(self._piece_files)):
            result = merge(result, self._read_piece(piece_idx), remove_duplicate_points=self._remove_duplicate_points)
        return result

    def _merge_structured(self) -> mesh_protocols.MeshFields:
        decomposition = self._get_structured_decomposition()
        piece_readers = [self._make_piece_reader(piece_idx) for piece_idx in range(len(self._piece_files))]
        piece_fields = [self._read_from(reader) for reader in piece_readers]
        merger = StructuredFieldMerger(
            tuple(tuple(decomposition.decomposition_along(i)) for i in decomposition.meshed_dimensions())
        )
        pfields = self._merge_point_fields(piece_fields, decomposition, merger)
        cfields = self._merge_cell_fields(piece_fields, decomposition, merger)
        mesh = self._make_structured_mesh(decomposition, piece_readers, piece_fields, merger)
        return MeshFields(mesh, pfields, cfields)

    def _make_structured_mesh(
        self,
        decomposition: _StructuredDecomposition,
        piece_readers: list[_FieldDataReader],
        piece_fields: list[mesh_protocols.MeshFields],
        merger: StructuredFieldMerger,
    ) -> mesh_protocols.Mesh:
        raise NotImplementedError("Reader implementation does not handle structured grids")

    def _merge_point_fields(self, piece_fields, decomposition, merger) -> dict[str, ndarray]:
        pfields: dict[str, list] = {n: [] for n in set(f.name for p in piece_fields for f in p.point_fields)}
        for piece in piece_fields:
            for pfield in piece.point_fields:
                pfields[pfield.name].append(pfield.values)
        return {
            name: merger.merge_point_fields(lambda loc, n=name: pfields[n][decomposition.domain_id(loc)])
            for name in pfields
        }

    def _merge_cell_fields(self, piece_fields, decomposition, merger) -> dict[str, list[ndarray]]:
        cts = set(ct for p in piece_fields for _, ct in p.cell_fields_types)
        assert len(cts) == 1
        ct = cts.pop()

        cfields: dict[str, list] = {
            n: []
            for n in set(remove_cell_type_suffix(ct, f.name) for p in piece_fields for f, _ in p.cell_fields_types)
        }
        for piece in piece_fields:
            for cfield, _ in piece.cell_fields_types:
                cfields[remove_cell_type_suffix(ct, cfield.name)].append(cfield.values)
        return {
            name: [merger.merge_cell_fields(lambda loc, n=name: cfields[n][decomposition.domain_id(loc)])]
            for name in cfields
        }

    def _get_structured_decomposition(self) -> _StructuredDecomposition:
        raw_piece_extents = [[int(v) for v in p.attrib["Extent"].split(" ")] for p in self._piece_elements]
        piece_extents_begin = array(
            [[raw_extent[d * 2] for d in range(_VTK_SPACE_DIM)] for raw_extent in raw_piece_extents]
        )
        piece_extents_end = array(
            [[raw_extent[d * 2 + 1] for d in range(_VTK_SPACE_DIM)] for raw_extent in raw_piece_extents]
        )
        unique_extents_begin = [list(unique(piece_extents_begin[:, i])) for i in range(_VTK_SPACE_DIM)]
        unique_extents_end = [list(unique(piece_extents_end[:, i])) for i in range(_VTK_SPACE_DIM)]
        sizes_along_axis = [
            [e - b for e, b in zip(unique_extents_end[d], unique_extents_begin[d])] for d in range(_VTK_SPACE_DIM)
        ]
        has_dimension = [sizes_along_axis[i][0] > 0 for i in range(_VTK_SPACE_DIM)]

        order = zeros(
            shape=tuple(len(sizes_along_axis[i]) for i in range(_VTK_SPACE_DIM) if has_dimension[i]), dtype=int
        )
        for i, piece_begin in enumerate(piece_extents_begin):
            piece_location = tuple(
                unique_extents_begin[direction].index(piece_begin[direction])
                for direction in range(_VTK_SPACE_DIM)
                if has_dimension[direction]
            )
            order[piece_location] = i
        return self._StructuredDecomposition(sizes_along_axis, order)


class PVTUReader(_PVTKReader):
    """Reads meshes from the VTK file format for parallel unstructured grids"""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__("UnstructuredGrid", VTUReader, *args, **kwargs)


class PVTPReader(_PVTKReader):
    """Reads meshes from the VTK file format for parallel polydata"""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__("PolyData", VTPReader, *args, **kwargs)


class PVTSReader(_PVTKReader):
    """Reads meshes from the VTK file format for parallel structured grids"""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__("StructuredGrid", VTSReader, *args, **kwargs)

    def _make_structured_mesh(
        self,
        decomposition: _PVTKReader._StructuredDecomposition,
        piece_readers: list[_FieldDataReader],
        piece_fields: list[mesh_protocols.MeshFields],
        merger: StructuredFieldMerger,
    ) -> StructuredMesh:
        piece_points = [p.domain.points for p in piece_fields]
        merged_points = merger.merge_point_fields(lambda loc: piece_points[decomposition.domain_id(loc)])
        extents = decomposition.merged_extents()
        return StructuredMesh(extents=(extents[0], extents[1], extents[2]), points=merged_points)


class PVTRReader(_PVTKReader):
    """Reads meshes from the VTK file format for parallel rectilinear grids"""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__("RectilinearGrid", VTRReader, *args, **kwargs)

    def _make_structured_mesh(
        self,
        decomposition: _PVTKReader._StructuredDecomposition,
        piece_readers: list[_FieldDataReader],
        piece_fields: list[mesh_protocols.MeshFields],
        merger: StructuredFieldMerger,
    ) -> RectilinearMesh:
        extents = decomposition.merged_extents()
        ordinates = [zeros(shape=(extents[i] + 1,)) for i in range(_VTK_SPACE_DIM)]
        for direction in decomposition.meshed_dimensions():
            index_offset = 0
            for i in range(len(decomposition.decomposition_along(direction))):
                domain_location = tuple(i if k == direction else 0 for k in range(decomposition.dimension()))
                domain_id = decomposition.domain_id(domain_location)
                piece_reader = piece_readers[domain_id]
                assert isinstance(piece_reader, VTRReader)
                piece_ordinates = piece_reader.ordinates(direction)
                num_ordinates = len(piece_ordinates)
                ordinates[direction][index_offset : index_offset + num_ordinates] = piece_ordinates
                index_offset += num_ordinates - 1
        return RectilinearMesh(
            extents=(extents[0], extents[1], extents[2]), ordinates=(ordinates[0], ordinates[1], ordinates[2])
        )


class PVTIReader(_PVTKReader):
    """Reads meshes from the VTK file format for parallel image grids"""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__("ImageData", VTIReader, *args, **kwargs)

    def _make_structured_mesh(
        self,
        decomposition: _PVTKReader._StructuredDecomposition,
        piece_readers: list[_FieldDataReader],
        piece_fields: list[mesh_protocols.MeshFields],
        merger: StructuredFieldMerger,
    ) -> ImageMesh:
        first_reader = piece_readers[0]
        assert isinstance(first_reader, VTIReader)

        origin = first_reader.origin
        spacing = first_reader.spacing
        extents = decomposition.merged_extents()
        return ImageMesh(
            extents=(extents[0], extents[1], extents[2]),
            origin=(origin[0], origin[1], origin[2]),
            spacing=(spacing[0], spacing[1], spacing[2]),
            basis=first_reader.basis,
        )


_VTK_EXTENSION_TO_READER[".pvtu"] = PVTUReader
_VTK_EXTENSION_TO_READER[".pvtp"] = PVTPReader
_VTK_EXTENSION_TO_READER[".pvts"] = PVTSReader
_VTK_EXTENSION_TO_READER[".pvtr"] = PVTRReader
_VTK_EXTENSION_TO_READER[".pvti"] = PVTIReader

_VTK_TYPE_TO_EXTENSION["PUnstructuredGrid"] = ".pvtu"
_VTK_TYPE_TO_EXTENSION["PPolyData"] = ".pvtp"
_VTK_TYPE_TO_EXTENSION["PStructuredGrid"] = ".pvts"
_VTK_TYPE_TO_EXTENSION["PRectilinearGrid"] = ".pvtr"
_VTK_TYPE_TO_EXTENSION["PImageData"] = ".pvti"
