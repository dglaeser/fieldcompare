# SPDX-FileCopyrightText: 2023 Dennis Gläser <dennis.glaeser@iws.uni-stuttgart.de>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Test the command-line interface of fieldcompare"""

from os import remove, listdir, makedirs
from os.path import isfile, join, splitext
from shutil import rmtree, copytree, copy
from pathlib import Path
from io import StringIO
from xml.etree import ElementTree

from fieldcompare._cli import main
from fieldcompare._cli._logger import CLILogger
from data.generate_test_meshes import _make_test_mesh, _perturb_mesh
from data.generate_test_meshes import _get_time_series_point_data_values
from data.generate_test_meshes import _get_time_series_cell_data_values
from data.generate_test_meshes import _write_time_series


TEST_DATA_PATH = Path(__file__).resolve().parent / Path("data")


def test_cli_file_mode_pass():
    assert main([
        "file",
        str(TEST_DATA_PATH / Path("test_mesh.vtu")),
        str(TEST_DATA_PATH / Path("test_mesh.vtu"))
    ]) == 0


def test_cli_file_mode_reader_selection():
    csv_file = "test_tabular_data.csv"
    csv_file_path = str(TEST_DATA_PATH / Path(csv_file))
    modified_ext_filename = f"{splitext(csv_file)[0]}.dat"
    copy(csv_file_path, modified_ext_filename)
    assert main([
        "file",
        csv_file_path,
        modified_ext_filename,
        "--read-as", "dsv:*.dat"
    ]) == 0
    remove(modified_ext_filename)


def test_cli_file_mode_reader_selection_multiple_occurrences():
    csv_file = "test_tabular_data.csv"
    csv_file_path = str(TEST_DATA_PATH / Path(csv_file))
    modified_ext_filename = f"{splitext(csv_file)[0]}.dat"
    copy(csv_file_path, modified_ext_filename)
    assert main([
        "file",
        csv_file_path,
        modified_ext_filename,
        "--read-as", "dsv:*.dat",
        "--read-as", "mesh:*dat"
    ]) == 0
    remove(modified_ext_filename)


def test_cli_file_mode_reader_selection_with_options():
    csv_file = str(TEST_DATA_PATH / Path("test_tabular_data.csv"))
    csv_file_copy = f"{splitext(csv_file)[0]}.dat"
    copy(csv_file, csv_file_copy)
    assert main([
        "file",
        csv_file,
        csv_file_copy,
        "--read-as", 'dsv:*.dat'
    ]) == 0
    assert main([
        "file",
        csv_file,
        csv_file_copy,
        "--read-as", 'dsv{"use_names": true, "skip_rows": 0}:*.dat'
    ]) == 0
    assert main([
        "file",
        csv_file,
        csv_file_copy,
        "--read-as", 'dsv{"use_names": false, "skip_rows": 1}:*.dat'
    ]) == 1  # should fail because of non-matching field names
    remove(csv_file_copy)


def test_cli_file_mode_default_reader_selection_with_options():
    csv_file = str(TEST_DATA_PATH / Path("test_tabular_data.csv"))
    csv_file_copy = f"{splitext(csv_file)[0]}.dat"
    copy(csv_file, csv_file_copy)
    assert main([
        "file",
        csv_file,
        csv_file_copy,
        "--read-as", 'dsv'
    ]) == 0
    assert main([
        "file",
        csv_file,
        csv_file_copy,
        "--read-as", 'dsv{"use_names": true, "skip_rows": 0}'
    ]) == 0
    assert main([
        "file",
        csv_file,
        csv_file_copy,
        "--read-as", 'dsv{"use_names": false, "skip_rows": 1}'
    ]) == 0
    assert main([
        "file",
        str(TEST_DATA_PATH / Path("test_mesh.vtu")),
        str(TEST_DATA_PATH / Path("test_mesh.vtu")),
        "--read-as", 'dsv{"use_names": false, "skip_rows": 1}'
    ]) == 1  # should fail, trying to read a mesh as dsv
    remove(csv_file_copy)


