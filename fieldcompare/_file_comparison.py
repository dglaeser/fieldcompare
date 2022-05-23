"""Class to perform a comparison of two files"""

from textwrap import indent
from dataclasses import dataclass

from ._field import FieldContainerInterface
from ._field_io import is_mesh_file, make_mesh_field_reader, read_fields
from ._format import as_error
from ._logging import (
    LoggerInterface,
    StandardOutputLogger,
    ModifiedVerbosityLogger,
    IndentedLogger
)

from ._field_comparison import FieldComparison, FieldComparisonOptions


@dataclass
class FileComparisonOptions(FieldComparisonOptions):
    disable_mesh_reordering: bool = False
    disable_mesh_ghost_point_removal: bool = False


class FileComparison:
    """Class to perform a comparison of two files"""
    def __init__(self,
                 options: FileComparisonOptions = FileComparisonOptions(),
                 logger: LoggerInterface = StandardOutputLogger()):
        self._field_comparison = FieldComparison(options, logger)
        self._disable_mesh_reordering = options.disable_mesh_reordering
        self._disable_ghost_point_removal = options.disable_mesh_ghost_point_removal
        self._logger = logger

    def __call__(self, res_file: str, ref_file: str,) -> bool:
        """Check two files for equality of the contained fields"""
        try:
            res_fields = self._read_file(res_file)
            ref_fields = self._read_file(ref_file)
        except Exception as e:
            self._logger.log(f"Error reading fields. Exception:\n{e}\n", verbosity_level=1)
            return False
        return self._field_comparison(res_fields, ref_fields)

    def _read_file(self, filename: str) -> FieldContainerInterface:
        try:
            self._logger.log(f"Reading fields from '{filename}'\n", verbosity_level=1)
            low_verbosity_logger = ModifiedVerbosityLogger(self._logger, verbosity_change=-2)
            file_io_logger = IndentedLogger(low_verbosity_logger, " -- ")
            if is_mesh_file(filename):
                return self._read_mesh_file(filename, file_io_logger)
            return read_fields(filename, logger=file_io_logger)
        except IOError as e:
            raise Exception(_read_error_message(filename, str(e)))

    def _read_mesh_file(self, filename: str, logger: LoggerInterface) -> FieldContainerInterface:
        reader = make_mesh_field_reader(filename)
        reader.attach_logger(logger)
        reader.remove_ghost_points = False if self._disable_ghost_point_removal else True
        reader.permute_uniquely = False if self._disable_mesh_reordering else True
        return reader.read(filename)


def _read_error_message(filename: str, except_str: str) -> str:
    if not except_str.endswith("\n"):
        except_str = f"{except_str}\n"
    return as_error("Error") + f" reading '{filename}':\n" + indent(except_str, " "*4)
