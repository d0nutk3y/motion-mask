import threading

from motion_mask import loggers

logger = loggers.LoggerFactory.get_logger(name=__name__)


class AppTest(threading.Thread):
    def __init__(self):
        super().__init__()
        self._run_loop_timeout = 2
        self._stop_event = threading.Event()

    def run(self):
        logger.info('Starting App')
        try:
            while not self._stop_event.is_set():
                logger.info('Tick on app test thread')

                self._stop_event.wait(timeout=self._run_loop_timeout)
        finally:
            try:
                self.graceful_shutdown()
            except Exception as e:
                logger.warning(f'Error on graceful shutdown: {e}')

    def apply_settings(self):
        logger.info('apply settings')

    def graceful_shutdown(self):
        logger.info('graceful shutdown')

    def stop(self):
        self._stop_event.set()
