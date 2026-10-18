import dataclasses
import enum

from motion_mask import loggers

logger = loggers.LoggerFactory.get_logger(name=__name__)


class SettingName(enum.StrEnum):
    mode = 'mode'
    camera = 'camera'
    virtual_camera = 'virtual camera'
    avatar_name = 'avatar name'


class SettingsSource:
    def get_option_value(self, setting_name: SettingName):
        raise NotImplementedError()


class DictSettingsSource(SettingsSource):
    def __init__(self,
                 settings_dict: dict[SettingName, str]):
        self.settings_dict = settings_dict

    def get_option_value(self, setting_name: SettingName):
        return self.settings_dict.get(setting_name)


@dataclasses.dataclass
class Choice:
    value: str | int
    label: str


class ChoicesSource:
    def get_choices(self) -> list[Choice]:
        raise NotImplementedError()


class Option:
    def __init__(self, name: SettingName):
        self.name: SettingName = name
        self._available_choices: dict[str, Choice] = {}
        self._current_choice: Choice = Choice(label='no choice',
                                              value='no choice')

    def sync_with_sources(self, choices_source: ChoicesSource):
        self._available_choices = {c.value: c for c
                                   in choices_source.get_choices()}

        available_choices_as_text = ', '.join([str(x) for x in self._available_choices.keys()])
        logger.debug(f'{self.name}: updated available choices: {available_choices_as_text}')

    def sync_with_settings(self, settings_source: SettingsSource):
        value = settings_source.get_option_value(setting_name=self.name)
        if value is None:
            return

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

    def sync_with_settings_source(self, settings_source: SettingsSource = None):
        options = self._data.values()
        for o in options:
            try:
                if settings_source is not None:
                    o.sync_with_settings(settings_source=settings_source)
            except Exception as e:
                message = f'option:{o.name} e:{e}'
                raise RuntimeError(f'Can not update option: {message}')

    def to_dict(self) -> dict[SettingName, str]:
        return {name: option.current_choice.value
                for name, option in self._data.items()}
