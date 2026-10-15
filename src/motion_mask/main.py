import argparse
import sys

from pathlib import Path

import cv2

from motion_mask import monitoring
from motion_mask import loggers

from motion_mask.avatar import AvatarException
from motion_mask.capture import CaptureWrap
from motion_mask.constants import AppMode, VirtualCamera
from motion_mask.launch_settings import (LaunchSettings,
                                         SettingName,
                                         create_default_launch_settings, CameraInfo)

from motion_mask.virtual_camera import NoneVirtualCamera, DefaultVirtualCamera

logger = loggers.LoggerFactory.get_logger(name=__name__)


class AppException(Exception):
    pass


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


def create_path(path_as_str: str) -> Path:
    if getattr(sys, 'frozen', False):
        # Nuitka устанавливает sys.frozen = True в собранном виде
        base = Path(sys.executable).parent
    else:
        # Режим разработки: ресурсы внутри пакета
        base = Path(__file__).parent

    path = base.joinpath(path_as_str)
    return path


class CliOptionsParser:
    @staticmethod
    def parse_args() -> argparse.Namespace:
        parser = argparse.ArgumentParser(
            description='motion-mask',
            formatter_class=CustomHelpFormatter)

        modes_as_str = [str(mode) for mode in AppMode]

        parser.add_argument(
            '--mode',
            type=str,
            required=True,
            metavar='MODE',
            help=f'application mode: {', '.join(modes_as_str)}'
        )

        parser.add_argument(
            '--camera',
            type=str,
            required=False,
            metavar='CAMERA',
            help=f'camera device: /dev/video0, /dev/video1, Insta360 Link',
            default=VirtualCamera.v4l2loopback,
        )

        devices_as_str = [str(device) for device in VirtualCamera]
        parser.add_argument(
            '--virtual-camera',
            type=str,
            required=False,
            metavar='VIRTUAL_CAMERA',
            help=f'virtual camera device: {', '.join(devices_as_str)}',
            default=VirtualCamera.v4l2loopback,
        )

        parser.add_argument(
            '--avatar-name',
            type=str,
            required=False,
            metavar='AVATAR_NAME',
            help=f'name of avatar dir in ./avatars',
            default='kanisan',
        )

        args = parser.parse_args()

        return args

    def parse_settings(self) -> dict[SettingName, str]:
        args = self.parse_args()

        mode = AppMode(args.mode)
        camera = args.camera
        virtual_camera = args.virtual_camera

        avatar_name = args.avatar_name

        logger.debug(f'cli parsed: mode: {mode}')
        logger.debug(f'cli parsed: camera: {camera}')
        logger.debug(f'cli parsed: virtual camera: {virtual_camera}')
        logger.debug(f'cli parsed: avatar name: {avatar_name}')

        return {
            SettingName.mode: mode,
            SettingName.camera: camera,
            SettingName.virtual_camera: virtual_camera,
            SettingName.avatar_name: avatar_name,
        }


