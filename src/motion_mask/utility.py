import sys
from pathlib import Path


def create_path(path_as_str: str) -> Path:
    if getattr(sys, 'frozen', False):
        # Nuitka устанавливает sys.frozen = True в собранном виде
        base = Path(sys.executable).parent
    else:
        # Режим разработки: ресурсы внутри пакета
        base = Path(__file__).parent

    path = base.joinpath(path_as_str)
    return path
