import json
import pathlib
import sys
from pathlib import Path

import cv2

from motion_mask import loggers
from motion_mask import monitoring
from motion_mask.app_cli import (
    CliMode,
    CliOptionsParser)
from motion_mask.avatar import AvatarException
from motion_mask.camera import (
    CameraInfo,
    CamerasInfoStorage,
    VirtualCamerasInfoStorage)
from motion_mask.capture import CaptureWrap
from motion_mask.constants import (
    AppMode,
    CameraDevice,
    PathsToFiles,
    VirtualCameraDevice)
from motion_mask.files_io import FileStorage
from motion_mask.launch_settings import (
    Choice,
    ChoicesSource,
    DictSettingsSource,
    LaunchSettings,
    Option, SettingName)
from motion_mask.tui import LaunchResult, Tui
from motion_mask.utility import create_path
from motion_mask.virtual_camera import (
    DefaultVirtualCamera,
    NoneVirtualCamera)

logger = loggers.LoggerFactory.get_logger(name=__name__)


class AppException(Exception):
    pass


class AppPaths:
    def __init__(self):
        self.model_path = create_path(
            path_as_str=PathsToFiles.model,
        )

        self.avatar_settings_path = create_path(
            path_as_str=PathsToFiles.avatar_settings,
        )

        self.avatars_dir_path = create_path(
            path_as_str=PathsToFiles.avatars_dir,
        )


class App:
    MONITORING_START_POLICY: dict[AppMode, bool] = {
        AppMode.calibration: False,
        AppMode.preview: True,
        AppMode.live: False
    }

    def __init__(self, launch_settings: LaunchSettings, app_paths: AppPaths):
        self.launch_settings = launch_settings
        self.paths: AppPaths = app_paths

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

        logger.debug(f'camera ref: {camera_ref}')
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
        getter = self.launch_settings.get_current_choice

        mode, _ = getter(name=SettingName.mode)
        mode = AppMode(mode)

        camera, _ = getter(name=SettingName.camera)
        virtual_camera, _ = getter(name=SettingName.virtual_camera)
        avatar_name, _ = getter(name=SettingName.avatar_name)

        avatar_path = self.paths.avatars_dir_path.joinpath(avatar_name)
        model_path = self.paths.model_path
        avatar_settings_path = self.paths.avatar_settings_path

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


class Runner:
    def __init__(self):
        self.paths = AppPaths()

        path_to_saved_launch_settings = create_path(
            path_as_str=PathsToFiles.launch_settings)

        self.launch_settings_storage: FileStorage = FileStorage(
            filepath=path_to_saved_launch_settings)

        self.lsf = LaunchSettingsFactory()

    @staticmethod
    def _is_settings_full(settings: dict[SettingName, str]) -> bool:
        if not settings:
            return False
        for n, s in settings.items():
            if s == '':
                logger.info(f'No value for argument: {n}')
                return False
        return True

    def fill_launch_settings(self, parsed_settings):
        is_parsed_settings_full = self._is_settings_full(settings=parsed_settings)

        if is_parsed_settings_full:
            launch_settings = self.lsf.create_launch_settings()
            launch_settings.sync_with_settings_source(
                settings_source=DictSettingsSource(
                    settings_dict=parsed_settings
                )
            )
            return launch_settings

        is_launch_settings_exist = self.launch_settings_storage.exists()
        if is_launch_settings_exist:
            json_text = self.launch_settings_storage.load()
            from_json_settings = json.loads(json_text)

            launch_settings = self.lsf.create_launch_settings()
            launch_settings.sync_with_settings_source(
                settings_source=DictSettingsSource(
                    settings_dict=from_json_settings
                )
            )

            return launch_settings

        default_launch_settings = self.lsf.create_default_launch_settings()
        return default_launch_settings

    def run(self):
        op = CliOptionsParser()
        cli_mode, parsed_settings = op.parse_settings()

        launch_settings = self.fill_launch_settings(
            parsed_settings=parsed_settings)

        if cli_mode is CliMode.cli_start:
            self._run_app(launch_settings=launch_settings)
        elif cli_mode is CliMode.cli_setup:
            self._run_setup(launch_settings=launch_settings)

    def _run_app(self, launch_settings: LaunchSettings):
        logger.debug('starting app...')

        app = App(launch_settings=launch_settings,
                  app_paths=self.paths)
        app.launch()

    def _run_setup(self, launch_settings: LaunchSettings):
        logger.debug('starting setup...')

        logger.debug(f'before: {launch_settings.to_dict()}')


        launcher = Tui(launch_settings=launch_settings)
        launch_result = launcher.launch()
        logger.debug(f'tui exit status: {launch_result}')


        if launch_result == LaunchResult.save:
            settings_after_launcher = launcher.get_updated_launch_settings()

            logger.debug(f'after: {settings_after_launcher.to_dict()}')

            json_text = json.dumps(
                settings_after_launcher.to_dict(),
                indent=2,
            )

            self.launch_settings_storage.save(text=json_text)

        sys.exit(0)


