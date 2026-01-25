"""Application-wide logging initialization

IMPORTANT: Call `initialize_logging()` in the lambda handler's `__init__.py` file
before any other logging is done.

Logging format:
{
    "timestamp": "2025-12-26T12:00:00.000Z",
    "level": "INFO",
    "logger": "cloudshortener.utils.logging",
    "message": "Application started"
}

TODO:
    - remove this ugly JSON formatting (ditch CloudWatch) and add some sensible logging
"""

import os
import json
import logging
import logging.config
from datetime import datetime, UTC

from cloudshortener.utils.constants import LOG_LEVEL_ENV


class JsonFormatter(logging.Formatter):
    """JSON formatter that includes LogRecord extras"""

    STANDARD_ATTRS = frozenset(
        {
            'args',
            'asctime',
            'created',
            'exc_info',
            'exc_text',
            'filename',
            'funcName',
            'levelname',
            'levelno',
            'lineno',
            'module',
            'msecs',
            'msg',
            'name',
            'pathname',
            'process',
            'processName',
            'relativeCreated',
            'stack_info',
            'thread',
            'threadName',
            'taskName',
        }
    )

    def format(self, record: logging.LogRecord) -> str:
        # fmt: off
        timestamp = datetime.fromtimestamp(record.created, tz=UTC) \
                            .isoformat(timespec="milliseconds") \
                            .replace("+00:00", "Z")
        # fmt: on

        log = {
            'timestamp': timestamp,
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }

        # Attach `extra` fields
        for key, value in record.__dict__.items():
            if key not in self.STANDARD_ATTRS:
                log[key] = value

        return json.dumps(log)


def initialize_logging() -> None:
    log_level = os.getenv(LOG_LEVEL_ENV, 'INFO').upper()
    logging.config.dictConfig(
        {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'json': {
                    '()': JsonFormatter,
                }
            },
            'handlers': {
                'stdout': {
                    'class': 'logging.StreamHandler',
                    'formatter': 'json',
                    'stream': 'ext://sys.stdout',
                }
            },
            'root': {
                'level': log_level,
                'handlers': ['stdout'],
            },
        }
    )
