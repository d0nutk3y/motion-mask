import argparse
import enum

import monitoring
import loggers
from avatar import AvatarException
from virtual_camera import NoneVirtualCamera, DefaultVirtualCamera

logger = loggers.LoggerFactory.get_logger(name=__name__)


class AppMode(enum.StrEnum):
    SETUP = 'setup'
    PREVIEW = 'preview'
    LIVE = 'live'


class DeviceType(enum.StrEnum):
    # pyvirtualcam device type
    v4l2loopback = 'v4l2loopback'
    obs = 'obs'
    unitycapture = 'unitycapture'


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
            choices=devices_as_str,
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
                      model_path: str,
                      device: str,
                      avatar_dir_path: str,
                      ):

        if mode == AppMode.SETUP:
            from calibration_engine import CalibrationEngine
            engine = CalibrationEngine(model_path=model_path)
        elif mode == AppMode.PREVIEW:
            from avatar_engine import AvatarEngine
            engine = AvatarEngine(model_path=model_path,
                                  avatar_path=avatar_dir_path,
                                  preview_mode=True,
                                  virtual_camera=NoneVirtualCamera())
        elif mode == AppMode.LIVE:
            virtual_camera = DefaultVirtualCamera(device=device)

            from avatar_engine import AvatarEngine
            engine = AvatarEngine(model_path=model_path,
                                  avatar_path=avatar_dir_path,
                                  preview_mode=False,
                                  virtual_camera=virtual_camera)

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

        args = self.parse_args()

        mode = AppMode(args.mode)
        device = DeviceType(args.device)
        avatar_dir_path = args.avatar

        model_path = './landmarkers/face_landmarker.task'

        logger.debug(f'args: {model_path}')
        logger.debug(f'mode: {mode}')
        logger.debug(f'device: {device}')
        logger.debug(f'avatar: {avatar_dir_path}')

        try:
            self.start_monitoring(mode=mode)

            engine = self.create_engine(mode=mode,
                                        device=device,
                                        avatar_dir_path=avatar_dir_path,
                                        model_path=model_path)

            engine.launch()
            exit(0)
        except AvatarException as e:
            logger.error(f'Avatar error: {e}')
            exit(1)


if __name__ == '__main__':
    app = App()
    app.main()
