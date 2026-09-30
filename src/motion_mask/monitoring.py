import os
import threading
import time
import psutil

import loggers

logger = loggers.LoggerFactory.get_logger(name=__name__)


class MemoryMonitor(threading.Thread):
    def __init__(self,
                 idle_seconds: float = 5.0,
                 launch_delay: float = 0):
        super(MemoryMonitor, self).__init__(daemon=True)

        self.idle_seconds = idle_seconds
        self.launch_delay = launch_delay

        self.continue_loop = True
        self.base_rss_mb: float = 0.0

        self.process = psutil.Process(os.getpid())


    def convert_to_MB(self, value: float) -> float:
        return value / (1024 * 1024)

    def run(self):
        time.sleep(self.launch_delay)
        logger.debug(f'Monitoring started!')
        self.base_rss_mb = self.convert_to_MB(self.process.memory_info().rss)

        while True:
            self.idle()

            if not self.continue_loop:
                break

            try:
                self.measure()
            except Exception as e:
                logger.error(f'Unknown error: {e}')
                break

    def stop(self):
        self.continue_loop = False

    def idle(self):
        time.sleep(self.idle_seconds)

    def measure(self):
        mem_info = self.process.memory_info()
        rss_mb = self.convert_to_MB(mem_info.rss)
        vms_mb = self.convert_to_MB(mem_info.vms)
        mem_percent = self.process.memory_percent()

        message = (f'RSS: {rss_mb:.2f} MB | '
                   f'VMS: {vms_mb:.2f} MB | '
                   f'Memory usage: {mem_percent:.2f}% | '
                   f'base RSS: {self.base_rss_mb:.2f} MB')
        logger.debug(message)
