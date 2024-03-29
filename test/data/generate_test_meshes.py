# SPDX-FileCopyrightText: 2023 Dennis Gläser <dennis.glaeser@iws.uni-stuttgart.de>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Generate the mesh files used in the tests"""

from __future__ import annotations

import random
import numpy as np

from os.path import splitext
from copy import deepcopy
from meshio import Mesh
from meshio.xdmf import TimeSeriesWriter


def _test_function(coord) -> float:
    return (1.0 - coord[0])*(1.0 - coord[1])


def _test_vector(coord, dim: int = 3) -> list[float]:
    return [_test_function(coord) for _ in range(dim)]


def _add_ghost_points(mesh, use_preexisting_points=True):
    cpy = deepcopy(mesh)
    if use_preexisting_points:
        num_points = len(mesh.points)
        cpy.points = np.append(mesh.points, mesh.points[0:int(num_points/2)], axis=0)
    else:
        dim = len(mesh.points[0])
        max_point = np.array([
            np.max(mesh.points[:, i]) for i in range(dim)
        ])
        cpy.points = np.append(mesh.points, [max_point+max_point], axis=0)
        cpy.points = np.append(mesh.points, [max_point+max_point+max_point], axis=0)
    return cpy


def _make_non_conforming_test_mesh(refinement: int = 1):
    num_cells_x = int(pow(2, refinement))
    num_cells_y = int(pow(2, refinement))

    dx = 1.0/num_cells_x
    dy = 1.0/num_cells_y

    points: list = []
    cells: list = [("quad", [])]
    for i in range(num_cells_x):
        for j in range(num_cells_y):
            p0_idx = len(points)
            p0 = [i*dx, j*dy, 0.0]
            points.append(p0)
            points.append([p0[0] + dx, p0[1] + 0.0, 0.0])
            points.append([p0[0] + dx, p0[1] + dy, 0.0])
            points.append([p0[0] + 0.0, p0[1] + dy, 0.0])
            cells[0][1].append([p0_idx, p0_idx+1, p0_idx+2, p0_idx+3])
    return Mesh(points, cells)


def _get_cell_center(cell, mesh_points):
    center = deepcopy(mesh_points[cell[0]])
    dim = len(center)
    for corner_idx in cell[1:]:
        center = [center[i] + mesh_points[corner_idx][i] for i in range(dim)]
    center = [center[i]/len(cell) for i in range(dim)]
    return center


