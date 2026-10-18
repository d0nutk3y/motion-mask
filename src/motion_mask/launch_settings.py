import dataclasses
import enum
import json
import pathlib
from pprint import pprint

from cv2_enumerate_cameras import enumerate_cameras

from motion_mask import loggers
from motion_mask.constants import AppMode, CameraDevice, VirtualCameraDevice, VirtualCamera, \
    VirtualCameraBackend

logger = loggers.LoggerFactory.get_logger(name=__name__)


class SettingName(enum.StrEnum):
    mode = 'mode'
    camera = 'camera'
    virtual_camera = 'virtual camera'
    avatar_name = 'avatar name'


class SettingsSource:
    def get_option_value(self):
        raise NotImplementedError()


class DictSettingsSource(SettingsSource):
    def __init__(self,
                 settings_dict: dict[SettingName, str],
                 name: str):
        self.name = name
        self.settings_dict = settings_dict

    def get_option_value(self):
        return self.settings_dict[SettingName(self.name)]


@dataclasses.dataclass
class Choice:
    value: str | int
    label: str


class ChoicesSource:
    def get_choices(self) -> list[Choice]:
        raise NotImplementedError()


class ModeChoicesSource(ChoicesSource):
    _DEFAULT_MODES = [mode.value for mode in AppMode]

    def get_choices(self) -> list[Choice]:
        return [Choice(value=str(x), label=str(x)) for x in self._DEFAULT_MODES]


@dataclasses.dataclass
class CameraInfo:
    path: str
    vid: int
    pid: int
    index: int
    name: str
    backend: int

    def get_info(self):
        return {
            'index': self.index,
            'vid': self.vid,
            'pid': self.pid,
            'name': self.name,
            'path': self.path,
            'backend': self.backend
        }

class VirtualCamerasInfoStorage:
    def __init__(self):
        self.mapping = {
            VirtualCamera.v4l2loopback_video9:
                (VirtualCameraBackend.v4l2loopback, VirtualCameraDevice.video9),
            VirtualCamera.v4l2loopback_video8:
                (VirtualCameraBackend.v4l2loopback, VirtualCameraDevice.video8),
            VirtualCamera.v4l2loopback_video7:
                (VirtualCameraBackend.v4l2loopback, VirtualCameraDevice.video7),
            VirtualCamera.obs:
                (VirtualCameraBackend.obs, VirtualCameraDevice.obs),
            VirtualCamera.unitycapture:
                (VirtualCameraBackend.unity_capture, VirtualCameraDevice.unity_capture),
        }

    def get_mapping(self):
        return self.mapping.copy()

    def get_backend_device_pair(self, setting: str):
        return self.mapping[VirtualCamera(setting)]


class CamerasInfoStorage:
    def __init__(self):
        self._camera_infos: dict[int, CameraInfo] = dict()

    def update(self):
        self._camera_infos = dict()
        for camera_info in enumerate_cameras():
            ci = CameraInfo(
                path=camera_info.path,
                vid=camera_info.vid,
                pid=camera_info.pid,
                index=camera_info.index,
                name=camera_info.name,
                backend=camera_info.backend,
            )

            logger.info(f'Camera detected: {ci.get_info()}')
            self._camera_infos[ci.index] = ci

    @property
    def camera_infos(self) -> list[CameraInfo]:
        return list(self._camera_infos.values())

    def get_by_index(self, index: int) -> list[CameraInfo] | None:
        return [self._camera_infos.get(index)]

    def get_by_path(self, path: str) -> list[CameraInfo] | None:
        result = []
        for ci in self._camera_infos.values():
            if ci.path == path:
                result.append(ci)

        return result

    def get_by_name(self, name_part: str) -> list[CameraInfo] | None:
        result = []

        name_part_lower = name_part.lower()
        for ci in self._camera_infos.values():
            if name_part_lower in ci.name.lower():
                result.append(ci)

        return result

    def get_camera_info(self, ref: str | int) -> list[CameraInfo] | None:
        if isinstance(ref, int):
            return self.get_by_index(ref)

        try:
            index_probably = int(ref)
            return self.get_by_index(index_probably)
        except ValueError:
            pass

        if isinstance(ref, str):
            result = self.get_by_path(ref)
            if result:
                return result

            return self.get_by_name(ref)


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
    def __init__(self):
        self.default_avatars_dir_path = (
            pathlib.Path(__file__)
            .resolve()
            .parent
            .joinpath('avatars')
        )

        logger.debug(f'CWD: {pathlib.Path.cwd()}')
        logger.debug(f'Absolute path: {self.default_avatars_dir_path.resolve()}')

    def get_choices(self) -> list[Choice]:
        avatars_paths_choices: list[Choice] = list()
        path = self.default_avatars_dir_path

        for child in path.glob(pattern='*'):
            if child.is_dir():
                logger.debug(f'Found avatar dir: {child.absolute()}')
                choice = Choice(
                    value=child.name,
                    label=child.name)
                avatars_paths_choices.append(choice)

        return avatars_paths_choices


