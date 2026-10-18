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