def test_cli_file_mode_junit_report():
    report_filename = "file_mode_junit.xml"
    if isfile(report_filename):
        remove(report_filename)
    assert main([
        "file",
        str(TEST_DATA_PATH / Path("test_mesh.vtu")),
        str(TEST_DATA_PATH / Path("test_mesh_permutated.vtu")),
        "--junit-xml", report_filename
    ]) == 0
    assert isfile(report_filename)
    ElementTree.parse(report_filename)
    remove(report_filename)


def test_cli_file_mode_fail_on_perturbed_mesh():
    _mesh = _make_test_mesh()
    _perturbed_mesh = _perturb_mesh(_make_test_mesh(), max_perturbation=1e-3)

    _mesh_filename = "_test_mesh_cli_file_mode_fail.vtu"
    _perturbed_mesh_filename = _mesh_filename.replace(".vtu", "_reference.vtu")
    _mesh.write(_mesh_filename)
    _perturbed_mesh.write(_perturbed_mesh_filename)
    assert main(["file", _mesh_filename, _perturbed_mesh_filename]) == 1

    remove(_mesh_filename)
    remove(_perturbed_mesh_filename)


def test_cli_file_mode_fail_on_perturbed_mesh_without_mesh_reordering():
    # pass with mesh-reordering
    assert main([
        "file",
        str(TEST_DATA_PATH / Path("test_mesh.vtu")),
        str(TEST_DATA_PATH / Path("test_mesh_permutated.vtu"))
    ]) == 0

    # fail without mesh-reordering
    assert main([
        "file",
        str(TEST_DATA_PATH / Path("test_mesh.vtu")),
        str(TEST_DATA_PATH / Path("test_mesh_permutated.vtu")),
        "--disable-mesh-reordering"
    ]) == 1


def test_cli_file_mode_fail_on_permuted_non_conforming_mesh_without_ghost_removal():
    # pass with mesh-reordering
    assert main([
        "file",
        str(TEST_DATA_PATH / Path("test_non_conforming_mesh.vtu")),
        str(TEST_DATA_PATH / Path("test_non_conforming_mesh_with_ghost_points.vtu"))
    ]) == 0

    # fail without mesh-reordering
    assert main([
        "file",
        str(TEST_DATA_PATH / Path("test_non_conforming_mesh.vtu")),
        str(TEST_DATA_PATH / Path("test_non_conforming_mesh_with_ghost_points.vtu")),
        "--disable-mesh-orphan-point-removal"
    ]) == 1


def test_cli_file_mode_passes_without_ghost_removal_when_ghosts_do_not_overlap():
    assert main([
        "file",
        str(TEST_DATA_PATH / Path("test_non_conforming_mesh_with_non_overlapping_ghost_points_permutated.vtu")),
        str(TEST_DATA_PATH / Path("test_non_conforming_mesh_with_non_overlapping_ghost_points.vtu"))
    ]) == 0
    assert main([
        "file",
        str(TEST_DATA_PATH / Path("test_non_conforming_mesh_with_non_overlapping_ghost_points_permutated.vtu")),
        str(TEST_DATA_PATH / Path("test_non_conforming_mesh_with_non_overlapping_ghost_points.vtu")),
        "--disable-mesh-orphan-point-removal"
    ]) == 0


def test_cli_file_fails_without_space_dimension_matching():
    args = [
        "file",
        str(TEST_DATA_PATH / Path("poisson_time_series_3d.pvd")),
        str(TEST_DATA_PATH / Path("poisson_time_series_2d.xdmf")),
        "-rtol", "1e-7"
    ]
    assert main(args) == 0
    args = [
        "file",
        str(TEST_DATA_PATH / Path("poisson_time_series_3d.pvd")),
        str(TEST_DATA_PATH / Path("poisson_time_series_2d.xdmf")),
        "--disable-mesh-space-dimension-matching",
        "-rtol", "1e-7"
    ]
    assert main(args) == 1


