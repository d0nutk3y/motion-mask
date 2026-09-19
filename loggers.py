import logging.handlers
import sys
from datetime import datetime


class LoggerFactory:
    __app_name = 'motion-mask'
    default_logging_lvl = logging.DEBUG
    stream = sys.stdout

    @classmethod
    def _create_stream_handler(cls, is_light: bool):
        stream_handler = logging.StreamHandler(stream=cls.stream)
        stream_handler.setLevel(cls.default_logging_lvl)

        if is_light:
            format_str = '%(asctime)s | %(message)s'
        else:
            format_str = '%(asctime)s | %(name)s | %(levelname)s | %(message)s'

        stream_formatter = CustomFormatter(format_str)
        stream_handler.setFormatter(stream_formatter)

        return stream_handler

    @classmethod
    def _create_file_handler(cls, logging_level, filename):
        file_handler = logging.handlers.RotatingFileHandler(
            filename=filename,
            mode='w',
            encoding='utf8',
        )
        file_handler.setLevel(logging_level)

        file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(message)s')
        file_handler.setFormatter(file_formatter)

        return file_handler

    @classmethod
    def get_logger(cls,
                   name: str,
                   with_file_handlers=False,
                   is_light=True):
        l = logging.getLogger(name=name)

        l.propagate = False
        l.setLevel(cls.default_logging_lvl)

        l.addHandler(cls._create_stream_handler(is_light=is_light))

        if with_file_handlers:
            debug_file_handler = cls._create_file_handler(
                logging_level=logging.DEBUG,
                filename=f'{cls.__app_name}_debug.log')
            l.addHandler(debug_file_handler)

            info_file_handler = cls._create_file_handler(
                logging_level=logging.INFO,
                filename=f'{cls.__app_name}_info.log')
            l.addHandler(info_file_handler)
        return l

class CustomFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created)
        return dt.strftime("%H:%M:%S:%f")[:-2]