from pathlib import Path

from fieldcompare import FieldDataComparator, FieldDataSequence, protocols
from fieldcompare.mesh import Mesh, MeshFields, cell_types
from fieldcompare.io import read


def get_mesh():
    return Mesh(
        points=[[float(i), 0.0] for i in range(3)],
        connectivity=([(cell_types.line, [[0, 1], [1, 2]])])
    )


def get_field_data(step_idx: int) -> MeshFields:
    return MeshFields(
        mesh=get_mesh(),
        point_data={"pd": [float(step_idx), 2.0*float(step_idx), 3.0*float(step_idx)]},
        cell_data={"cd": [[float(step_idx), 2.0*float(step_idx)]]}
    )


class MockFieldDataSource:
    def __init__(self, num_steps: int = 3) -> None:
        assert num_steps > 0
        self._step_idx = 0
        self._num_steps = num_steps

    def reset(self) -> None:
        self._step_idx = 0

    def step(self) -> bool:
        self._step_idx += 1
        return self._step_idx < self._num_steps

    def get(self) -> protocols.FieldData:
        return get_field_data(self._step_idx)

    @property
    def number_of_steps(self) -> int:
        return self._num_steps


def test_field_data_sequence():
    sequence = FieldDataSequence(source=MockFieldDataSource())
    reference_mesh = get_mesh()
    for step_idx, field_data in enumerate(sequence):
        assert field_data.domain.equals(reference_mesh)
        assert FieldDataComparator(field_data, get_field_data(step_idx))()


def test_xdmf_field_data_sequence():
    xdmf_file = Path(__file__).resolve().parent / Path("data/test_time_series.xdmf")
    sequence = read(str(xdmf_file))
    assert isinstance(sequence, protocols.FieldDataSequence)

    mesh = None
    for field_data in sequence:
        mesh = field_data.domain
        break

    for field_data in sequence:
        assert mesh is not None
        assert mesh.equals(field_data.domain)
        for field in field_data:
            print(f"Field = {field}")