def test_cli_file_mode_field_filter():
    with StringIO() as stream:
        logger = CLILogger(output_stream=stream)
        args = [
            "file",
            str(TEST_DATA_PATH / Path("test_mesh.vtu")),
            str(TEST_DATA_PATH / Path("test_mesh.vtu")),
            "--include-fields", "function"
        ]
        assert main(args, logger) == 0
        comparison_logs = [
            line for line in stream.getvalue().split("\n") if "Comparing the field" in line
        ]
        assert len(comparison_logs) == 1
        assert "function" in comparison_logs[0]


def test_cli_file_mode_field_exclusion_filter():
    with StringIO() as stream:
        logger = CLILogger(output_stream=stream)
        args = [
            "file",
            str(TEST_DATA_PATH / Path("test_mesh.vtu")),
            str(TEST_DATA_PATH / Path("test_mesh.vtu")),
            "--exclude-fields", "function"
        ]
        assert main(args, logger) == 0
        comparison_logs = [
            line for line in stream.getvalue().split("\n") if "Comparison of the field" in line
        ]
        assert not any("function" in log for log in comparison_logs)


def test_cli_file_mode_relative_tolerance_definition():
    _mesh = _make_test_mesh()
    _perturbed_mesh = _make_test_mesh()

    _rel_perturbation = 1e-3
    _func_values = _perturbed_mesh.point_data["function"]
    _func_values[0] += _func_values[0]*_rel_perturbation
    _perturbed_mesh.point_data["function"] = _func_values

    _mesh_filename = "_test_mesh_cli_file_mode_default_rel_tol_fail.vtu"
    _perturbed_mesh_filename = _mesh_filename.replace(".vtu", "_reference.vtu")
    _mesh.write(_mesh_filename)
    _perturbed_mesh.write(_perturbed_mesh_filename)
    assert main([
        "file",
        _mesh_filename,
        _perturbed_mesh_filename
    ]) == 1
    assert main([
        "file",
        _mesh_filename,
        _perturbed_mesh_filename,
        "--relative-tolerance", f"wrong_field:{str(_rel_perturbation*2.0)}"
    ]) == 1
    assert main([
        "file",
        _mesh_filename,
        _perturbed_mesh_filename,
        "--relative-tolerance", f"function:{str(_rel_perturbation*2.0)}"
    ]) == 0
    assert main([
        "file",
        _mesh_filename,
        _perturbed_mesh_filename,
        "--relative-tolerance", str(_rel_perturbation*2.0)
    ]) == 0

    remove(_mesh_filename)
    remove(_perturbed_mesh_filename)


def test_cli_file_mode_absolute_tolerance_definition():
    _mesh = _make_test_mesh()
    _perturbed_mesh = _make_test_mesh()

    _abs_perturbation = 1e-3
    _func_values = _perturbed_mesh.point_data["function"]
    _func_values[0] += _abs_perturbation
    _perturbed_mesh.point_data["function"] = _func_values

    _mesh_filename = "_test_mesh_cli_file_mode_default_rel_tol_fail.vtu"
    _perturbed_mesh_filename = _mesh_filename.replace(".vtu", "_reference.vtu")
    _mesh.write(_mesh_filename)
    _perturbed_mesh.write(_perturbed_mesh_filename)
    assert main([
        "file",
        _mesh_filename,
        _perturbed_mesh_filename,
        "--relative-tolerance", "0",
    ]) == 1
    assert main([
        "file",
        _mesh_filename,
        _perturbed_mesh_filename,
        "--relative-tolerance", "0",
        "--absolute-tolerance", f"wrong_field:{str(_abs_perturbation*2.0)}"
    ]) == 1
    assert main([
        "file",
        _mesh_filename,
        _perturbed_mesh_filename,
        "--relative-tolerance", "0",
        "--absolute-tolerance", f"function:{str(_abs_perturbation*2.0)}"
    ]) == 0
    assert main([
        "file",
        _mesh_filename,
        _perturbed_mesh_filename,
        "--relative-tolerance", "0",
        "--absolute-tolerance", str(_abs_perturbation*2.0)
    ]) == 0

    remove(_mesh_filename)
    remove(_perturbed_mesh_filename)


