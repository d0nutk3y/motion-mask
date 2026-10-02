import threading

import cv2
import numpy as np
import pyvirtualcam

from motion_mask import loggers

logger = loggers.LoggerFactory.get_logger(name=__name__)


class VirtualCameraInterface():
    def set_frame(self, frame):
        raise NotImplementedError()

    def stop(self):
        raise NotImplementedError()

    def start(self):
        raise NotImplementedError()

    def has_errors(self):
        raise NotImplementedError()



class NoneVirtualCamera(VirtualCameraInterface):
    def set_frame(self, frame):
        pass

    def stop(self):
        pass

    def start(self):
        pass

    def has_errors(self):
        return False

    def join(self):
        pass


class DefaultVirtualCamera(threading.Thread, VirtualCameraInterface):
    def __init__(self, device: str):
        super().__init__()

        self._stop_event = threading.Event()
        self._error_event = threading.Event()

        self.device = device

        self.width = 1024
        self.height = 576
        self.fps = 30

        self.fit_to_camera_resolution = True

        self.blank_frame = np.full((self.height, self.width, 3), 16, dtype=np.uint8)
        self._frame = self.blank_frame

    def has_errors(self):
        return self._error_event.is_set()

    def run(self):
        try:
            self._run()
        except Exception as e:
            logger.error(f'Problems with starting virtual camera: {e}')
            self._error_event.set()

    def _run(self):
        with pyvirtualcam.Camera(
                device=self.device,
                width=self.width,
                height=self.height,
                fps=self.fps) as cam:
            while not self._stop_event.is_set():
                cam.send(self._frame)
                timeout = 1 / self.fps
                self._stop_event.wait(timeout=timeout)

    def set_frame(self, frame):
        converted_to_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        if self.fit_to_camera_resolution:
            f = cv2.resize(converted_to_rgb, (self.width, self.height))
        else:
            f = converted_to_rgb

        self._frame = f

    def stop(self):
        self._stop_event.set()
