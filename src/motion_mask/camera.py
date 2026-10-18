import dataclasses

from cv2_enumerate_cameras import enumerate_cameras

from motion_mask import loggers
from motion_mask.constants import VirtualCamera, VirtualCameraBackend, VirtualCameraDevice

logger = loggers.LoggerFactory.get_logger(name=__name__)


@dataclasses.dataclass
class CameraInfo:
    path: str
    vid: int
    pid: int
    index: int
    name: str
    backend: int

    def get_info(self):
        return {
            'index': self.index,
            'vid': self.vid,
            'pid': self.pid,
            'name': self.name,
            'path': self.path,
            'backend': self.backend
        }


class CamerasInfoStorage:
    def __init__(self):
        self._camera_infos: dict[int, CameraInfo] = dict()

    def update(self):
        self._camera_infos = dict()
        for camera_info in enumerate_cameras():
            ci = CameraInfo(
                path=camera_info.path,
                vid=camera_info.vid,
                pid=camera_info.pid,
                index=camera_info.index,
                name=camera_info.name,
                backend=camera_info.backend,
            )

            logger.info(f'Camera detected: {ci.get_info()}')
            self._camera_infos[ci.index] = ci

    @property
    def camera_infos(self) -> list[CameraInfo]:
        return list(self._camera_infos.values())

    def get_by_index(self, index: int) -> list[CameraInfo] | None:
        return [self._camera_infos.get(index)]

    def get_by_path(self, path: str) -> list[CameraInfo] | None:
        result = []
        for ci in self._camera_infos.values():
            if ci.path == path:
                result.append(ci)

        return result

    def get_by_name(self, name_part: str) -> list[CameraInfo] | None:
        result = []

        name_part_lower = name_part.lower()
        for ci in self._camera_infos.values():
            if name_part_lower in ci.name.lower():
                result.append(ci)

        return result

    def get_camera_info(self, ref: str | int) -> list[CameraInfo] | None:
        if isinstance(ref, int):
            return self.get_by_index(ref)

        try:
            index_probably = int(ref)
            return self.get_by_index(index_probably)
        except ValueError:
            pass

        if isinstance(ref, str):
            result = self.get_by_path(ref)
            if result:
                return result

            return self.get_by_name(ref)


class VirtualCamerasInfoStorage:
    def __init__(self):
        self.mapping = {
            VirtualCamera.v4l2loopback_video9:
                (VirtualCameraBackend.v4l2loopback, VirtualCameraDevice.video9),
            VirtualCamera.v4l2loopback_video8:
                (VirtualCameraBackend.v4l2loopback, VirtualCameraDevice.video8),
            VirtualCamera.v4l2loopback_video7:
                (VirtualCameraBackend.v4l2loopback, VirtualCameraDevice.video7),
            VirtualCamera.obs:
                (VirtualCameraBackend.obs, VirtualCameraDevice.obs),
            VirtualCamera.unitycapture:
                (VirtualCameraBackend.unity_capture, VirtualCameraDevice.unity_capture),
        }

    def get_mapping(self):
        return self.mapping.copy()

    def get_backend_device_pair(self, setting: str):
        return self.mapping[VirtualCamera(setting)]
