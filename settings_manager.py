from settings import Settings, SettingsException
from files_io import Storage, FileStorage

import loggers

logger = loggers.LoggerFactory.get_logger(name=__name__)


class SettingsManager:
    settings_path: str = './settings.json'

    def __init__(self):
        self.settings_storage: Storage = FileStorage(self.settings_path)

        try:
            self.load_settings()
        except SettingsException:
            self.settings: Settings = Settings()
            logger.info(f'Default settings loaded')

    def update_thresholds_mapping(self, mapping):
        original_mapping = self.settings.thresholds_settings_mapping

        for n, ts in original_mapping.items():
            try:
                new_ts = mapping[n]
            except KeyError:
                continue

            original_mapping[n] = new_ts

    def load_settings(self):
        try:
            text = self.settings_storage.load()
            self.settings = Settings.from_json(text=text)
            logger.info('Settings loaded')
        except Exception:
            logger.error(f'Error with loading settings')
            raise SettingsException('Loading error')

    def save_settings(self):
        try:
            json_text = self.settings.to_json()
            self.settings_storage.save(text=json_text)
            logger.info('Settings saved')
        except Exception as e:
            logger.error(f'Error with saving settings: {e}')
            raise SettingsException('Saving error')
