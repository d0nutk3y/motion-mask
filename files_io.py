from pathlib import Path

import loggers

logger = loggers.LoggerFactory.get_logger(name=__name__)


class StorageException(Exception):
    pass


class Storage:
    def save(self, text: str):
        raise NotImplementedError()

    def load(self) -> str:
        raise NotImplementedError()


class FileStorage(Storage):
    encoding = 'utf-8'

    def __init__(self, filepath: str):
        self.filepath = Path(filepath)

    def save(self, text: str):
        try:
            self.filepath.parent.mkdir(parents=True, exist_ok=True)

            with open(self.filepath, 'w', encoding=self.encoding) as f:
                f.write(text)

        except Exception as e:
            logger.error(f"Save error: {type(e)}: {e}")

    def load(self) -> str:
        try:
            with open(self.filepath, 'r', encoding=self.encoding) as f:
                text = f.read()
            return text

        except FileNotFoundError as e:
            logger.error(f"File not found: {self.filepath}")
            raise StorageException()
        except Exception as e:
            logger.error(f"Load error: {type(e)}: {e}")
            raise StorageException()


if __name__ == "__main__":
    fs = FileStorage(filepath='./test.json')
    test_text = 'some\ntest_text\nfor test'

    fs.save(text=test_text)

    text_from_file = fs.load()
    print(text_from_file)

    print(f'Is same: {test_text == text_from_file}')
