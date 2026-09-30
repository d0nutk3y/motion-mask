import threading
import time

import cv2
import numpy as np
import pyvirtualcam

import loggers

logger = loggers.LoggerFactory.get_logger(name=__name__)


class VirtualCameraInterface():
    def set_frame(self, frame):
        raise NotImplementedError()

    def stop(self):
        raise NotImplementedError()

    def start(self):
        raise NotImplementedError()


class NoneVirtualCamera(VirtualCameraInterface):
    def set_frame(self, frame):
        pass

    def stop(self):
        pass

    def start(self):
        pass


class DefaultVirtualCamera(threading.Thread, VirtualCameraInterface):
    def __init__(self, device: str):
        super().__init__()

        self.stop_trigger = False

        self.device = device

        self.width = 1024
        self.height = 576
        self.fps = 30

        self.fit_to_camera_resolution = True

        self.blank_frame = np.full((self.height, self.width, 3), 16, dtype=np.uint8)
        self._frame = self.blank_frame

    def run(self):
        try:
            self._run()
        except Exception as e:
            logger.error(f'Problems with starting virtual camera: {e}')
            return

    def _run(self):
        with pyvirtualcam.Camera(
                device=self.device,
                width=self.width,
                height=self.height,
                fps=self.fps) as cam:

            while True:
                if self.stop_trigger:
                    break

                cam.send(self._frame)
                time.sleep(1 / self.fps)

    def set_frame(self, frame):
        converted_to_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        if self.fit_to_camera_resolution:
            f = cv2.resize(converted_to_rgb, (self.width, self.height))
        else:
            f = converted_to_rgb

        self._frame = f

    def stop(self):
        self.stop_trigger = True
