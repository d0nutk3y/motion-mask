import logging.config
import logging.handlers
from datetime import datetime


class ShortLevelFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created)
        return dt.strftime("%H:%M:%S:%f")[:-2]

    def format(self, record):
        original = record.levelname
        record.levelname = original[:1]
        try:
            return super().format(record)
        finally:
            record.levelname = original


class CustomFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created)
        return dt.strftime("%H:%M:%S:%f")[:-2]


class LoggerFactory:
    LOGGING_CONFIG = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "light": {
                "()": "motion_mask.loggers.ShortLevelFormatter",
                "format": "%(asctime)s | %(levelname)s | %(message)s"},
            "full": {"()": "motion_mask.loggers.CustomFormatter",
                     "format": "%(asctime)s | %(name)s | %(levelname)s | %(message)s"},
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
                "formatter": "light",
                "level": "DEBUG",
            },
        },
        "loggers": {
            "motion_mask": {
                "level": "DEBUG",
                "handlers": ["console"],
                "propagate": False,
            },
        },
        "root": {
            "level": "WARNING",
            "handlers": ["console"],
        },
    }

    @classmethod
    def get_logger(cls, name: str):
        logger = logging.getLogger(name=name)
        return logger


class LoggingStreamSwitcher:
    def __init__(self, initial_config, stream=None):
        self.stream = stream
        self.initial_config = initial_config

    def change_stream(self):
        config = self.initial_config.copy()

        if self.stream is not None:
            config["handlers"]["console"] = {
                "class": "logging.StreamHandler",
                "stream": self.stream,
                "formatter": "light",
                "level": "DEBUG",
            }

        logging.config.dictConfig(config)

    def reset(self):
        logging.config.dictConfig(self.initial_config)
