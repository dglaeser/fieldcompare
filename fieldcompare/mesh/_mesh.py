"""Class to represent computational meshes"""
from typing import Iterable, Tuple
from .._array import Array, ArrayLike, make_array


class Mesh:
    """Represents a computational mesh"""
    def __init__(self,
                 points: ArrayLike,
                 connectivity: Iterable[Tuple[str, ArrayLike]]) -> None:
        self._points = make_array(points)
        self._corners = {
            cell_type: make_array(corners)
            for cell_type, corners in connectivity
        }

    @property
    def points(self) -> Array:
        """Return the points of this mesh"""
        return self._points

    @property
    def cell_types(self) -> Iterable[str]:
        """Return the cell types present in this mesh"""
        return self._corners.keys()

    def connectivity(self, cell_type: str) -> Array:
        """Return the corner indices array for the cells of the given type"""
        return self._corners[cell_type]
