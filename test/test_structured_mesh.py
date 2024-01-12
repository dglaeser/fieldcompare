# SPDX-FileCopyrightText: 2023 Dennis Gläser <dennis.glaeser@iws.uni-stuttgart.de>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations
from itertools import product
from functools import reduce
from operator import mul
from math import pi, sin, cos

from fieldcompare.predicates import FuzzyEquality
from fieldcompare.mesh._structured_mesh import _locations_in
from fieldcompare.mesh import ImageMesh, StructuredFieldMerger as Merger
from numpy import ndarray, array, eye, all as np_all

import pytest


SPACE_DIMENSION = 3
FIELD_DIMENSIONS = [0, 1, 2]
TEST_LATTICE_SIZES = [
    (1,), (2,),
    (2, 1), (1, 2), (3, 3),
    (1, 2, 3), (3, 1, 2), (2, 2, 2)
]


@pytest.mark.parametrize("rotation_angle", [0.0, pi/4.0, -pi/4.0])
def test_rotated_image_mesh(rotation_angle):
    sinangle, cosangle = sin(rotation_angle), cos(rotation_angle)
    rot = array([[cosangle, -sinangle, 0], [sinangle, cosangle, 0], [0, 0, 1]])
    basis = eye(3, 3)*rot
    mesh = ImageMesh(
        extents=(1, 1, 1),
        origin=(0., 0., 0.),
        spacing=(1., 1., 1.),
        basis=basis
    )
    assert FuzzyEquality()(mesh.points, array([
        [0.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [1.0, 1.0, 0.0],
        [0.0, 0.0, 1.0],
        [1.0, 0.0, 1.0],
        [0.0, 1.0, 1.0],
        [1.0, 1.0, 1.0],
    ]).dot(basis))


@pytest.mark.parametrize("field_dim", FIELD_DIMENSIONS)
@pytest.mark.parametrize("lattice_size", TEST_LATTICE_SIZES)
def test_structured_point_field_merge(field_dim, lattice_size):
    dimension = len(lattice_size)
    pieces, fields, piece_sizes_along_axes = _make_pieces_and_fields(
        lattice_size,
        make_point_fields=True,
        field_dimension=field_dim
    )

    merger = Merger(piece_sizes_along_axes)
    merged = merger.merge_point_fields(lambda loc: fields[loc])

    num_points_along_axes = [sum(n for n in piece_sizes_along_axes[d]) + 1 for d in range(dimension)]
    num_total_points = reduce(mul, num_points_along_axes)
    assert merged.shape == tuple([num_total_points] + list(_tensor_shape(field_dim)))

    nd_shape = tuple(num_points_along_axes + list(_tensor_shape(field_dim)))
    merged_non_flat_view = merged.reshape(nd_shape, order='F')
    for i, loc in enumerate(_locations_in(lattice_size)):
        offsets = [
            sum(piece_sizes_along_axes[d][k] for k in range(loc[d])) for d in range(dimension)
        ]
        piece_shape = pieces[loc]
        for ituple in product(*list(range(1, n) for n in piece_shape)):
            ituple = tuple(it + o for it, o in zip(ituple, offsets))
            merged_value = merged_non_flat_view[ituple]
            expected_value = _to_tensor(field_dim, _value_in_domain(i))
            assert np_all(merged_value == expected_value)


@pytest.mark.parametrize("field_dim", FIELD_DIMENSIONS)
@pytest.mark.parametrize("lattice_size", TEST_LATTICE_SIZES)
def test_structured_cell_field_merge(field_dim, lattice_size):
    dimension = len(lattice_size)
    pieces, fields, piece_sizes_along_axes = _make_pieces_and_fields(
        lattice_size,
        make_point_fields=False,
        field_dimension=field_dim
    )

    merger = Merger(piece_sizes_along_axes)
    merged = merger.merge_cell_fields(lambda loc: fields[loc])

    num_cells_along_axes = [sum(n for n in piece_sizes_along_axes[d]) for d in range(dimension)]
    num_total_cells = reduce(mul, num_cells_along_axes)
    assert merged.shape == tuple([num_total_cells] + list(_tensor_shape(field_dim)))

    nd_shape = tuple(num_cells_along_axes + list(_tensor_shape(field_dim)))
    merged_non_flat_view = merged.reshape(nd_shape, order='F')
    for i, loc in enumerate(_locations_in(lattice_size)):
        offsets = [
            sum(piece_sizes_along_axes[d][k] for k in range(loc[d])) for d in range(dimension)
        ]
        piece_shape = pieces[loc]
        for ituple in product(*list(range(1, n) for n in piece_shape)):
            ituple = tuple(it + o for it, o in zip(ituple, offsets))
            merged_value = merged_non_flat_view[ituple]
            expected_value = _to_tensor(field_dim, _value_in_domain(i))
            assert np_all(merged_value == expected_value)

def _make_pieces_and_fields(
    lattice_size, make_point_fields: bool, field_dimension: int
) -> tuple[ndarray, ndarray, tuple[tuple[int]]]:
    piece_sizes_along_axes = tuple(
        tuple([k + 3 for k in range(lattice_size[i])])
        for i in range(len(lattice_size))
    )
    pieces = ndarray(shape=lattice_size, dtype=object)
    fields = ndarray(shape=lattice_size, dtype=object)
    for i, loc in enumerate(_locations_in(lattice_size)):
        this_shape = tuple([piece_sizes_along_axes[d][loc[d]] for d in range(len(loc))])
        num_values = reduce(mul, (n + (1 if make_point_fields else 0) for n in this_shape))
        pieces[loc] = this_shape
        fields[loc] = array([
            _to_tensor(field_dimension, _value_in_domain(i)) for _ in range(num_values)
        ])
    return pieces, fields, piece_sizes_along_axes


def _value_in_domain(i) -> int:
    return 42 + i


def _to_tensor(dim: int, value: int) -> ndarray | int:
    if dim == 0:
        return value
    result = ndarray(shape=_tensor_shape(dim), dtype=int)
    result.fill(value)
    return result


def _tensor_shape(dim: int) -> tuple[int, ...]:
    if dim == 0:
        return tuple()
    return tuple(SPACE_DIMENSION for _ in range(dim))
