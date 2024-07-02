from src.config import LOG_DIR

import logging
import os
from datetime import datetime
import pytz
import logfire


def converter(timestamp):
    dt = datetime.fromtimestamp(timestamp, tz=pytz.utc)
    return dt.astimezone(pytz.timezone("US/Eastern")).timetuple()


formatter = logging.Formatter(
    "%(asctime)s - %(name)s:%(levelname)s: %(filename)s:%(lineno)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
formatter.converter = converter


def get_file_handler(log_dir=LOG_DIR, file_prefix: str = ""):
    """
    Returns a file handler for logging.
    """
    os.makedirs(log_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d")
    file_name = f"{file_prefix}_{timestamp}.log"
    file_handler = logging.FileHandler(os.path.join(log_dir, file_name))
    file_handler.setFormatter(formatter)
    return file_handler


def get_console_handler():
    """
    Returns a console handler for logging.
    """
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    return console_handler


testgen_logger = logging.getLogger("testgen_logger")
testgen_logger.setLevel(logging.INFO)
testgen_logger.addHandler(get_file_handler(file_prefix="testgen"))
testgen_logger.addHandler(get_console_handler())

sync_repo = logging.getLogger("sync_repo")
sync_repo.setLevel(logging.INFO)
sync_repo.addHandler(get_file_handler(file_prefix="syncrepo"))
sync_repo.addHandler(get_console_handler())

loggers = [testgen_logger, sync_repo]


def set_log_level(level=logging.INFO):
    """
    Sets the logging level for all defined loggers.
    """
    for logger in loggers:
        logger.setLevel(level)
        for handler in logger.handlers:
            handler.setLevel(level)


def configure_uvicorn_logger():
    uvicorn_error_logger = logging.getLogger("uvicorn.error")
    uvicorn_error_logger.addHandler(get_file_handler())
    uvicorn_error_logger.addHandler(get_console_handler())


# LOGFIRE METRICS
# accepted_count = logfire.metric_counter("accepted_tests", unit="1")
# failed_count = logfire.metric_counter("failed_tests", unit="1")
# total_count = logfire.metric_counter("total_tests", unit="1")
