import dataclasses
import enum
import pathlib
from pprint import pprint

from cv2_enumerate_cameras import enumerate_cameras

from motion_mask import loggers
from motion_mask.constants import AppMode

logger = loggers.LoggerFactory.get_logger(name=__name__)


class SettingName(enum.StrEnum):
    mode = 'mode'
    camera = 'camera'
    virtual_camera = 'virtual_camera'
    avatar_name = 'avatar_name'


class DefaultStuffFactory:
    def create_default_settings(self) -> dict[SettingName, str]:
        return {
            SettingName.mode: 'preview',
            SettingName.camera: '/dev/video0',
            SettingName.virtual_camera: '/dev/video9',
            SettingName.avatar_name: 'kanisan',
        }


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


class ChoicesSource:
    def get_choices(self):
        raise NotImplementedError()


class ModeChoicesSource(ChoicesSource):
    _DEFAULT_MODES = [mode.value for mode in AppMode]

    def get_choices(self):
        return self._DEFAULT_MODES


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

    def get_choices(self):
        self.camera_info_storage.update()
        camera_infos = self.camera_info_storage.camera_infos

        return [x.index for x in camera_infos]


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

    def get_choices(self):
        avatars_paths = list()
        path = self.default_avatars_dir_path

        for child in path.glob(pattern='*'):
            if child.is_dir():
                logger.debug(f'found avatar dir: {child.absolute()}')
                avatars_paths.append(child.name)

        return avatars_paths


class Option:
    name: SettingName

    _available_choices: list[str] | None
    _old_choice: str | None
    _new_choice: str | None

    def __init__(self, name: SettingName,
                 settings_source: SettingsSource,
                 choices_source: ChoicesSource):
        self.name = name
        self.settings_source = settings_source
        self.choices_source = choices_source

        self._available_choices = None
        self._old_choice = None
        self._new_choice = None

    def is_new_choice_legit(self):
        if not self._new_choice in self._available_choices:
            raise ValueError(f'Value {self._new_choice} '
                             f'is not in {self._available_choices}')

    def is_valid(self):
        if self._available_choices is None or not self._available_choices:
            return False

        if self._old_choice is None:
            return False

        if self._new_choice is None:
            return False

        return True

    def update(self):
        self._available_choices = self.choices_source.get_choices()

        available_choices_as_text = ', '.join([str(x) for x in self._available_choices])
        logger.debug(f'{self.name}: updated available choices: {available_choices_as_text}')

        self._old_choice = self.settings_source.get_option_value()
        logger.debug(f'{self.name}: updated old_choice: {self._old_choice}')

    def is_old_choice_in_choices(self) -> bool:
        if self._old_choice is None or self._available_choices is None:
            return False

        return self._old_choice in self._available_choices

    def is_new_value_set(self):
        return self._new_choice is not None

    @property
    def available_choices(self):
        return self._available_choices

    @property
    def old_choice(self):
        return self._old_choice

    @property
    def new_choice(self):
        return self._new_choice

    @new_choice.setter
    def new_choice(self, value):
        self._new_choice = value

    def get_info(self):
        return {
            'old': str(self.old_choice),
            'new': str(self.new_choice),
            'choices': self.available_choices,
        }


class LaunchSettings:
    def __init__(self, camera_info_storage: CamerasInfoStorage):
        self.camera_info_storage = camera_info_storage
        self._data: dict[SettingName, Option] = dict()

    def add_option(self, option: Option):
        if option.name in self._data:
            raise ValueError('Can not update')

        self._data[option.name] = option

    def get_option(self, name: SettingName):
        return self._data.get(name)

    def get_new_choice(self, name: SettingName):
        return self._data.get(name).new_choice

    def to_dict(self):
        return {k.value: v.get_info()
                for k, v in self._data.items()}

    def update_all_options(self):
        for o in self._data.values():
            try:
                o.update()
            except Exception as e:
                message = f'option:{o.name} e:{e}'
                raise RuntimeError(f'Can not update option: {message}')

    def check_all_options(self):
        for option in self._data.values():
            if not option.is_new_choice_legit():
                logger.warning(f'Applied setting is not legit: '
                               f'{option.name}={option.new_choice}')

    def apply_settings(self, settings: dict[SettingName, str]):
        for name, value in settings.items():
            option = self.get_option(name=name)

            if option is None:
                logger.warning(f'No option for name {name}')
                continue

            option.new_choice = value


def create_default_launch_settings():
    df = DefaultStuffFactory()
    default_settings = df.create_default_settings()

    def create_option(name: SettingName, choices_source: ChoicesSource):
        return Option(name=name,
                      settings_source=DictSettingsSource(
                          name=name,
                          settings_dict=default_settings
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
        choices_source=CameraChoicesSource(camera_info_storage=cis)
    )

    avatar_path_option = create_option(
        name=SettingName.avatar_name,
        choices_source=AvatarPathChoicesSource()
    )

    ld = LaunchSettings(camera_info_storage=cis)

    ld.add_option(mode_option)
    ld.add_option(camera_option)
    ld.add_option(virtual_camera_option)
    ld.add_option(avatar_path_option)

    return ld


def tests():
    def ppprint(text):
        pprint(text, sort_dicts=False, width=60)

    ld = create_default_launch_settings()
    ld.update_all_options()
    ppprint(ld.to_dict())


if __name__ == '__main__':
    tests()