class ModeChoicesSource(ChoicesSource):
    _DEFAULT_MODES = [mode.value for mode in AppMode]

    def get_choices(self) -> list[Choice]:
        return [Choice(value=str(x), label=str(x)) for x in self._DEFAULT_MODES]


class CameraChoicesSource(ChoicesSource):
    def __init__(self, camera_info_storage: CamerasInfoStorage):
        self.camera_info_storage = camera_info_storage

    def get_choices(self) -> list[Choice]:
        self.camera_info_storage.update()
        camera_infos = self.camera_info_storage.camera_infos

        return [Choice(value=x.index, label=f'{x.index}: {x.name} {x.path}')
                for x in camera_infos]


class VirtualCameraChoicesSource(ChoicesSource):
    def __init__(self):
        vcis = VirtualCamerasInfoStorage()
        self.mapping = vcis.get_mapping()

        self.choices = [
            Choice(label=f'{backend}: {device}', value=setting)
            for setting, (backend, device)
            in self.mapping.items()
        ]

    def get_choices(self) -> list[Choice]:
        return self.choices


class AvatarPathChoicesSource(ChoicesSource):
    def __init__(self, path_to_avatar_dir):
        self.path_to_avatar_dir = path_to_avatar_dir

        logger.debug(f'CWD: {pathlib.Path.cwd()}')
        logger.debug(f'Absolute path: {self.path_to_avatar_dir.resolve()}')

    def get_choices(self) -> list[Choice]:
        avatars_paths_choices: list[Choice] = list()
        path = self.path_to_avatar_dir

        for child in path.glob(pattern='*'):
            if child.is_dir():
                logger.debug(f'Found avatar dir: {child.absolute()}')
                choice = Choice(
                    value=child.name,
                    label=child.name)
                avatars_paths_choices.append(choice)

        return avatars_paths_choices


class LaunchSettingsFactory:
    DEFAULT_SETTINGS_DICT = {
        SettingName.mode: AppMode.preview,
        SettingName.camera: CameraDevice.video0,
        SettingName.virtual_camera: VirtualCameraDevice.video9,
        SettingName.avatar_name: 'kanisan',
    }

    def __init__(self, paths: AppPaths | None = None):

        if paths is None:
            self.paths = AppPaths()
        else:
            self.paths = paths

    def sync_with_default_settings(self, launch_settings: LaunchSettings):
        launch_settings.sync_with_settings_source(
            settings_source=DictSettingsSource(
                settings_dict=self.DEFAULT_SETTINGS_DICT
            )
        )

    def create_launch_settings(self) -> LaunchSettings:
        options_choices_sources = [
            (SettingName.mode, ModeChoicesSource()),
            (SettingName.camera, CameraChoicesSource(
                camera_info_storage=CamerasInfoStorage())),
            (SettingName.virtual_camera, VirtualCameraChoicesSource()),
            (SettingName.avatar_name, AvatarPathChoicesSource(
                path_to_avatar_dir=self.paths.avatars_dir_path)),
        ]

        ld = LaunchSettings()

        for name, choices_source in options_choices_sources:
            option = Option(name=name)
            option.sync_with_sources(choices_source=choices_source)
            ld.add_option(option)

        return ld

    def create_default_launch_settings(self):
        ls = self.create_launch_settings()
        self.sync_with_default_settings(launch_settings=ls)

        return ls


def run():
    runner = Runner()
    runner.run()


if __name__ == '__main__':
    run()
