"""Test the command-line interface of fieldcompare"""

from pathlib import Path
from context import fieldcompare
from fieldcompare import _cli

TEST_DATA_PATH = Path(__file__).resolve().parent / Path("data")

def test_cli():
    assert _cli.main([
        str(TEST_DATA_PATH / Path("test_mesh.vtu")),
        str(TEST_DATA_PATH / Path("test_mesh.vtu"))
    ])

if __name__ == "__main__":
    test_cli()
