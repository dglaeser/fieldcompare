"""Test logging facilities"""

from io import StringIO
from contextlib import redirect_stdout

from context import fieldcompare
from fieldcompare.logging import StreamLogger, StandardOutputLogger
from fieldcompare.logging import ModifiedVerbosityLoggerFacade, IndentedLoggingFacade

def test_stdout_logger():
    with StringIO() as stream:
        with redirect_stdout(stream):
            assert "hello" not in stream.getvalue()
            logger = StandardOutputLogger()
            logger.log("hello")
            assert "hello" in stream.getvalue()

def test_stream_logger():
    with StringIO() as stream:
        assert "hello" not in stream.getvalue()
        logger = StreamLogger(stream)
        logger.log("hello")
        assert "hello" in stream.getvalue()

def test_modified_verbosity_logger():
    with StringIO() as stream:
        assert "hello" not in stream.getvalue()
        logger = StreamLogger(stream, verbosity_level=1)
        mod_logger = ModifiedVerbosityLoggerFacade(logger, verbosity_change=-1)
        mod_logger.log("donotprint", verbosity_level=1)
        assert "donotprint" not in stream.getvalue()

def test_indented_logger():
    with StringIO() as stream:
        logger = StreamLogger(stream, verbosity_level=1)
        mod_logger = IndentedLoggingFacade(logger, first_line_prefix=" --")
        mod_logger.log("hello", verbosity_level=1)
        assert " --hello" in stream.getvalue()


if __name__ == "__main__":
    test_stdout_logger()
    test_stream_logger()
    test_modified_verbosity_logger()
    test_indented_logger()
