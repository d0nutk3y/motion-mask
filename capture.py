import threading
import time

import cv2
import numpy as np

import loggers

logger = loggers.LoggerFactory.get_logger(name=__name__)


class CaptureWrap(threading.Thread):
    def __init__(self, number=0, width=640, height=360):
        super().__init__()
        self.stop_trigger = False

        self.capture = cv2.VideoCapture(number)

        if not self.capture.isOpened():
            e = RuntimeError("ERROR: Cannot open camera")
            logger.error(e)
            raise e

        # Web camera optimal capture settings
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        self.blank_frame = np.zeros((width, height, 3), dtype=np.uint8)
        self.frame = self.blank_frame

    def run(self):
        try:
            self._run()
        except Exception as e:
            logger.error(f'Problems with camera: {e}')
            return


    def _run(self):
        while True:
            if self.stop_trigger:
                break

            ret, frame = self.capture.read()
            if ret:
                self.frame = frame

            time.sleep(1 / 30)

    def get_frame(self):
        return self.frame if self.frame is not None else self.blank_frame

    def stop(self):
        self.stop_trigger = True
        self.capture.release()
