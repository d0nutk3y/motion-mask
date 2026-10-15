import enum


class AppMode(enum.StrEnum):
    SETUP = 'setup'
    PREVIEW = 'preview'
    LIVE = 'live'


class VirtualCamera(enum.StrEnum):
    # pyvirtualcam device type
    v4l2loopback = 'v4l2loopback'
    obs = 'obs'
    unitycapture = 'unitycapture'
    some_video_device = '/dev/video9'

