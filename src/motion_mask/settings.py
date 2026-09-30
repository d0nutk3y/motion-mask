import dataclasses
import enum
import json

from common import (
    MouthThresholdsNames,
    GazeThresholdsNames,
    EyelidThresholdsNames,
    BrowThresholdsNames)


@dataclasses.dataclass
class ThresholdSettings:
    high: float
    low: float

    def to_dict(self):
        return {'high': self.high, 'low': self.low}

    @staticmethod
    def create_from_dict(d: dict):
        return ThresholdSettings(
            high=d['high'],
            low=d['low']
        )

    def percent_diff(self, other: 'ThresholdSettings'):
        delta = abs(other.high - self.high)
        average = (self.high + other.high) / 2
        ratio = delta / average

        return round(ratio, 3)


class SettingsSection(enum.StrEnum):
    threshold_settings = 'threshold_settings'
    common_settings = 'common_settings'


class CommonSettings(enum.StrEnum):
    frames_to_drop = 'frames_to_drop'


class SettingsException(Exception):
    pass


class Settings:
    def __init__(self):
        self.common_settings_mapping = self.get_commons_defaults()
        self.thresholds_settings_mapping = self.get_thresholds_defaults()

    @classmethod
    def get_commons_defaults(cls) -> dict[str, str | int | float]:
        return {
            CommonSettings.frames_to_drop: 0
        }

    @classmethod
    def get_thresholds_defaults(cls) -> dict[str, ThresholdSettings]:
        brows: dict[str, ThresholdSettings] = {
            BrowThresholdsNames.left_common: ThresholdSettings(
                high=0.20, low=0.20 * 0.1
            ),
            BrowThresholdsNames.right_common: ThresholdSettings(
                high=0.20, low=0.20 * 0.1
            ),
        }

        eyelids: dict[str, ThresholdSettings] = {
            EyelidThresholdsNames.left_blink: ThresholdSettings(
                high=0.50, low=0.50 * 0.1
            ),
            EyelidThresholdsNames.left_squint: ThresholdSettings(
                high=0.55, low=0.55 * 0.1
            ),
            EyelidThresholdsNames.left_wide: ThresholdSettings(
                high=0.015, low=0.015 * 0.1
            ),
            EyelidThresholdsNames.right_blink: ThresholdSettings(
                high=0.50, low=0.50 * 0.1
            ),
            EyelidThresholdsNames.right_squint: ThresholdSettings(
                high=0.55, low=0.55 * 0.1
            ),
            EyelidThresholdsNames.right_wide: ThresholdSettings(
                high=0.015, low=0.015 * 0.1
            ),

        }

        gazes: dict[str, ThresholdSettings] = {
            GazeThresholdsNames.left_look_up: ThresholdSettings(
                high=0.2, low=0.2 * 0.1
            ),
            GazeThresholdsNames.left_look_down: ThresholdSettings(
                high=0.6, low=0.6 * 0.1
            ),
            GazeThresholdsNames.left_look_in: ThresholdSettings(
                high=0.4, low=0.4 * 0.1
            ),
            GazeThresholdsNames.left_look_out: ThresholdSettings(
                high=0.4, low=0.4 * 0.1
            ),
            GazeThresholdsNames.right_look_up: ThresholdSettings(
                high=0.2, low=0.2 * 0.1
            ),
            GazeThresholdsNames.right_look_down: ThresholdSettings(
                high=0.6, low=0.6 * 0.1
            ),
            GazeThresholdsNames.right_look_in: ThresholdSettings(
                high=0.4, low=0.4 * 0.1
            ),
            GazeThresholdsNames.right_look_out: ThresholdSettings(
                high=0.4, low=0.4 * 0.1
            ),
        }

        mouth: dict[str, ThresholdSettings] = {
            MouthThresholdsNames.smile_left: ThresholdSettings(
                high=0.1, low=0.1 * 0.01
            ),
            MouthThresholdsNames.smile_right: ThresholdSettings(
                high=0.1, low=0.1 * 0.01
            ),
            MouthThresholdsNames.open: ThresholdSettings(
                high=0.02, low=0.02 * 0.01
            ),
            MouthThresholdsNames.pucker: ThresholdSettings(
                high=0.7, low=0.7 * 0.01
            ),
        }

        parts = [
            brows,
            eyelids,
            gazes,
            mouth,
        ]

        result = {}
        for d in parts:
            result |= d

        return result

    def to_json(self) -> str:
        threshold_settings = {n: s.to_dict() for n, s
                              in self.thresholds_settings_mapping.items()}

        d = {
            SettingsSection.common_settings: self.common_settings_mapping,
            SettingsSection.threshold_settings: threshold_settings,
        }

        return json.dumps(
            d,
            indent=2,
        )

    @classmethod
    def from_json(cls, text: str) -> 'Settings':
        d = json.loads(text)
        new_settings = Settings()

        d_cs: dict = d[SettingsSection.common_settings]
        new_settings.common_settings_mapping = {k: cls.convert(v)
                                                for k, v in d_cs.items()}

        d_ts: dict = d[SettingsSection.threshold_settings]
        new_settings.thresholds_settings_mapping = {k: ThresholdSettings.create_from_dict(d=v)
                                                    for k, v in d_ts.items()}

        return new_settings

    @classmethod
    def convert(cls, text_value: str) -> int | float | bool | str:
        try:
            return int(text_value)
        except ValueError:
            pass

        try:
            return float(text_value)
        except ValueError:
            pass

        if text_value.lower() == 'true':
            return True

        if text_value.lower() == 'false':
            return False

        return text_value

    def get(self, setting: str):
        if setting not in self.common_settings_mapping:
            raise ValueError()

        as_str = self.common_settings_mapping[setting]

        return self.convert(text_value=as_str)

    def get_thresholds_settings(self):
        return self.thresholds_settings_mapping.copy()


if __name__ == '__main__':
    settings = Settings()
    json_text = settings.to_json()

    print('\n'.join(json_text.split(sep='\n')[:12] + ['...']))
    print(f'len of json text: {len(json_text)}\n')

    settings_from_json = Settings.from_json(text=json_text)

    json_text_2 = settings_from_json.to_json()
    print('\n'.join(json_text_2.split(sep='\n')[:12] + ['...']))
    print(f'len of json text: {len(json_text_2)}\n')

    # must be same
    assert (json_text_2 == json_text)
