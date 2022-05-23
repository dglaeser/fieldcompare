from os import remove
from io import StringIO
from pathlib import Path
from typing import List, Optional

from _common import write_file, make_test_mesh, make_point_data_array, make_cell_data_arrays
from _common import PointDataStorage, CellDataStorage

from fieldcompare import FileComparison, FileComparisonOptions
from fieldcompare import StreamLogger


TEST_DATA_PATH = Path(__file__).resolve().parent / Path("data")


def _write_mesh_file(filename: str,
                     num_point_fields: int,
                     num_cell_fields: int,
                     perturbation: Optional[float] = None) -> None:
    mesh = make_test_mesh()
    point_data = PointDataStorage()
    for i in range(num_point_fields):
        values = make_point_data_array(mesh)
        if perturbation is not None:
            values[0] += perturbation
        point_data.add(f"pfield_{i+1}", values)

    cell_data = CellDataStorage()
    for i in range(num_cell_fields):
        values = make_cell_data_arrays(mesh)
        if perturbation is not None:
            for _vals in values.values():
                _vals[0] += perturbation
        cell_data.add(f"cfield_{i+1}", values)

    write_file(filename, mesh, point_data, cell_data)


def test_file_comparison_identical_files_and_default_options():
    mesh_file = "test_file_comparison_identical_files_and_default_options.vtk"
    _write_mesh_file(mesh_file, num_point_fields=1, num_cell_fields=1)

    assert FileComparison()(mesh_file, mesh_file)

    remove(mesh_file)


def test_file_comparison_fails_without_mesh_reordering():
    test_file = str(TEST_DATA_PATH / Path("test_mesh.vtu"))
    reference_file = str(TEST_DATA_PATH / Path("test_mesh_permutated.vtu"))

    assert FileComparison()(test_file, reference_file)
    assert not FileComparison(
        FileComparisonOptions(disable_mesh_reordering=True)
    )(test_file, reference_file)


def test_file_comparison_missing_reference_field():
    base_filename = "test_file_comparison_missing_reference_field"
    result_filename = f"{base_filename}_result.vtk"
    reference_filename = f"{base_filename}_reference.vtk"
    _write_mesh_file(result_filename, num_point_fields=2, num_cell_fields=1)
    _write_mesh_file(reference_filename, num_point_fields=1, num_cell_fields=1)

    assert not FileComparison()(result_filename, reference_filename)
    assert FileComparison(
        FileComparisonOptions(ignore_missing_reference_fields=True)
    )(result_filename, reference_filename)

    remove(result_filename)
    remove(reference_filename)


def test_file_comparison_missing_result_field():
    base_filename = "test_file_comparison_missing_result_field"
    result_filename = f"{base_filename}_result.vtk"
    reference_filename = f"{base_filename}_reference.vtk"
    _write_mesh_file(result_filename, num_point_fields=1, num_cell_fields=1)
    _write_mesh_file(reference_filename, num_point_fields=2, num_cell_fields=1)

    assert not FileComparison()(result_filename, reference_filename)
    assert FileComparison(
        FileComparisonOptions(ignore_missing_result_fields=True)
    )(result_filename, reference_filename)

    remove(result_filename)
    remove(reference_filename)


def test_file_comparison_inclusion_filter():
    stream = StringIO()
    logger = StreamLogger(stream)

    base_filename = "test_file_comparison_inclusion_filter"
    result_filename = f"{base_filename}_result.vtk"
    reference_filename = f"{base_filename}_reference.vtk"
    _write_mesh_file(result_filename, num_point_fields=2, num_cell_fields=2)
    _write_mesh_file(reference_filename, num_point_fields=2, num_cell_fields=2)

    def _inclusion_filter(names: List[str]) -> List[str]:
        return list(filter(lambda n: "field_1" in n, names))

    assert FileComparison(
        FileComparisonOptions(field_inclusion_filter=_inclusion_filter),
        logger=logger
    )(result_filename, reference_filename)
    log_output = stream.getvalue()

    assert any(
        "Comparison of" in line and "field_1" in line
        for line in log_output.split("\n")
    )
    assert not any(
        "Comparison of" in line and "field_2" in line
        for line in log_output.split("\n")
    )

    remove(result_filename)
    remove(reference_filename)


def test_file_comparison_exclusion_filter():
    stream = StringIO()
    logger = StreamLogger(stream)

    base_filename = "test_file_comparison_inclusion_filter"
    result_filename = f"{base_filename}_result.vtk"
    reference_filename = f"{base_filename}_reference.vtk"
    _write_mesh_file(result_filename, num_point_fields=2, num_cell_fields=2)
    _write_mesh_file(reference_filename, num_point_fields=2, num_cell_fields=2)

    def _exclusion_filter(names: List[str]) -> List[str]:
        return list(filter(lambda n: "field_1" in n, names))

    assert FileComparison(
        FileComparisonOptions(field_exclusion_filter=_exclusion_filter),
        logger=logger
    )(result_filename, reference_filename)
    log_output = stream.getvalue()

    assert not any(
        "Comparison of" in line and "field_1" in line
        for line in log_output.split("\n")
    )
    assert any(
        "Comparison of" in line and "field_2" in line
        for line in log_output.split("\n")
    )

    remove(result_filename)
    remove(reference_filename)


def test_file_comparison_tolerance_definition():
    base_filename = "test_file_comparison_inclusion_filter"
    result_filename = f"{base_filename}_result.vtk"
    reference_filename = f"{base_filename}_reference.vtk"
    _write_mesh_file(result_filename, num_point_fields=2, num_cell_fields=2)
    _write_mesh_file(reference_filename, num_point_fields=2, num_cell_fields=2, perturbation=1e-8)

    assert not FileComparison(FileComparisonOptions())(result_filename, reference_filename)
    assert FileComparison(
        FileComparisonOptions(absolute_tolerances=lambda n: 1e-7)
    )(result_filename, reference_filename)
    assert FileComparison(
        FileComparisonOptions(relative_tolerances=lambda n: 1)
    )(result_filename, reference_filename)

    remove(result_filename)
    remove(reference_filename)
