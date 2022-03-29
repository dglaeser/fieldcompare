"""Test the command-line interface of fieldcompare"""

from os import remove, listdir, makedirs
from os.path import isfile, join, splitext
from shutil import rmtree, copytree
from pathlib import Path
from io import StringIO

from context import fieldcompare
from fieldcompare._cli import main
from fieldcompare.logging import StreamLogger
from data.generate_test_meshes import _make_test_mesh, _perturb_mesh
from data.generate_test_meshes import _get_time_series_point_data_values
from data.generate_test_meshes import _get_time_series_cell_data_values
from data.generate_test_meshes import _write_time_series

TEST_DATA_PATH = Path(__file__).resolve().parent / Path("data")

def test_cli_file_mode_pass():
    assert main([
        "file", str(TEST_DATA_PATH / Path("test_mesh.vtu")),
        "--reference", str(TEST_DATA_PATH / Path("test_mesh.vtu"))
    ]) == 0

def test_cli_file_mode_fail():
    _mesh = _make_test_mesh()
    _perturbed_mesh = _perturb_mesh(_make_test_mesh(), max_perturbation=1e-3)

    _mesh_filename = "_test_mesh_cli_file_mode_fail.vtu"
    _perturbed_mesh_filename = _mesh_filename.replace(".vtu", "_reference.vtu")
    _mesh.write(_mesh_filename)
    _perturbed_mesh.write(_perturbed_mesh_filename)
    assert main(["file", _mesh_filename, "--reference", _perturbed_mesh_filename]) == 1

    remove(_mesh_filename)
    remove(_perturbed_mesh_filename)

def test_cli_file_mode_field_filter():
    with StringIO() as stream:
        logger = StreamLogger(stream)
        args = [
            "file", str(TEST_DATA_PATH / Path("test_mesh.vtu")),
            "--reference", str(TEST_DATA_PATH / Path("test_mesh.vtu")),
            "--include-fields", "function"
        ]
        assert main(args, logger) == 0
        comparison_logs = [
            line for line in stream.getvalue().split("\n") if "Comparison of the fields" in line
        ]
        assert len(comparison_logs) == 1
        assert "function" in comparison_logs[0]

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
        "file", _mesh_filename,
        "--reference", _perturbed_mesh_filename
    ]) == 1
    assert main([
        "file", _mesh_filename,
        "--reference", _perturbed_mesh_filename,
        "--relative-tolerance", f"wrong_field:{str(_rel_perturbation*2.0)}"
    ]) == 1
    assert main([
        "file", _mesh_filename,
        "--reference", _perturbed_mesh_filename,
        "--relative-tolerance", f"function:{str(_rel_perturbation*2.0)}"
    ]) == 0
    assert main([
        "file", _mesh_filename,
        "--reference", _perturbed_mesh_filename,
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
        "file", _mesh_filename,
        "--reference", _perturbed_mesh_filename,
        "--relative-tolerance", "0",
    ]) == 1
    assert main([
        "file", _mesh_filename,
        "--reference", _perturbed_mesh_filename,
        "--relative-tolerance", "0",
        "--absolute-tolerance", f"wrong_field:{str(_abs_perturbation*2.0)}"
    ]) == 1
    assert main([
        "file", _mesh_filename,
        "--reference", _perturbed_mesh_filename,
        "--relative-tolerance", "0",
        "--absolute-tolerance", f"function:{str(_abs_perturbation*2.0)}"
    ]) == 0
    assert main([
        "file", _mesh_filename,
        "--reference", _perturbed_mesh_filename,
        "--relative-tolerance", "0",
        "--absolute-tolerance", str(_abs_perturbation*2.0)
    ]) == 0

    remove(_mesh_filename)
    remove(_perturbed_mesh_filename)