def test_cli_file_mode_missing_result_fields():
    _mesh = _make_test_mesh()
    _reference_mesh = _make_test_mesh()
    _mesh.point_data = {}

    _mesh_filename = "_test_cli_file_mode_missing_reference_fields.vtu"
    _reference_mesh_filename = _mesh_filename.replace(".vtu", "_reference.vtu")
    _mesh.write(_mesh_filename)
    _reference_mesh.write(_reference_mesh_filename)

    assert main([
        "file",
        _mesh_filename,
        _reference_mesh_filename,
    ]) == 1
    assert main([
        "file",
        _mesh_filename,
        _reference_mesh_filename,
        "--ignore-missing-reference-fields"
    ]) == 1
    assert main([
        "file",
        _mesh_filename,
        _reference_mesh_filename,
        "--ignore-missing-source-fields"
    ]) == 0

    remove(_mesh_filename)
    remove(_reference_mesh_filename)


def test_cli_file_mode_missing_reference_fields():
    _mesh = _make_test_mesh()
    _reference_mesh = _make_test_mesh()
    _reference_mesh.point_data = {}

    _mesh_filename = "_test_cli_file_mode_missing_reference_fields.vtu"
    _reference_mesh_filename = _mesh_filename.replace(".vtu", "_reference.vtu")
    _mesh.write(_mesh_filename)
    _reference_mesh.write(_reference_mesh_filename)

    assert main([
        "file",
        _mesh_filename,
        _reference_mesh_filename,
    ]) == 1
    assert main([
        "file",
        _mesh_filename,
        _reference_mesh_filename,
        "--ignore-missing-source-fields"
    ]) == 1
    assert main([
        "file",
        _mesh_filename,
        _reference_mesh_filename,
        "--ignore-missing-reference-fields"
    ]) == 0

    remove(_mesh_filename)
    remove(_reference_mesh_filename)


def test_cli_file_mode_missing_sequences_steps():
    _mesh = _make_test_mesh()
    _point_data_1 = _get_time_series_point_data_values(_mesh, num_time_steps=2)
    _cell_data_1 = _get_time_series_cell_data_values(_mesh, num_time_steps=2)
    _point_data_2 = _get_time_series_point_data_values(_mesh, num_time_steps=3)
    _cell_data_2 = _get_time_series_cell_data_values(_mesh, num_time_steps=3)

    _mesh_1_filename = "_test_cli_file_mode_missing_sequences_steps_field_1.xdmf"
    _mesh_2_filename = "_test_cli_file_mode_missing_sequences_steps_field_2.xdmf"
    _write_time_series(_mesh_1_filename, _mesh, _point_data_1, _cell_data_1, num_time_steps=2)
    _write_time_series(_mesh_2_filename, _mesh, _point_data_2, _cell_data_2, num_time_steps=3)

    assert main(["file", _mesh_1_filename, _mesh_2_filename]) == 1
    assert main(["file", _mesh_1_filename, _mesh_2_filename, "--ignore-missing-sequence-steps"]) == 0

    remove(_mesh_1_filename)
    remove(_mesh_2_filename)
    remove(_mesh_1_filename.replace(".xdmf", ".h5"))
    remove(_mesh_2_filename.replace(".xdmf", ".h5"))


