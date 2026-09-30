import argparse
import enum

from importlib.resources import files, as_file
from pathlib import Path

from motion_mask import monitoring
from motion_mask import loggers

from motion_mask.avatar import AvatarException
from motion_mask.virtual_camera import NoneVirtualCamera, DefaultVirtualCamera

logger = loggers.LoggerFactory.get_logger(name=__name__)


def check():
    # Dependencies check
    try:
        import pyvirtualcam
        import mediapipe as mp

        print('[OK] pyvirtualcam version:', pyvirtualcam.__version__)
        print('[OK] mediapipe version:', mp.__version__)
    except Exception as e:
        print('[FAILED] some dependencies import failed')
        print(f'Exception: {e}')

    # Virtual camera check
    try:
        with pyvirtualcam.Camera(width=1280, height=720, fps=10) as cam:
            print('[OK] virtual cam is avaliable')
    except Exception as e:
        print('[FAILED] failed to use virtual camera')
        print(f'Exception: {e}')


class AppMode(enum.StrEnum):
    SETUP = 'setup'
    PREVIEW = 'preview'
    LIVE = 'live'


class DeviceType(enum.StrEnum):
    # pyvirtualcam device type
    v4l2loopback = 'v4l2loopback'
    obs = 'obs'
    unitycapture = 'unitycapture'


def create_path(package_name: str, path_as_str: str) -> Path:
    resource = files(package_name).joinpath(path_as_str)
    with as_file(resource) as path:
        return path


class App:
    def __init__(self):
        self.memory_monitor = monitoring.MemoryMonitor(
            idle_seconds=3.0,
            launch_delay=15.0
        )

    @staticmethod
    def parse_args() -> argparse.Namespace:
        parser = argparse.ArgumentParser(
            description='Motion mask',
            formatter_class=argparse.RawDescriptionHelpFormatter)

        modes_as_str = [str(mode) for mode in AppMode]

        parser.add_argument(
            '-m', '--mode',
            type=str,
            required=True,
            choices=modes_as_str,
            help=f'application mode: {", ".join(modes_as_str)}'
        )

        devices_as_str = [str(device) for device in DeviceType]
        parser.add_argument(
            '-d', '--device',
            type=str,
            required=False,
            help=f'virtual camera device: {", ".join(devices_as_str)}',
            default=DeviceType.v4l2loopback,
        )

        parser.add_argument(
            '-a', '--avatar',
            type=str,
            required=False,
            metavar='path_to_avatar',
            help=f'path to avatar directory',
            default='./avatars/kanisan',
        )

        args = parser.parse_args()

        return args

    @staticmethod
    def create_engine(mode: AppMode,
                      model_path: Path,
                      device: str,
                      avatar_dir_path: Path,
                      settings_path: Path,
                      ):

        if mode == AppMode.SETUP:
            from motion_mask.calibration_engine import CalibrationEngine
            engine = CalibrationEngine(
                model_path=model_path,
                settings_path=settings_path,
            )
        elif mode == AppMode.PREVIEW:
            from motion_mask.avatar_engine import AvatarEngine
            engine = AvatarEngine(model_path=model_path,
                                  avatar_path=avatar_dir_path,
                                  preview_mode=True,
                                  virtual_camera=NoneVirtualCamera(),
                                  settings_path=settings_path,
                                  )
        elif mode == AppMode.LIVE:
            from motion_mask.avatar_engine import AvatarEngine



            virtual_camera = DefaultVirtualCamera(device=device)
            engine = AvatarEngine(model_path=model_path,
                                  avatar_path=avatar_dir_path,
                                  preview_mode=False,
                                  virtual_camera=virtual_camera,
                                  settings_path=settings_path,
                                  )

        return engine

    MONITORING_START_POLICY: dict[AppMode, bool] = {
        AppMode.SETUP: False,
        AppMode.PREVIEW: True,
        AppMode.LIVE: False
    }

    def start_monitoring(self, mode: AppMode):
        start_allowed = self.MONITORING_START_POLICY[mode]

        if start_allowed:
            self.memory_monitor.start()

    def main(self):
        package_name = 'motion_mask'

        settings_path = create_path(
            package_name=package_name,
            path_as_str='settings/settings.json',
        )

        model_path = create_path(
            package_name=package_name,
            path_as_str='landmarkers/face_landmarker.task',
        )

        args = self.parse_args()

        mode = AppMode(args.mode)
        device = args.device

        avatar_dir_path = create_path(
            package_name=package_name,
            path_as_str=args.avatar,
        )

        logger.debug(f'settings_path: {settings_path}')
        logger.debug(f'model_path: {model_path}')
        logger.debug(f'mode: {mode}')
        logger.debug(f'device: {device}')
        logger.debug(f'avatar dir: {avatar_dir_path}')

        try:
            self.start_monitoring(mode=mode)

            engine = self.create_engine(mode=mode,
                                        device=device,
                                        avatar_dir_path=avatar_dir_path,
                                        model_path=model_path,
                                        settings_path=settings_path,
                                        )

            engine.launch()
            exit(0)
        except AvatarException as e:
            logger.error(f'Avatar error: {e}')
            exit(1)


def run():
    app = App()
    app.main()


if __name__ == '__main__':
    run()
