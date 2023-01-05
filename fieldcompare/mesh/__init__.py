"""Classes and functions related to fields defined on computational meshes."""

from ._mesh import Mesh
from ._cell_type import CellType, CellTypes
from ._mesh_fields import MeshFields
from ._mesh_fields_comparator import MeshFieldsComparator
from ._transformations import strip_orphan_points, sort_points, sort_cells, sort, merge, extend_space_dimension_to

__all__ = [
    "Mesh",
    "CellType",
    "CellTypes",
    "MeshFields",
    "strip_orphan_points",
    "sort_points",
    "sort_cells",
    "sort",
    "merge",
]
