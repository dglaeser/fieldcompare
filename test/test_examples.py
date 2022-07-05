"""Test the api examples"""

from os import listdir, chdir, getcwd
from pathlib import Path
from subprocess import run


EXAMPLE_FOLDER = Path(__file__).resolve().parents[1] / Path("examples")

def test_api_examples():
    api_example_folder = EXAMPLE_FOLDER / Path("api")
    cwd = getcwd()
    chdir(str(api_example_folder))

    for _file in listdir(api_example_folder):
        _file = api_example_folder / Path(_file)
        if _file.suffix == ".py":
            print(f"Running example {_file}")
            run(["python3", str(_file)], check=True)

    chdir(cwd)