class App:
    MONITORING_START_POLICY: dict[AppMode, bool] = {
        AppMode.SETUP: False,
        AppMode.PREVIEW: True,
        AppMode.LIVE: False
    }

    def __init__(self, launch_settings: LaunchSettings):
        self.launch_settings = launch_settings

        self.memory_monitor = monitoring.MemoryMonitor(
            idle_seconds=3.0,
            launch_delay=15.0
        )

        self.cap_width = 640
        self.cap_height = 360

    def is_camera_working(self,
                          camera_info: CameraInfo,
                          max_attempts: int = 3) -> bool:

        cap = cv2.VideoCapture(camera_info.index, camera_info.backend)

        try:
            if not cap.isOpened():
                logger.debug(
                    f"Camera '{camera_info.name}' (index={camera_info.index}, "
                    f"path={camera_info.path}) failed to open"
                )
                return False

            # Пытаемся прочитать кадр несколько раз —
            # первое чтение может вернуть False даже для рабочей камеры
            for attempt in range(max_attempts):
                ret, frame = cap.read()
                if ret and frame is not None and frame.size > 0:
                    logger.debug(
                        f"Camera '{camera_info.name}' (index={camera_info.index}) "
                        f"is working. Frame shape: {frame.shape}"
                    )
                    return True

            logger.debug(
                f"Camera '{camera_info.name}' (index={camera_info.index}) "
                f"opened but returned no frames after {max_attempts} attempts"
            )
            return False

        except Exception as e:
            logger.warning(
                f"Camera '{camera_info.name}' (index={camera_info.index}) "
                f"raised exception during check: {e}"
            )
            return False

        finally:
            cap.release()

    def test_cameras(self, cameras_infos: list[CameraInfo]) -> CameraInfo | None:
        camera_info = None
        for ci in cameras_infos:
            logger.info(f'Trying camera: {ci.get_info()}')

            if self.is_camera_working(camera_info=ci):
                camera_info = ci
                break

        return camera_info

    def create_engine(
            self,
            mode: AppMode,
            model_path: Path,
            camera_ref: str,
            virtual_camera_ref: str,
            avatar_dir_path: Path,
            settings_path: Path,
    ):
        cis = self.launch_settings.camera_info_storage

        cameras_infos = cis.get_camera_info(ref=camera_ref)

        camera_info = self.test_cameras(cameras_infos=cameras_infos)
        if camera_info is None:
            raise AppException('No camera passed tests')

        camera = CaptureWrap(camera_index=camera_info.index,
                             camera_backend=camera_info.backend,
                             width=self.cap_width,
                             height=self.cap_height)

        if mode == AppMode.SETUP:
            from motion_mask.calibration_engine import CalibrationEngine

            engine = CalibrationEngine(
                model_path=model_path,
                avatar_settings_path=settings_path,
                camera=camera,
            )

        elif mode == AppMode.PREVIEW:
            from motion_mask.avatar_engine import AvatarEngine

            virtual_camera = NoneVirtualCamera()
            engine = AvatarEngine(
                avatar_settings_path=settings_path,
                model_path=model_path,
                avatar_path=avatar_dir_path,
                preview_mode=True,
                camera=camera,
                virtual_camera=virtual_camera,
            )

        elif mode == AppMode.LIVE:
            from motion_mask.avatar_engine import AvatarEngine

            virtual_camera = DefaultVirtualCamera(device=virtual_camera_ref)
            engine = AvatarEngine(
                avatar_settings_path=settings_path,
                model_path=model_path,
                avatar_path=avatar_dir_path,
                preview_mode=False,
                camera=camera,
                virtual_camera=virtual_camera,
            )

        return engine

    def start_monitoring(self, mode: AppMode):
        start_allowed = self.MONITORING_START_POLICY[mode]

        if start_allowed:
            self.memory_monitor.start()

    def launch(self):
        mode = self.launch_settings.get_new_choice(name=SettingName.mode)
        camera = self.launch_settings.get_new_choice(name=SettingName.camera)
        virtual_camera = self.launch_settings.get_new_choice(name=SettingName.virtual_camera)
        avatar_name = self.launch_settings.get_new_choice(name=SettingName.avatar_name)

        avatar_path = create_path(
            path_as_str=f'./avatars/{avatar_name}'
        )

        model_path = create_path(
            path_as_str='landmarkers/face_landmarker.task',
        )

        settings_path = create_path(
            path_as_str='settings/settings.json',
        )

        logger.debug(f'setting: mode: {mode}')
        logger.debug(f'setting: camera: {camera}')
        logger.debug(f'setting: virtual camera: {virtual_camera}')
        logger.debug(f'setting: avatar name: {avatar_name}')
        logger.debug(f'setting: avatar path: {avatar_path}')
        logger.debug(f'setting: model_path: {model_path}')
        logger.debug(f'setting: settings_path: {settings_path}')

        try:
            self.start_monitoring(mode=mode)

            engine = self.create_engine(
                mode=mode,
                camera_ref=camera,
                virtual_camera_ref=virtual_camera,
                avatar_dir_path=avatar_path,
                model_path=model_path,
                settings_path=settings_path,
            )

            engine.launch()
            sys.exit(0)
        except AvatarException as e:
            logger.error(f'Avatar error: {e}')
            sys.exit(1)


def run():
    cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_SILENT)

    op = CliOptionsParser()
    parsed_settings = op.parse_settings()

    launch_settings: LaunchSettings = create_default_launch_settings()

    launch_settings.update_all_options()
    launch_settings.apply_settings(settings=parsed_settings)

    app = App(launch_settings=launch_settings)
    app.launch()


if __name__ == '__main__':
    run()