def test_cli_file_mode_missing_result_field():
    _mesh = _make_test_mesh()
    _point_data_1 = _get_time_series_point_data_values(_mesh, num_time_steps=2)
    _cell_data_1 = _get_time_series_cell_data_values(_mesh, num_time_steps=2)
    _point_data_2 = _get_time_series_point_data_values(_mesh, num_time_steps=3)
    _cell_data_2 = _get_time_series_cell_data_values(_mesh, num_time_steps=3)

    _mesh_1_filename = "_test_mesh_cli_file_mode_missing_result_field_1.xdmf"
    _mesh_2_filename = "_test_mesh_cli_file_mode_missing_result_field_2.xdmf"
    _write_time_series(_mesh_1_filename, _mesh, _point_data_1, _cell_data_1, num_time_steps=2)
    _write_time_series(_mesh_2_filename, _mesh, _point_data_2, _cell_data_2, num_time_steps=3)

    assert main(["file", _mesh_1_filename, "--reference", _mesh_2_filename]) == 1
    assert main(["file", _mesh_1_filename, "--reference", _mesh_2_filename, "--ignore-missing-reference-fields"]) == 1
    assert main(["file", _mesh_1_filename, "--reference", _mesh_2_filename, "--ignore-missing-result-fields"]) == 0

    remove(_mesh_1_filename)
    remove(_mesh_2_filename)
    remove(_mesh_1_filename.replace(".xdmf", ".h5"))
    remove(_mesh_2_filename.replace(".xdmf", ".h5"))

def test_cli_file_mode_missing_reference_field():
    _mesh = _make_test_mesh()
    _point_data_1 = _get_time_series_point_data_values(_mesh, num_time_steps=3)
    _cell_data_1 = _get_time_series_cell_data_values(_mesh, num_time_steps=3)
    _point_data_2 = _get_time_series_point_data_values(_mesh, num_time_steps=2)
    _cell_data_2 = _get_time_series_cell_data_values(_mesh, num_time_steps=2)

    _mesh_1_filename = "_test_mesh_cli_file_mode_missing_reference_field_1.xdmf"
    _mesh_2_filename = "_test_mesh_cli_file_mode_missing_reference_field_2.xdmf"
    _write_time_series(_mesh_1_filename, _mesh, _point_data_1, _cell_data_1, num_time_steps=3)
    _write_time_series(_mesh_2_filename, _mesh, _point_data_2, _cell_data_2, num_time_steps=2)

    assert main(["file", _mesh_1_filename, "--reference", _mesh_2_filename]) == 1
    assert main(["file", _mesh_1_filename, "--reference", _mesh_2_filename, "--ignore-missing-reference-fields"]) == 0
    assert main(["file", _mesh_1_filename, "--reference", _mesh_2_filename, "--ignore-missing-result-fields"]) == 1
    remove(_mesh_1_filename)
    remove(_mesh_2_filename)
    remove(_mesh_1_filename.replace(".xdmf", ".h5"))
    remove(_mesh_2_filename.replace(".xdmf", ".h5"))

def test_cli_directory_mode():
    assert main(["dir", str(TEST_DATA_PATH), "--reference-dir", str(TEST_DATA_PATH)]) == 0

def test_cli_folder_mode_field_filter():
    with StringIO() as stream:
        logger = StreamLogger(stream)
        args = [
            "dir", str(TEST_DATA_PATH),
            "--reference-dir", str(TEST_DATA_PATH),
            "--include-fields", "function"
        ]
        assert main(args, logger) == 0
        comparison_logs = [
            line for line in stream.getvalue().split("\n") if "Comparison of the fields" in line
        ]
        assert all("function" in log for log in comparison_logs)

def test_cli_directory_mode_missing_result_file():
    tmp_results_path = TEST_DATA_PATH.resolve().parent / Path("cli_dir_test_results_data")
    copytree(TEST_DATA_PATH, tmp_results_path, dirs_exist_ok=True)
    assert main(["dir", str(tmp_results_path), "--reference-dir", str(TEST_DATA_PATH)]) == 0

    # remove one file from temporary results directory
    for first_vtu_file in filter(
        lambda f: isfile(join(tmp_results_path, f)) and splitext(f)[1] == ".vtu",
        listdir(tmp_results_path)
    ):
        remove(join(tmp_results_path, first_vtu_file))
        break

    assert main([
        "dir", str(tmp_results_path),
        "--reference-dir", str(TEST_DATA_PATH)
    ]) == 1
    assert main([
        "dir", str(tmp_results_path),
        "--reference-dir", str(TEST_DATA_PATH),
        "--ignore-missing-result-files"
    ]) == 0

    rmtree(tmp_results_path)