def test_cli_file_mode_missing_sequences_steps_force_comparison():
    _mesh = _make_test_mesh()
    _point_data_1 = _get_time_series_point_data_values(_mesh, num_time_steps=2)
    _cell_data_1 = _get_time_series_cell_data_values(_mesh, num_time_steps=2)
    _point_data_2 = _get_time_series_point_data_values(_mesh, num_time_steps=3)
    _cell_data_2 = _get_time_series_cell_data_values(_mesh, num_time_steps=3)

    _mesh_1_filename = "_test_cli_file_mode_missing_sequences_steps_force_comparison_field_1.xdmf"
    _mesh_2_filename = "_test_cli_file_mode_missing_sequences_steps_force_comparison_field_2.xdmf"
    _write_time_series(_mesh_1_filename, _mesh, _point_data_1, _cell_data_1, num_time_steps=2)
    _write_time_series(_mesh_2_filename, _mesh, _point_data_2, _cell_data_2, num_time_steps=3)

    stream = StringIO()
    assert main(
        ["file", _mesh_1_filename, _mesh_2_filename],
        logger=CLILogger(output_stream=stream)
    ) == 1
    assert "Comparing the field" not in stream.getvalue()

    stream = StringIO()
    assert main(
        ["file", _mesh_1_filename, _mesh_2_filename, "--force-sequence-comparison"],
        logger=CLILogger(output_stream=stream)
    ) == 1
    assert "Comparing the field" in stream.getvalue()

    remove(_mesh_1_filename)
    remove(_mesh_2_filename)
    remove(_mesh_1_filename.replace(".xdmf", ".h5"))
    remove(_mesh_2_filename.replace(".xdmf", ".h5"))


def test_cli_directory_mode_pass():
    assert main(["dir", str(TEST_DATA_PATH), str(TEST_DATA_PATH)]) == 0


def test_cli_directory_mode_arg_is_not_a_directory():
    assert main(["dir", str(TEST_DATA_PATH), str(TEST_DATA_PATH / Path("test_mesh.vtu"))]) == 1
    assert main(["dir", str(TEST_DATA_PATH / Path("test_mesh.vtu")), str(TEST_DATA_PATH)]) == 1
    assert main(["dir", str(TEST_DATA_PATH / Path("test_mesh.vtu")), str(TEST_DATA_PATH / Path("test_mesh.vtu"))]) == 1


def test_cli_directory_mode_junit_report():
    tmp_results_path = TEST_DATA_PATH.resolve().parent / Path("cli_dir_junit_report_results_data")
    rmtree(tmp_results_path, ignore_errors=True)
    copytree(TEST_DATA_PATH, tmp_results_path, dirs_exist_ok=True)
    copy(
        tmp_results_path / Path("test_mesh_permutated.vtu"),
        tmp_results_path / Path("test_mesh.vtu"),
    )
    report_filename = "dir_mode_junit.xml"
    if isfile(report_filename):
        remove(report_filename)
    assert main([
        "dir",
        str(TEST_DATA_PATH),
        str(tmp_results_path),
        "--junit-xml", report_filename
    ]) == 0
    assert isfile(report_filename)
    ElementTree.parse(report_filename)
    remove(report_filename)
    rmtree(tmp_results_path)


def test_cli_directory_mode_field_filter():
    with StringIO() as stream:
        logger = CLILogger(output_stream=stream)
        args = [
            "dir",
            str(TEST_DATA_PATH),
            str(TEST_DATA_PATH),
            "--include-fields", "function"
        ]
        assert main(args, logger) == 0
        comparison_logs = [
            line for line in stream.getvalue().split("\n") if "Comparison of the field" in line
        ]
        assert all("function" in log for log in comparison_logs)


def test_cli_directory_mode_field_exclusion_filter():
    with StringIO() as stream:
        logger = CLILogger(output_stream=stream)
        args = [
            "dir",
            str(TEST_DATA_PATH),
            str(TEST_DATA_PATH),
            "--exclude-fields", "function"
        ]
        assert main(args, logger) == 0
        comparison_logs = [
            line for line in stream.getvalue().split("\n") if "Comparison of the field" in line
        ]
        assert not any("function" in log for log in comparison_logs)


def test_cli_directory_mode_missing_result_file():
    tmp_results_path = TEST_DATA_PATH.resolve().parent / Path("cli_dir_test_results_data")
    rmtree(tmp_results_path, ignore_errors=True)
    copytree(TEST_DATA_PATH, tmp_results_path, dirs_exist_ok=True)
    assert main(["dir", str(tmp_results_path), str(TEST_DATA_PATH)]) == 0

    # remove one file from temporary results directory
    for first_vtu_file in filter(
        lambda f: isfile(join(tmp_results_path, f)) and splitext(f)[1] == ".vtu",
        listdir(tmp_results_path)
    ):
        remove(join(tmp_results_path, first_vtu_file))
        break

    assert main([
        "dir",
        str(tmp_results_path),
        str(TEST_DATA_PATH)
    ]) == 1
    assert main([
        "dir",
        str(tmp_results_path),
        str(TEST_DATA_PATH),
        "--ignore-missing-reference-files"
    ]) == 1
    assert main([
        "dir",
        str(tmp_results_path),
        str(TEST_DATA_PATH),
        "--ignore-missing-source-files"
    ]) == 0

    rmtree(tmp_results_path)


