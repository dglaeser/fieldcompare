"""Test the command-line interface of fieldcompare"""

from pathlib import Path
from context import fieldcompare
from fieldcompare._cli import main

TEST_DATA_PATH = Path(__file__).resolve().parent / Path("data")

def test_cli():
    assert main([
        "file", str(TEST_DATA_PATH / Path("test_mesh.vtu")),
        "--reference", str(TEST_DATA_PATH / Path("test_mesh.vtu"))
    ]) == 0

if __name__ == "__main__":
    test_cli()