def test_cli_directory_mode_missing_reference_file():
    tmp_reference_path = TEST_DATA_PATH.resolve().parent / Path("cli_dir_test_ref_data")
    copytree(TEST_DATA_PATH, tmp_reference_path, dirs_exist_ok=True)
    assert main(["dir", str(TEST_DATA_PATH), "--reference-dir", str(tmp_reference_path)]) == 0

    # remove one file from temporary reference path
    for first_vtu_file in filter(
        lambda f: isfile(join(tmp_reference_path, f)) and splitext(f)[1] == ".vtu",
        listdir(tmp_reference_path)
    ):
        remove(join(tmp_reference_path, first_vtu_file))
        break

    assert main([
        "dir", str(TEST_DATA_PATH),
        "--reference-dir", str(tmp_reference_path)
    ]) == 1
    assert main([
        "dir", str(TEST_DATA_PATH),
        "--reference-dir", str(tmp_reference_path),
        "--ignore-missing-reference-files"
    ]) == 0

    rmtree(tmp_reference_path)

def test_cli_directory_mode_file_inclusion_filter():
    # check that the normal run has xdmf in the output
    with StringIO() as stream:
        logger = StreamLogger(stream)
        main(["dir", str(TEST_DATA_PATH), "--reference-dir", str(TEST_DATA_PATH)], logger)
        assert ".xdmf" in stream.getvalue()
    # check that the normal run has xdmf in the output with verbosity=1 (which should remove filter output)
    with StringIO() as stream:
        logger = StreamLogger(stream)
        main([
            "dir", str(TEST_DATA_PATH),
            "--reference-dir", str(TEST_DATA_PATH),
            "--verbosity=1"], logger)
        assert ".xdmf" in stream.getvalue()
    # check that xdmf disappears with regex
    with StringIO() as stream:
        logger = StreamLogger(stream)
        main([
            "dir", str(TEST_DATA_PATH),
            "--reference-dir", str(TEST_DATA_PATH),
            "--include-files",
            "*.vtu",
            "--verbosity=1"], logger)
        assert ".xdmf" not in stream.getvalue()

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
        "dir", res_dir,
        "--reference-dir", ref_dir,
        "--absolute-tolerance", "0",
    ]) == 1
    assert main([
        "dir", res_dir,
        "--reference-dir", ref_dir,
        "--absolute-tolerance", "0",
        "--relative-tolerance", f"wrong_field:{str(_rel_perturbation*2.0)}"
    ]) == 1
    assert main([
        "dir", res_dir,
        "--reference-dir", ref_dir,
        "--relative-tolerance", "0",
        "--relative-tolerance", f"function:{str(_rel_perturbation*2.0)}"
    ]) == 0
    assert main([
        "dir", res_dir,
        "--reference-dir", ref_dir,
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
        "dir", res_dir,
        "--reference-dir", ref_dir,
        "--relative-tolerance", "0",
    ]) == 1
    assert main([
        "dir", res_dir,
        "--reference-dir", ref_dir,
        "--relative-tolerance", "0",
        "--absolute-tolerance", f"wrong_field:{str(_abs_perturbation*2.0)}"
    ]) == 1
    assert main([
        "dir", res_dir,
        "--reference-dir", ref_dir,
        "--relative-tolerance", "0",
        "--absolute-tolerance", f"function:{str(_abs_perturbation*2.0)}"
    ]) == 0
    assert main([
        "dir", res_dir,
        "--reference-dir", ref_dir,
        "--relative-tolerance", "0",
        "--absolute-tolerance", str(_abs_perturbation*2.0)
    ]) == 0

    rmtree(res_dir)
    rmtree(ref_dir)


if __name__ == "__main__":
    test_cli_file_mode_pass()
    test_cli_file_mode_fail()
    test_cli_file_mode_missing_result_field()
    test_cli_file_mode_missing_reference_field()
    test_cli_directory_mode()
    test_cli_directory_mode_missing_result_file()
    test_cli_directory_mode_missing_reference_file()
    test_cli_directory_mode_regex()
