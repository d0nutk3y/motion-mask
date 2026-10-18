import sys
from pathlib import Path

import cv2

from motion_mask import loggers
from motion_mask import monitoring
from motion_mask.avatar import AvatarException
from motion_mask.capture import CaptureWrap
from motion_mask.constants import AppMode, PathsToFiles
from motion_mask.launch_settings import (
    CameraInfo,
    CamerasInfoStorage,
    LaunchSettings,
    SettingName,
    VirtualCamerasInfoStorage)
from motion_mask.utility import create_path
from motion_mask.virtual_camera import DefaultVirtualCamera, NoneVirtualCamera

logger = loggers.LoggerFactory.get_logger(name=__name__)


class AppException(Exception):
    pass


class App:
    MONITORING_START_POLICY: dict[AppMode, bool] = {
        AppMode.calibration: False,
        AppMode.preview: True,
        AppMode.live: False
    }

    def __init__(self, launch_settings: LaunchSettings):
        self.launch_settings = launch_settings

        self.memory_monitor = monitoring.MemoryMonitor(
            idle_seconds=3.0,
            launch_delay=15.0
        )

        self.cap_width = 640
        self.cap_height = 360

    @classmethod
    def is_camera_working(cls,
                          camera_info: CameraInfo,
                          max_attempts: int = 3) -> bool:

        cap = cv2.VideoCapture(camera_info.index, camera_info.backend)

        try:
            if not cap.isOpened():
                logger.debug(
                    f'Camera failed to open: {camera_info.get_info()}'
                )
                return False

            for attempt in range(max_attempts):
                ret, frame = cap.read()
                if ret and frame is not None and frame.size > 0:
                    logger.debug(
                        f'Camera is working: {camera_info.get_info()}'
                    )
                    return True

            logger.debug(
                f'Camera opened but returned no frames: {camera_info.get_info()}'
            )
            return False

        except Exception as e:
            logger.warning(
                f'Camera raised exception during check: {camera_info.get_info()}\n'
                f'Exception {e}'
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
        cis = CamerasInfoStorage()
        cis.update()

        cameras_infos = cis.get_camera_info(ref=camera_ref)

        camera_info = self.test_cameras(cameras_infos=cameras_infos)
        if camera_info is None:
            raise AppException('No camera passed tests')

        camera = CaptureWrap(camera_index=camera_info.index,
                             camera_backend=camera_info.backend,
                             width=self.cap_width,
                             height=self.cap_height)

        if mode == AppMode.calibration:
            from motion_mask.calibration_engine import CalibrationEngine

            engine = CalibrationEngine(
                model_path=model_path,
                avatar_settings_path=settings_path,
                camera=camera,
            )

        elif mode == AppMode.preview:
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

        elif mode == AppMode.live:
            from motion_mask.avatar_engine import AvatarEngine

            vcis = VirtualCamerasInfoStorage()
            backend, device = vcis.get_backend_device_pair(setting=virtual_camera_ref)
            virtual_camera = DefaultVirtualCamera(
                backend=backend,
                device=device)

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
        # Load
        mode = self.launch_settings.get_current_choice_value(name=SettingName.mode)
        camera = self.launch_settings.get_current_choice_value(name=SettingName.camera)
        virtual_camera = self.launch_settings.get_current_choice_value(
            name=SettingName.virtual_camera)
        avatar_name = self.launch_settings.get_current_choice_value(name=SettingName.avatar_name)

        avatar_path = create_path(
            path_as_str=f'./avatars/{avatar_name}'
        )

        model_path = create_path(
            path_as_str=PathsToFiles.model,
        )

        avatar_settings_path = create_path(
            path_as_str=PathsToFiles.avatar_settings,
        )

        logger.debug(f'setting: mode: {mode}')
        logger.debug(f'setting: camera: {camera}')
        logger.debug(f'setting: virtual camera: {virtual_camera}')
        logger.debug(f'setting: avatar name: {avatar_name}')
        logger.debug(f'setting: avatar path: {avatar_path}')
        logger.debug(f'setting: model_path: {model_path}')
        logger.debug(f'setting: avatar_settings_path: {avatar_settings_path}')

        # Create
        try:
            self.start_monitoring(mode=mode)

            engine = self.create_engine(
                mode=mode,
                camera_ref=camera,
                virtual_camera_ref=virtual_camera,
                avatar_dir_path=avatar_path,
                model_path=model_path,
                settings_path=avatar_settings_path,
            )
        except AvatarException as e:
            logger.error(f'Avatar error: {e}')
            sys.exit(1)

        # Launch
        try:
            engine.launch()
            sys.exit(0)
        except AppException as e:
            logger.error(f'Avatar error: {e}')
            sys.exit(1)
