"""Functionality to deduce the domain type from files"""

from enum import Enum, auto
from dataclasses import dataclass

from ..mesh import is_mesh_file, is_mesh_sequence
from ..tabular import is_tabular_data_file


class DomainType(Enum):
    mesh = auto()
    table = auto()
    unknown = auto()


@dataclass
class FileType:
    domain_type: DomainType
    is_sequence: bool


def deduce_file_type(filename: str) -> FileType:
    domain = _deduce_domain_type(filename)
    return FileType(
        domain_type=domain,
        is_sequence=_is_sequence(filename, domain)
    )


def is_supported_file(filename: str) -> bool:
    return _deduce_domain_type(filename) != DomainType.unknown


def _deduce_domain_type(filename: str) -> DomainType:
    if is_mesh_file(filename):
        return DomainType.mesh
    if is_tabular_data_file(filename):
        return DomainType.table
    return DomainType.unknown


def _is_sequence(filename: str, domain_type: DomainType) -> bool:
    if domain_type == DomainType.mesh:
        return is_mesh_sequence(filename)
    return False