class Option:
    def __init__(self, name: SettingName,
                 settings_source: SettingsSource,
                 choices_source: ChoicesSource):
        self.name: SettingName = name
        self._available_choices: dict[str, Choice] = {}
        self._current_choice: Choice = Choice(label='xxx', value='')

        self.settings_source = settings_source
        self.choices_source = choices_source

    def is_current_choice_legit(self):
        if not self._current_choice.value in self._available_choices:
            raise ValueError(f'Value {self._current_choice.value} '
                             f'is not in {self._available_choices.values()}')

    def sync_with_sources(self):
        self._available_choices = {c.value: c for c
                                   in self.choices_source.get_choices()}

        available_choices_as_text = ', '.join([str(x) for x in self._available_choices.keys()])
        logger.debug(f'{self.name}: updated available choices: {available_choices_as_text}')

        value = self.settings_source.get_option_value()
        self._current_choice = Choice(value=value, label=value)

        logger.debug(f'Current choice for {self.name}: updated with value: {value}')

    @property
    def available_choices(self):
        return self._available_choices

    @property
    def current_choice(self):
        return self._current_choice

    @current_choice.setter
    def current_choice(self, value):
        self._current_choice = value


class LaunchSettings:
    def __init__(self):
        self._data: dict[SettingName, Option] = dict()

    def add_option(self, option: Option):
        if option.name in self._data:
            raise ValueError('Can not update')

        self._data[option.name] = option

    def get_option(self, name: SettingName):
        return self._data.get(name)

    def get_current_choice_value(self, name: SettingName):
        return self._data.get(name).current_choice.value

    def sync_with_sources(self):
        for o in self._data.values():
            try:
                o.sync_with_sources()
            except Exception as e:
                message = f'option:{o.name} e:{e}'
                raise RuntimeError(f'Can not update option: {message}')

    def check_all_options(self):
        for option in self._data.values():
            if not option.is_current_choice_legit():
                logger.warning(f'Applied setting is not legit: '
                               f'{option.name}={option.current_choice}')

    def apply_settings(self, settings: dict[SettingName, str]):
        for name, value in settings.items():
            option = self.get_option(name=name)

            if option is None:
                logger.warning(f'No option for name {name}')
                continue

            option.current_choice = Choice(value=value, label=value)

    def to_json(self) -> str:
        settings = {name: option.current_choice.value
                    for name, option in self._data.items()}

        return json.dumps(
            settings,
            indent=2,
        )

    @classmethod
    def from_json(cls, text: str) -> 'LaunchSettings':
        d = json.loads(text)

        new_settings = create_launch_settings(settings_dict=d)

        return new_settings


def create_launch_settings(settings_dict: dict[SettingName, str] = None) -> LaunchSettings:
    if settings_dict is None:
        settings_dict = {
            SettingName.mode: AppMode.preview,
            SettingName.camera: CameraDevice.video0,
            SettingName.virtual_camera: VirtualCameraDevice.video9,
            SettingName.avatar_name: 'kanisan',
        }

    def create_option(name: SettingName, choices_source: ChoicesSource):
        return Option(name=name,
                      settings_source=DictSettingsSource(
                          name=name,
                          settings_dict=settings_dict
                      ),
                      choices_source=choices_source
                      )

    mode_option = create_option(
        name=SettingName.mode,
        choices_source=ModeChoicesSource()
    )

    cis = CamerasInfoStorage()

    camera_option = create_option(
        name=SettingName.camera,
        choices_source=CameraChoicesSource(camera_info_storage=cis)
    )

    virtual_camera_option = create_option(
        name=SettingName.virtual_camera,
        choices_source=VirtualCameraChoicesSource()
    )

    avatar_path_option = create_option(
        name=SettingName.avatar_name,
        choices_source=AvatarPathChoicesSource()
    )

    ld = LaunchSettings()

    ld.add_option(mode_option)
    ld.add_option(camera_option)
    ld.add_option(virtual_camera_option)
    ld.add_option(avatar_path_option)

    return ld


def tests():
    def ppprint(text):
        pprint(text, sort_dicts=False, width=61)

    ld = create_launch_settings()
    ld.sync_with_sources()

    print(ld.to_json())


if __name__ == '__main__':
    tests()