def test_cli_directory_mode_reader_selection():
    tmp_results_path = TEST_DATA_PATH.resolve().parent / Path("test_cli_directory_mode_reader_selection")
    rmtree(tmp_results_path, ignore_errors=True)
    makedirs(tmp_results_path)
    copy(TEST_DATA_PATH / Path("test_tabular_data.csv"), tmp_results_path / Path("table.dat"))
    assert main(["dir", str(tmp_results_path), str(tmp_results_path)]) == 1
    assert main(["dir", str(tmp_results_path), str(tmp_results_path), "--read-as", "dsv:*.dat"]) == 0
    rmtree(tmp_results_path)


def test_cli_directory_mode_default_reader_selection():
    tmp_results_path = TEST_DATA_PATH.resolve().parent / Path("test_cli_directory_mode_reader_selection")
    rmtree(tmp_results_path, ignore_errors=True)
    makedirs(tmp_results_path)
    copy(TEST_DATA_PATH / Path("test_tabular_data.csv"), tmp_results_path / Path("table.dat"))
    assert main(["dir", str(tmp_results_path), str(tmp_results_path)]) == 1
    assert main(["dir", str(tmp_results_path), str(tmp_results_path), "--read-as", "dsv"]) == 0
    rmtree(tmp_results_path)

    # this should then try to read meshes as dsv files causing the run to fail
    assert main(["dir", str(TEST_DATA_PATH), str(TEST_DATA_PATH), "--read-as", "dsv"]) == 1


def test_cli_directory_mode_missing_reference_file():
    tmp_reference_path = TEST_DATA_PATH.resolve().parent / Path("cli_dir_test_ref_data")
    rmtree(tmp_reference_path, ignore_errors=True)
    copytree(TEST_DATA_PATH, tmp_reference_path, dirs_exist_ok=True)
    assert main(["dir", str(TEST_DATA_PATH), str(tmp_reference_path)]) == 0

    # remove one file from temporary reference path
    for first_vtu_file in filter(
        lambda f: isfile(join(tmp_reference_path, f)) and splitext(f)[1] == ".vtu",
        listdir(tmp_reference_path)
    ):
        remove(join(tmp_reference_path, first_vtu_file))
        break

    assert main([
        "dir",
        str(TEST_DATA_PATH),
        str(tmp_reference_path)
    ]) == 1
    assert main([
        "dir",
        str(TEST_DATA_PATH),
        str(tmp_reference_path),
        "--ignore-missing-source-files"
    ]) == 1
    assert main([
        "dir",
        str(TEST_DATA_PATH),
        str(tmp_reference_path),
        "--ignore-missing-reference-files"
    ]) == 0

    rmtree(tmp_reference_path)


def test_cli_directory_mode_file_inclusion_filter():
    # check that the normal run has xdmf in the output
    with StringIO() as stream:
        logger = CLILogger(output_stream=stream)
        main(["dir", str(TEST_DATA_PATH), str(TEST_DATA_PATH)], logger)
        assert ".xdmf" in stream.getvalue()
    # check that the normal run has xdmf in the output with verbosity=1 (which should remove filter output)
    with StringIO() as stream:
        logger = CLILogger(output_stream=stream)
        main([
            "dir",
            str(TEST_DATA_PATH),
            str(TEST_DATA_PATH),
            "--verbosity=1"], logger)
        assert ".xdmf" in stream.getvalue()
    # check that xdmf disappears with a given pattern
    with StringIO() as stream:
        logger = CLILogger(output_stream=stream)
        main([
            "dir",
            str(TEST_DATA_PATH),
            str(TEST_DATA_PATH),
            "--include-files",
            "*.vtu",
            "--verbosity=1"], logger)
        assert ".xdmf" not in stream.getvalue()
    # check that pattern matches ONLY vtu files
    with StringIO() as stream:
        logger = CLILogger(output_stream=stream)
        main([
            "dir",
            str(TEST_DATA_PATH),
            str(TEST_DATA_PATH),
            "--include-files",
            "*.pvtu",
            "--verbosity=1"], logger)
        assert ".vtu" not in stream.getvalue()


