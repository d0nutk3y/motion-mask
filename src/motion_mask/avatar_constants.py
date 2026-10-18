import enum


# Indexes -> Thresholds -> States
# All thresholds values must be unique

class FaceParts(enum.StrEnum):
    brow_left = 'brow_left'
    brow_right = 'brow_right'
    gaze_left = 'gaze_left'
    gaze_right = 'gaze_right'
    eyelid_left = 'eyelid_left'
    eyelid_right = 'eyelid_right'
    mouth = 'mouth'


# Brows


class BrowIndexMapping(enum.IntEnum):
    left_brow_down = 1
    left_brow_outer_up = 4
    right_brow_down = 2
    right_brow_outer_up = 5


class BrowThresholdsNames(enum.StrEnum):
    left_common = 'brow_left_common'
    right_common = 'brow_right_common'


class BrowState(enum.StrEnum):
    UP = 'brow up'
    NORMAL = 'brow normal'
    DOWN = 'brow down'


# Eyelids

class EyelidIndexMapping(enum.IntEnum):
    left_eyelid_blink = 9
    left_eyelid_squint = 19
    left_eyelid_wide = 21
    right_eyelid_blink = 10
    right_eyelid_squint = 20
    right_eyelid_wide = 22


class EyelidThresholdsNames(enum.StrEnum):
    left_blink = 'eyelid_left_blink'
    left_squint = 'eyelid_left_squint'
    left_wide = 'eyelid_left_wide'
    right_blink = 'eyelid_right_blink'
    right_squint = 'eyelid_right_squint'
    right_wide = 'eyelid_right_wide'


class EyelidState(enum.StrEnum):
    SQUINT = 'eyelid squint'
    CLOSED = 'eyelid closed'
    OPENED_FULL = 'eyelid opened full'
    OPENED_NORMAL = 'eyelid opened normal'


# Gaze


class GazeIndexMapping(enum.IntEnum):
    left_look_down = 11
    left_look_in = 13
    left_look_out = 15
    left_look_up = 17
    right_look_down = 12
    right_look_in = 14
    right_look_out = 16
    right_look_up = 18


class GazeThresholdsNames(enum.StrEnum):
    left_look_up = 'gaze_left_look_up'
    left_look_down = 'gaze_left_look_down'
    left_look_in = 'gaze_left_look_in'
    left_look_out = 'gaze_left_look_out'
    right_look_up = 'gaze_right_look_up'
    right_look_down = 'gaze_right_look_down'
    right_look_in = 'gaze_right_look_in'
    right_look_out = 'gaze_right_look_out'


class GazeState(enum.StrEnum):
    UP = 'gaze up'
    DOWN = 'gaze down'
    IN = 'gaze in'
    OUT = 'gaze out'
    UP_IN = 'gaze up in'
    UP_OUT = 'gaze up out'
    DOWN_IN = 'gaze down in'
    DOWN_OUT = 'gaze down out'
    CENTER = 'gaze center'


# Mouth


class MouthIndexMapping(enum.IntEnum):
    smile_left = 44
    smile_right = 45
    jaw_open = 25
    mouth_pucker = 38


class MouthThresholdsNames(enum.StrEnum):
    smile_right = 'mouth_smile_right'
    smile_left = 'mouth_smile_left'
    open = 'mouth_open'
    pucker = 'mouth_pucker'


class MouthState(enum.StrEnum):
    NORMAL_CLOSED = 'mouth normal closed'
    NORMAL_OPENED = 'mouth normal opened'
    SMILE_CLOSED = 'mouth smile closed'
    SMILE_OPENED = 'mouth smile opened'


index_to_name_mapping = {
    0: "_neutral",
    1: "browDownLeft",
    2: "browDownRight",
    3: "browInnerUp",
    4: "browOuterUpLeft",
    5: "browOuterUpRight",
    6: "cheekPuff",
    7: "cheekSquintLeft",
    8: "cheekSquintRight",
    9: "eyeBlinkLeft",
    10: "eyeBlinkRight",
    11: "eyeLookDownLeft",
    12: "eyeLookDownRight",
    13: "eyeLookInLeft",
    14: "eyeLookInRight",
    15: "eyeLookOutLeft",
    16: "eyeLookOutRight",
    17: "eyeLookUpLeft",
    18: "eyeLookUpRight",
    19: "eyeSquintLeft",
    20: "eyeSquintRight",
    21: "eyeWideLeft",
    22: "eyeWideRight",
    23: "jawForward",
    24: "jawLeft",
    25: "jawOpen",
    26: "jawRight",
    27: "mouthClose",
    28: "mouthDimpleLeft",
    29: "mouthDimpleRight",
    30: "mouthFrownLeft",
    31: "mouthFrownRight",
    32: "mouthFunnel",
    33: "mouthLeft",
    34: "mouthLowerDownLeft",
    35: "mouthLowerDownRight",
    36: "mouthPressLeft",
    37: "mouthPressRight",
    38: "mouthPucker",
    39: "mouthRight",
    40: "mouthRollLower",
    41: "mouthRollUpper",
    42: "mouthShrugLower",
    43: "mouthShrugUpper",
    44: "mouthSmileLeft",
    45: "mouthSmileRight",
    46: "mouthStretchLeft",
    47: "mouthStretchRight",
    48: "mouthUpperUpLeft",
    49: "mouthUpperUpRight",
    50: "noseSneerLeft",
    51: "noseSneerRight",
}
