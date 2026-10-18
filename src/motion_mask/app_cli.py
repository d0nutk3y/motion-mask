import argparse
import enum
from typing import Tuple

from motion_mask import loggers
from motion_mask.constants import AppMode, VirtualCamera
from motion_mask.launch_settings import SettingName

logger = loggers.LoggerFactory.get_logger(name=__name__)


class CustomHelpFormatter(argparse.HelpFormatter):
    def _format_action_invocation(self, action):
        if not action.option_strings:
            return super()._format_action_invocation(action)

        if action.nargs == 0:
            return ", ".join(action.option_strings)

        metavar, = self._metavar_formatter(action, action.dest)(1)

        parts = []
        for option in action.option_strings:
            if option.startswith("--"):
                parts.append(f"{option} {metavar}")
            else:
                parts.append(option)

        return ", ".join(parts)


class CliMode(enum.StrEnum):
    cli_setup = 'cli_setup'
    cli_start = 'cli_start'


class CliOptionsParser:
    @staticmethod
    def parse_args() -> argparse.Namespace:
        parser = argparse.ArgumentParser(
            description='motion-mask',
            formatter_class=CustomHelpFormatter)

        modes_as_str = [str(mode) for mode in AppMode]

        parser.add_argument(
            "--setup",
            action="store_true",
            help="launch tui setup",
        )

        parser.add_argument(
            '--mode',
            default='',
            type=str,
            required=False,
            metavar='MODE',
            help=f'application mode: {', '.join(modes_as_str)}'
        )

        parser.add_argument(
            '--camera',
            default='',
            type=str,
            required=False,
            metavar='CAMERA',
            help=f'camera by name/path/index: /dev/video0, /dev/video1, Insta360 Link, 200',
        )

        virtual_cameras_as_str = [str(vc) for vc in VirtualCamera]
        parser.add_argument(
            '--virtual-camera',
            default='',
            type=str,
            required=False,
            metavar='VIRTUAL_CAMERA',
            help=f'virtual camera: {', '.join(virtual_cameras_as_str)}',
        )

        parser.add_argument(
            '--avatar-name',
            default='',
            type=str,
            required=False,
            metavar='AVATAR_NAME',
            help=f'name of avatar: kanisan',
        )

        args = parser.parse_args()

        return args

    def parse_settings(self) -> Tuple[CliMode, dict[SettingName, str]]:
        args = self.parse_args()

        setup_mode = args.setup
        mode = args.mode
        camera = args.camera
        virtual_camera = args.virtual_camera
        avatar_name = args.avatar_name

        logger.debug(f'cli parsed: setup: {setup_mode}')
        logger.debug(f'cli parsed: mode: {mode}')
        logger.debug(f'cli parsed: camera: {camera}')
        logger.debug(f'cli parsed: virtual camera: {virtual_camera}')
        logger.debug(f'cli parsed: avatar name: {avatar_name}')

        parsed = {
            SettingName.mode: mode,
            SettingName.camera: camera,
            SettingName.virtual_camera: virtual_camera,
            SettingName.avatar_name: avatar_name,
        }

        if setup_mode:
            cli_mode = CliMode.cli_setup
        else:
            cli_mode = CliMode.cli_start

        return cli_mode, parsed