def test_cli_directory_mode_relative_tolerance_definition():
    _mesh = _make_test_mesh()
    _perturbed_mesh = _make_test_mesh()

    _rel_perturbation = 1e-3
    _func_values = _perturbed_mesh.point_data["function"]
    print(_func_values)
    _func_values[0] += _func_values[0]*_rel_perturbation
    _perturbed_mesh.point_data["function"] = _func_values

    res_dir = "test_cli_dir_mode_abs_tolerance_results"
    ref_dir = "test_cli_dir_mode_abs_tolerance_references"
    makedirs(res_dir, exist_ok=True)
    makedirs(ref_dir, exist_ok=True)

    _mesh_filename = "_test_mesh_cli_file_mode_default_rel_tol.vtu"
    _mesh.write(join(res_dir, _mesh_filename))
    _perturbed_mesh.write(join(ref_dir, _mesh_filename))
    assert main([
        "dir",
        res_dir,
        ref_dir,
        "--absolute-tolerance", "0",
    ]) == 1
    assert main([
        "dir",
        res_dir,
        ref_dir,
        "--absolute-tolerance", "0",
        "--relative-tolerance", f"wrong_field:{str(_rel_perturbation*2.0)}"
    ]) == 1
    assert main([
        "dir",
        res_dir,
        ref_dir,
        "--relative-tolerance", "0",
        "--relative-tolerance", f"function:{str(_rel_perturbation*2.0)}"
    ]) == 0
    assert main([
        "dir",
        res_dir,
        ref_dir,
        "--absolute-tolerance", "0",
        "--relative-tolerance", str(_rel_perturbation*2.0)
    ]) == 0

    rmtree(res_dir)
    rmtree(ref_dir)


def test_cli_directory_mode_absolute_tolerance_definition():
    _mesh = _make_test_mesh()
    _perturbed_mesh = _make_test_mesh()

    _abs_perturbation = 1e-3
    _func_values = _perturbed_mesh.point_data["function"]
    print(_func_values)
    _func_values[0] += _abs_perturbation
    _perturbed_mesh.point_data["function"] = _func_values

    res_dir = "test_cli_dir_mode_abs_tolerance_results"
    ref_dir = "test_cli_dir_mode_abs_tolerance_references"
    makedirs(res_dir, exist_ok=True)
    makedirs(ref_dir, exist_ok=True)

    _mesh_filename = "_test_mesh_cli_file_mode_default_rel_tol.vtu"
    _mesh.write(join(res_dir, _mesh_filename))
    _perturbed_mesh.write(join(ref_dir, _mesh_filename))
    assert main([
        "dir",
        res_dir,
        ref_dir,
        "--relative-tolerance", "0",
    ]) == 1
    assert main([
        "dir",
        res_dir,
        ref_dir,
        "--relative-tolerance", "0",
        "--absolute-tolerance", f"wrong_field:{str(_abs_perturbation*2.0)}"
    ]) == 1
    assert main([
        "dir",
        res_dir,
        ref_dir,
        "--relative-tolerance", "0",
        "--absolute-tolerance", f"function:{str(_abs_perturbation*2.0)}"
    ]) == 0
    assert main([
        "dir",
        res_dir,
        ref_dir,
        "--relative-tolerance", "0",
        "--absolute-tolerance", str(_abs_perturbation*2.0)
    ]) == 0

    rmtree(res_dir)
    rmtree(ref_dir)
