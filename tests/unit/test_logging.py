import pytest

from usdb_syncer import logger


def test_logger_exception_exits() -> None:
    logger._SHUTDOWN_ON_ERROR = True
    with pytest.raises(SystemExit):
        logger.logger.exception("Test exception")
    logger._SHUTDOWN_ON_ERROR = False
