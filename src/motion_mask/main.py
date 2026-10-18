import sys

from motion_mask.app import App
from motion_mask.app_cli import CliOptionsParser
from motion_mask.constants import PathsToFiles
from motion_mask.utility import create_path

from motion_mask import loggers

from motion_mask.files_io import FileStorage
from motion_mask.launch_settings import (LaunchSettings,
                                         create_launch_settings)
from motion_mask.launcher import Launcher

logger = loggers.LoggerFactory.get_logger(name=__name__)


def run():
    op = CliOptionsParser()
    parsed_settings = op.parse_settings()

    for n, s in parsed_settings.items():
        if s == '':
            logger.info(f'No value for argument: {n}')
            run_launcher_and_app()
            return

    run_cli_app(parsed_settings=parsed_settings)
    return


def run_cli_app(parsed_settings):
    launch_settings: LaunchSettings = create_launch_settings()

    launch_settings.sync_with_sources()
    launch_settings.apply_settings(settings=parsed_settings)

    app = App(launch_settings=launch_settings)
    app.launch()


def run_launcher_and_app():
    path_to_saved_launch_settings = create_path(
        path_as_str=PathsToFiles.launch_settings)

    storage = FileStorage(filepath=path_to_saved_launch_settings)

    if not path_to_saved_launch_settings.exists():
        launch_settings = create_launch_settings()
    else:
        settings_as_text = storage.load()
        launch_settings = LaunchSettings.from_json(text=settings_as_text)

    launch_settings.sync_with_sources()

    launcher = Launcher(launch_settings=launch_settings)
    launcher.run()

    settings_after_launcher = launcher.get_updated_launch_settings()
    storage.save(text=settings_after_launcher.to_json())

    app = App(launch_settings=settings_after_launcher)
    app.launch()


if __name__ == '__main__':
    run()
