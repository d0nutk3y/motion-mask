import os
import sys
from pathlib import Path


def create_path(path_as_str: str) -> Path:
    if '__compiled__' in globals():
        # Nuitka устанавливает __compiled__ в глобальное пространство имён модуля
        base = Path(sys.executable).parent
    else:
        # Режим разработки: ресурсы внутри пакета
        base = Path(__file__).parent

    path = base.joinpath(path_as_str)
    return path


import os, sys


def suppress_native_stderr():
    """Workaround for disabling C++ mediapipe logs flood to stderr"""
    old_fd = os.dup(2)
    devnull_fd = os.open(os.devnull, os.O_WRONLY)
    os.dup2(devnull_fd, 2)

    def restore():
        os.dup2(old_fd, 2)
        os.close(devnull_fd)
        os.close(old_fd)

    return restore
