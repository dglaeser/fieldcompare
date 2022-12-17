"""Transformation functions for mesh fields"""

from copy import deepcopy
from typing import Optional, Dict
from .._array import Array, concatenate, make_array, make_zeros
from ._mesh_fields import remove_cell_type_suffix

from ._mesh import Mesh
from ._mesh_fields import MeshFields
from . import protocols, permutations


def sort(mesh_fields: protocols.MeshFields) -> protocols.MeshFields:
    """Sort the given mesh fields to arrive at a unique representation"""
    return mesh_fields.transformed(
        permutations.remove_unconnected_points
    ).transformed(
        permutations.sort_points
    ).transformed(
        permutations.sort_cells
    )


def merge(*mesh_fields: protocols.MeshFields) -> protocols.MeshFields:
    """Merge the given mesh fields into a single one"""
    result: Optional[protocols.MeshFields] = None
    for i, fields in enumerate(mesh_fields):
        if i == 0:
            result = fields
        else:
            assert result is not None
            result = _merge(result, fields)
    assert result is not None
    return result


def _merge(fields1: protocols.MeshFields,
           fields2: protocols.MeshFields) -> MeshFields:
    points = concatenate((
        fields1.domain.points,
        fields2.domain.points
    ))

    # merged cell connectivities
    points2_offset = len(fields1.domain.points)
    cells_dict: Dict[str, Array] = {
        ct: make_array(fields1.domain.connectivity(ct))
        for ct in fields1.domain.cell_types
    }
    for ct in fields2.domain.cell_types:
        connectivity_with_offset = make_array(fields2.domain.connectivity(ct) + points2_offset)
        if ct in cells_dict:
            cells_dict[ct] = concatenate((cells_dict[ct], connectivity_with_offset))
        else:
            cells_dict[ct] = connectivity_with_offset

    # merged cell fields
    raw_cell_field_names = set()
    cell_fields: Dict[str, Dict[str, Array]] = {ct: {} for ct in cells_dict}
    for field, ct in fields1.cell_fields_types:
        raw_field_name = remove_cell_type_suffix(ct, field.name)
        cell_fields[ct][raw_field_name] = field.values
        raw_cell_field_names.add(raw_field_name)
    for field, ct in fields2.cell_fields_types:
        raw_field_name = remove_cell_type_suffix(ct, field.name)
        raw_cell_field_names.add(raw_field_name)
        if raw_field_name in cell_fields[ct]:
            cell_fields[ct][raw_field_name] = concatenate((
                cell_fields[ct][raw_field_name],
                field.values
            ))
        else:
            cell_fields[ct][raw_field_name] = field.values

    # merged point fields
    point_fields1: Dict[str, Array] = {f.name: f.values for f in fields1.point_fields}
    point_fields2: Dict[str, Array] = {f.name: f.values for f in fields2.point_fields}
    point_fields: Dict[str, Array] = {}
    for name in point_fields1:
        if name in point_fields2:
            point_fields[name] = concatenate((point_fields1[name], point_fields2[name]))
        else:
            zero = make_zeros(shape=point_fields1[name].shape[1:], dtype=point_fields1[name].dtype)
            point_fields[name] = concatenate((
                make_array(point_fields1[name]),
                make_array(
                    [deepcopy(zero) for _ in range(len(fields2.domain.points))],
                    dtype=point_fields1[name].dtype
                )
            ))
    for name in filter(lambda n: n not in point_fields, point_fields2):
        zero = make_zeros(shape=point_fields2[name].shape[1:], dtype=point_fields2[name].dtype)
        point_fields[name] = concatenate((
            make_array(
                [deepcopy(zero) for _ in range(points2_offset)],
                dtype=point_fields2[name].dtype
            ),
            make_array(point_fields2[name])
        ))

    return MeshFields(
        mesh=Mesh(
            points=points,
            connectivity=((ct, connectivity) for ct, connectivity in cells_dict.items())
        ),
        point_data=point_fields,
        cell_data={
            name: [cell_fields[ct][name] for ct in cells_dict]
            for name in raw_cell_field_names
        }
    )