def _make_test_mesh():
    points = [
        [0.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
        [1.0, 1.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.5, 0.5, 0.0],
        [2.0, 0.0, 0.0],
        [2.0, 1.0, 0.0]
    ]

    cells = [
        ("triangle", [
            [0, 1, 4],
            [1, 2, 4],
            [2, 3, 4],
            [3, 0, 4]
        ]),
        ("quad", [
            [1, 5, 6, 2]
        ])
    ]

    return Mesh(
        points,
        cells,
        point_data={
            "point_index": list(range(len(points))),
            "function": [_test_function(x) for x in points],
            "pvector": [_test_vector(x, 3) for x in points],
        },
        cell_data={
            "cell_index": [[0, 1, 2, 3], [4]],
            "cell_func_values": [
                [_test_function(_get_cell_center(cell, points)) for cell in corners]
                for _, corners in cells
            ],
            "cvector": [
                [_test_vector(_get_cell_center(cell, points)) for cell in corners]
                for _, corners in cells
            ],
        }
    )


def _permutate_mesh(mesh):
    seed = 1
    random_instance = random.Random(seed)

    def _permutated_array(orig_array, index_map):
        return [orig_array[idx] for idx in index_map]

    point_index_map = list(range(len(mesh.points)))
    random_instance.shuffle(point_index_map)
    new_points = [mesh.points[idx] for idx in point_index_map]
    new_point_data = {
        n: _permutated_array(mesh.point_data[n], point_index_map) for n in mesh.point_data
    }

    new_cells = []
    cell_type_index_maps = {}
    point_index_map_inverse = _get_inverse_index_map(point_index_map)
    for cell_block in mesh.cells:
        cell_type = cell_block.type
        corner_arrays = cell_block.data
        cell_type_index_map = list(range(len(corner_arrays)))
        random_instance.shuffle(cell_type_index_map)
        cell_type_index_maps[cell_type] = deepcopy(cell_type_index_map)

        permutated_cells = _permutated_array(corner_arrays, cell_type_index_map)
        permutated_cells = list(map(
            lambda corners: [point_index_map_inverse[i] for i in corners],
            permutated_cells
        ))
        new_cells.append((cell_type, permutated_cells))

    new_cell_data = {}
    for array_name in mesh.cell_data:
        for cell_block, array_values in zip(mesh.cells, mesh.cell_data[array_name]):
            cell_type = cell_block.type
            if array_name not in new_cell_data:
                new_cell_data[array_name] = []
            new_cell_data[array_name].append(_permutated_array(
                array_values, cell_type_index_maps[cell_type]
            ))

    return Mesh(
        new_points,
        new_cells,
        point_data=new_point_data,
        cell_data=new_cell_data
    )


def _get_inverse_index_map(forward_index_map):
    inverse = [0 for i in range(len(forward_index_map))]
    for list_index, mapped_index in enumerate(forward_index_map):
        inverse[mapped_index] = list_index
    return inverse


def _perturb_mesh(mesh, max_perturbation=1e-9):
    seed = 1
    random_instance = random.Random(seed)

    def _perturbed_position(pos):
        return [coord + random_instance.uniform(0, max_perturbation) for coord in pos]

    return Mesh(
        [_perturbed_position(point) for point in mesh.points],
        mesh.cells,
        point_data=mesh.point_data,
        cell_data=mesh.cell_data
    )


def _get_time_series_point_data_values(mesh, num_time_steps, max_perturbation=0.0):
    result = []
    for ts in range(num_time_steps-1):
        result.append({
            "point_data": np.array([_test_function(p)*(ts+1) for p in mesh.points])
        })

    # perturb the last time step
    seed = 1
    random_instance = random.Random(seed)
    result.append({
        "point_data": np.array([
            _test_function(p)*num_time_steps + random_instance.uniform(0, max_perturbation)
            for p in mesh.points
        ])
    })

    return result


def _get_time_series_cell_data_values(mesh, num_time_steps, max_perturbation=0.0):
    result = []
    for ts in range(num_time_steps-1):
        result.append({"cell_data": []})
        for cell_block in mesh.cells:
            result[-1]["cell_data"].append(np.array([
                _test_function(_get_cell_center(cell, mesh.points))*(ts+1)
                for cell in cell_block.data
            ]))

    # perturb the last time step
    seed = 1
    random_instance = random.Random(seed)
    result.append({"cell_data": []})
    for cell_block in mesh.cells:
        result[-1]["cell_data"].append(np.array([
            _test_function(
                _get_cell_center(cell, mesh.points)
            )*num_time_steps + random_instance.uniform(0, max_perturbation)
            for cell in cell_block.data
        ]))

    return result


def _write_time_series(filename, mesh, point_data, cell_data, num_time_steps):
    with TimeSeriesWriter(filename) as writer:
        writer.write_points_cells(mesh.points, mesh.cells)
        for ts in range(num_time_steps):
            writer.write_data(ts, point_data[ts], cell_data[ts])
    _add_license_header(filename)


def _write_mesh(filename, mesh):
    mesh.write(filename, binary=False)
    _add_license_header(filename)


def _add_license_header(filename) -> None:
    license_text = """
<!--SPDX-FileCopyrightText: 2023 Dennis Gläser <dennis.glaeser@iws.uni-stuttgart.de>-->
<!--SPDX-License-Identifier: GPL-3.0-or-later-->
"""
    if splitext(filename)[1] == ".vtu":
        xml_version_string = '<?xml version="1.0"?>'
        content = open(filename).read()
        content = content.split(xml_version_string)[1]
        content = f"{xml_version_string}{license_text}{content}"
        with open(filename, "w") as vtu_file:
            vtu_file.write(content)
    elif splitext(filename)[1] == ".xdmf":
        content = open(filename).read()
        with open(filename, "w") as xdmf_file:
            xdmf_file.write(f"{license_text}{content}")
    else:
        raise NotImplementedError(f"Unknown file format for '{filename}'")


if __name__ == "__main__":
    test_mesh = _make_test_mesh()
    _write_mesh("test_mesh.vtu", test_mesh)
    permutated_mesh = _permutate_mesh(test_mesh)
    _write_mesh("test_mesh_permutated.vtu", permutated_mesh)
    disturbed_mesh = _perturb_mesh(permutated_mesh)
    _write_mesh("test_mesh_permutated_perturbed.vtu", disturbed_mesh)

    point_values = _get_time_series_point_data_values(test_mesh, 3)
    cell_values = _get_time_series_cell_data_values(test_mesh, 3)
    _write_time_series("test_time_series.xdmf", test_mesh, point_values, cell_values, 3)

    point_values = _get_time_series_point_data_values(permutated_mesh, 3)
    cell_values = _get_time_series_cell_data_values(permutated_mesh, 3)
    _write_time_series("test_time_series_permutated.xdmf", permutated_mesh, point_values, cell_values, 3)

    point_values = _get_time_series_point_data_values(test_mesh, 3, 1e-8)
    cell_values = _get_time_series_cell_data_values(test_mesh, 3, 1e-8)
    _write_time_series("test_time_series_perturbed.xdmf", test_mesh, point_values, cell_values, 3)

    non_conforming = _make_non_conforming_test_mesh()
    _write_mesh("test_non_conforming_mesh.vtu", non_conforming)
    non_conforming_permuted = _permutate_mesh(non_conforming)
    _write_mesh("test_non_conforming_mesh_permutated.vtu", non_conforming_permuted)
    non_conforming_permuted_perturbed = _perturb_mesh(non_conforming_permuted)
    _write_mesh("test_non_conforming_mesh_permutated_perturbed.vtu", non_conforming_permuted_perturbed)

    non_conforming_with_ghosts = _add_ghost_points(non_conforming)
    _write_mesh("test_non_conforming_mesh_with_ghost_points.vtu", non_conforming_with_ghosts)

    non_conforming_with_ghosts = _add_ghost_points(non_conforming, use_preexisting_points=False)
    _write_mesh("test_non_conforming_mesh_with_non_overlapping_ghost_points.vtu", non_conforming_with_ghosts)

    non_conforming_with_ghosts = _add_ghost_points(non_conforming_permuted, use_preexisting_points=False)
    _write_mesh(
        "test_non_conforming_mesh_with_non_overlapping_ghost_points_permutated.vtu",
        non_conforming_with_ghosts
    )
