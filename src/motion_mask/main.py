from motion_mask import loggers
from motion_mask.app import App
from motion_mask.app_cli import (
    CliMode,
    CliOptionsParser)
from motion_mask.constants import PathsToFiles
from motion_mask.files_io import FileStorage
from motion_mask.launch_settings import (
    LaunchSettings,
    create_launch_settings)
from motion_mask.launcher import Launcher
from motion_mask.utility import create_path

logger = loggers.LoggerFactory.get_logger(name=__name__)


class Runner:
    def __init__(self):
        self.storage: FileStorage | None = None
        self.cli_mode: CliMode | None = None
        self.parsed_settings: dict | None = None

        self.path_to_saved_launch_settings = create_path(
            path_as_str=PathsToFiles.launch_settings)
        self.storage = FileStorage(filepath=self.path_to_saved_launch_settings)

        self.launch_settings: LaunchSettings | None = None

    @classmethod
    def _is_settings_full(cls, settings):
        for n, s in settings.items():
            if s == '':
                logger.info(f'No value for argument: {n}')
                return False
        return True

    def run(self):
        op = CliOptionsParser()
        cli_mode, parsed_settings = op.parse_settings()

        if not self.path_to_saved_launch_settings.exists():
            self.launch_settings = create_launch_settings()
        else:
            settings_as_text = self.storage.load()
            self.launch_settings = LaunchSettings.from_json(text=settings_as_text)

        self.launch_settings.sync_with_sources()

        if cli_mode == CliMode.cli_start:
            if self._is_settings_full(settings=parsed_settings):
                self.launch_settings.apply_settings(settings=parsed_settings)
                self._run_cli_app()
            else:
                self._run_app()
        elif cli_mode == CliMode.cli_setup:
            self._run_launcher()

    def _run_cli_app(self):
        logger.info('starting cli app...')

        app = App(launch_settings=self.launch_settings)
        app.launch()

    def _run_app(self):
        logger.info('starting app...')

        app = App(launch_settings=self.launch_settings)
        app.launch()

    def _run_launcher(self):
        logger.info('starting setup...')

        launcher = Launcher(launch_settings=self.launch_settings)
        launcher.run()

        settings_after_launcher = launcher.get_updated_launch_settings()
        self.storage.save(text=settings_after_launcher.to_json())


def run():
    runner = Runner()
    runner.run()


if __name__ == '__main__':
    run()
