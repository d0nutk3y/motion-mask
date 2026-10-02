import threading

import cv2
import numpy as np

from motion_mask import loggers

logger = loggers.LoggerFactory.get_logger(name=__name__)


class CaptureWrap(threading.Thread):
    def __init__(self, number=0, width=640, height=360, fps=30):
        super().__init__()
        self.capture = None

        self.number = number
        self.width = width
        self.height = height
        self._frame_interval = 1.0 / fps

        self._stop_event = threading.Event()
        self._error_event = threading.Event()
        self.blank_frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        self.frame = self.blank_frame

    def has_errors(self) -> bool:
        return self._error_event.is_set()

    def run(self):
        try:
            self.capture = cv2.VideoCapture(self.number)

            if not self.capture.isOpened():
                raise RuntimeError("Can not open camera")

            # Web camera optimal capture settings
            self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            self._check_camera_resolution()

        except Exception as e:
            logger.error(f'Problems with camera init: {e}')
            self._error_event.set()

            if self.capture is not None:
                self.capture.release()

            return

        try:
            self._run()
        except Exception as e:
            logger.error(f'Problems with camera runtime: {e}')
            self._error_event.set()
            return

    def _run(self):
        try:
            while not self._stop_event.is_set():

                ret, frame = self.capture.read()
                if ret:
                    self.frame = frame

                self._stop_event.wait(timeout=self._frame_interval)
        finally:
            if self.capture is not None:
                try:
                    self.capture.release()
                except Exception as e:
                    logger.warning(f'Error releasing camera: {e}')

    def get_frame(self):
        return self.frame

    def stop(self):
        self._stop_event.set()

    def _check_camera_resolution(self):
        actual_w = self.capture.get(cv2.CAP_PROP_FRAME_WIDTH)
        actual_h = self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT)
        if actual_w != self.width or actual_h != self.height:
            logger.warning(
                f'Camera resolution mismatch: requested {self.width}x{self.height}, got {actual_w}x{actual_h}')
