# SPDX-FileCopyrightText: 2023 Dennis Gläser <dennis.glaeser@iws.uni-stuttgart.de>
# SPDX-License-Identifier: GPL-3.0-or-later

from itertools import product
from functools import reduce
from operator import mul

from fieldcompare.mesh._structured_mesh import _locations_in
from fieldcompare.mesh import StructuredFieldMerger as Merger
from numpy import ndarray, array

import pytest


TEST_LATTICE_SIZES = [
    (1,), (2,),
    (2, 1), (1, 2), (3, 3),
    (1, 2, 3), (3, 1, 2), (2, 2, 2)
]


@pytest.mark.parametrize("lattice_size", TEST_LATTICE_SIZES)
def test_structured_point_field_merge(lattice_size):
    dimension = len(lattice_size)
    pieces, fields, piece_sizes_along_axes = _make_pieces_and_fields(lattice_size, make_point_fields=True)

    merger = Merger(piece_sizes_along_axes)
    merged = merger.merge_point_fields(lambda loc: fields[*loc])

    num_points_along_axes = [sum(n for n in piece_sizes_along_axes[d]) + 1 for d in range(dimension)]
    num_total_points = reduce(mul, num_points_along_axes)
    assert merged.shape == (num_total_points, )

    merged_non_flat_view = merged.reshape(tuple(num_points_along_axes), order='F')
    for i, loc in enumerate(_locations_in(lattice_size)):
        offsets = [
            sum(piece_sizes_along_axes[d][k] for k in range(loc[d])) for d in range(dimension)
        ]
        piece_shape = pieces[*loc]
        for ituple in product(*list(range(1, n) for n in piece_shape)):
            ituple = tuple(it + o for it, o in zip(ituple, offsets))
            assert merged_non_flat_view[*ituple] == _value_in_domain(i)


@pytest.mark.parametrize("lattice_size", TEST_LATTICE_SIZES)
def test_structured_cell_field_merge(lattice_size):
    dimension = len(lattice_size)
    pieces, fields, piece_sizes_along_axes = _make_pieces_and_fields(lattice_size, make_point_fields=False)

    merger = Merger(piece_sizes_along_axes)
    merged = merger.merge_cell_fields(lambda loc: fields[*loc])

    num_cells_along_axes = [sum(n for n in piece_sizes_along_axes[d]) for d in range(dimension)]
    num_total_cells = reduce(mul, num_cells_along_axes)
    assert merged.shape == (num_total_cells, )

    merged_non_flat_view = merged.reshape(tuple(num_cells_along_axes), order='F')
    for i, loc in enumerate(_locations_in(lattice_size)):
        offsets = [
            sum(piece_sizes_along_axes[d][k] for k in range(loc[d])) for d in range(dimension)
        ]
        piece_shape = pieces[*loc]
        for ituple in product(*list(range(1, n) for n in piece_shape)):
            ituple = tuple(it + o for it, o in zip(ituple, offsets))
            assert merged_non_flat_view[*ituple] == _value_in_domain(i)


def _make_pieces_and_fields(lattice_size, make_point_fields: bool) -> tuple[ndarray, ndarray, tuple[tuple[int]]]:
    piece_sizes_along_axes = tuple(
        tuple([k + 3 for k in range(lattice_size[i])])
        for i in range(len(lattice_size))
    )
    pieces = ndarray(shape=lattice_size, dtype=object)
    fields = ndarray(shape=lattice_size, dtype=object)
    for i, loc in enumerate(_locations_in(lattice_size)):
        this_shape = tuple([piece_sizes_along_axes[d][loc[d]] for d in range(len(loc))])
        num_values = reduce(mul, (n + (1 if make_point_fields else 0) for n in this_shape))
        pieces[*loc] = this_shape
        fields[*loc] = array([_value_in_domain(i) for _ in range(num_values)])
    return pieces, fields, piece_sizes_along_axes


def _value_in_domain(i) -> float:
    return 42 + i
