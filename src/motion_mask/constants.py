import enum


class AppMode(enum.StrEnum):
    calibration = 'calibration'
    preview = 'preview'
    live = 'live'


class PathsToFiles(enum.StrEnum):
    launch_settings = 'settings/launch.json'
    model = 'landmarkers/face_landmarker.task'
    avatar_settings = 'settings/avatar.json'


class VirtualCamera(enum.StrEnum):
    # pyvirtualcam device type
    v4l2loopback_video9 = 'v4l2loopback/video9'
    v4l2loopback_video8 = 'v4l2loopback/video8'
    v4l2loopback_video7 = 'v4l2loopback/video7'
    obs = 'obs'
    unitycapture = 'unitycapture'


class CameraDevice(enum.StrEnum):
    video0 = '/dev/video0'


class VirtualCameraDevice(enum.StrEnum):
    video9 = '/dev/video9'
    video8 = '/dev/video8'
    video7 = '/dev/video7'
    obs = 'OBS Virtual Camera'
    unity_capture = 'Unity Video Capture'


class VirtualCameraBackend(enum.StrEnum):
    v4l2loopback = 'v4l2loopback'
    obs = 'obs'
    unity_capture = 'unitycapture'
