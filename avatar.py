import enum
from collections import OrderedDict
from pathlib import Path

import cv2
import numpy as np
from mediapipe.tasks.python.components.containers import Category
from mediapipe.tasks.python.vision import FaceLandmarkerResult

from common import (
    BrowState,
    EyelidState,
    GazeState,
    MouthState, BrowThresholdsNames, EyelidThresholdsNames, GazeThresholdsNames,
    MouthThresholdsNames, FaceParts,
    BrowIndexMapping, EyelidIndexMapping, GazeIndexMapping, MouthIndexMapping)

import frame_utils as fu
from settings import ThresholdSettings

from shapes import (
    Shape,
    ShapeDefault,
)

import loggers

logger = loggers.LoggerFactory.get_logger(name=__name__)


class FileNames(enum.StrEnum):
    absent = 'absent'
    base = 'base'

    brow_left_normal = 'brow_left_normal'
    brow_left_up = 'brow_left_up'
    brow_right_normal = 'brow_right_normal'
    brow_right_up = 'brow_right_up'

    eyelid_left_closed = 'eyelid_left_closed'
    eyelid_left_opened_full = 'eyelid_left_opened_full'
    eyelid_left_opened_normal = 'eyelid_left_opened_normal'
    eyelid_left_squint = 'eyelid_left_squint'
    eyelid_right_closed = 'eyelid_right_closed'
    eyelid_right_opened_full = 'eyelid_right_opened_full'
    eyelid_right_opened_normal = 'eyelid_right_opened_normal'
    eyelid_right_squint = 'eyelid_right_squint'

    gaze_left_center = 'gaze_left_center'
    gaze_left_down = 'gaze_left_down'
    gaze_left_down_in = 'gaze_left_down_in'
    gaze_left_down_out = 'gaze_left_down_out'
    gaze_left_in = 'gaze_left_in'
    gaze_left_out = 'gaze_left_out'
    gaze_left_up = 'gaze_left_up'
    gaze_left_up_in = 'gaze_left_up_in'
    gaze_left_up_out = 'gaze_left_up_out'

    gaze_right_center = 'gaze_right_center'
    gaze_right_down = 'gaze_right_down'
    gaze_right_down_in = 'gaze_right_down_in'
    gaze_right_down_out = 'gaze_right_down_out'
    gaze_right_in = 'gaze_right_in'
    gaze_right_out = 'gaze_right_out'
    gaze_right_up = 'gaze_right_up'
    gaze_right_up_in = 'gaze_right_up_in'
    gaze_right_up_out = 'gaze_right_up_out'

    mouth_normal_closed = 'mouth_normal_closed'
    mouth_normal_opened = 'mouth_normal_opened'
    mouth_smile_closed = 'mouth_smile_closed'
    mouth_smile_opened = 'mouth_smile_opened'


class Threshold:
    def __init__(self,
                 low: float,
                 high: float, ):

        self.low = low
        self.high = high

        self._is_active = False

    def do_exceeds(self, shape: Shape) -> bool:
        score = shape.get_score()

        if self._is_active:
            if score < self.low:
                self._is_active = False
        else:
            if score > self.high:
                self._is_active = True

        return self._is_active

    def reset(self, active: bool = False):
        self._is_active = active

    @staticmethod
    def create_none():
        return Threshold(low=0.99, high=1.0)

    def update(self, threshold_settings: ThresholdSettings):
        self.low = threshold_settings.low
        self.high = threshold_settings.high
        self._is_active = False


class Part:
    name: str = 'part'
    blendshapes_indexes: list[int] = None
    thresholds_names: list[str] = None

    state_to_file_mapping: dict[str, str] = {}

    def __init__(self):
        self.shapes: dict[int, Shape] = {i: ShapeDefault(index=i)
                                         for i in self.blendshapes_indexes}

        self.thresholds: dict[str, Threshold] = {n: Threshold.create_none()
                                                 for n in self.thresholds_names}

    def update_thresholds(self, thresholds_mapping: dict[str, Threshold]):
        self.thresholds = {}

        for n in self.thresholds_names:
            self.thresholds[n] = thresholds_mapping[n]

    def update_blendshapes(self, blendshapes: list[Category]):
        for index in self.blendshapes_indexes:
            self.shapes[index].update(blendshapes=blendshapes)

    def calculate_state(self):
        raise NotImplementedError()

    def get_file_name(self, state):
        return self.state_to_file_mapping[state]


class Brow(Part):
    blendshapes_indexes = BrowIndexMapping
    thresholds_names = BrowThresholdsNames

    def __init__(self):
        super().__init__()

        self.down: Shape | None = None
        self.outer_up: Shape | None = None

        self.brow_threshold: Threshold | None = None

    def calculate_state(self):
        self._sync_fields()

        if self.brow_threshold.do_exceeds(self.outer_up):
            return BrowState.UP

        if self.brow_threshold.do_exceeds(self.down):
            return BrowState.DOWN

        return BrowState.NORMAL

    def _sync_fields(self):
        raise NotImplementedError()


class LeftBrow(Brow):
    name = FaceParts.brow_left

    state_to_file_mapping = {
        BrowState.UP: FileNames.brow_left_up,
        BrowState.NORMAL: FileNames.brow_left_normal,
        BrowState.DOWN: FileNames.brow_left_normal,
    }

    def _sync_fields(self):
        self.down = self.shapes[BrowIndexMapping.left_brow_down]
        self.outer_up = self.shapes[BrowIndexMapping.left_brow_outer_up]
        self.brow_threshold = self.thresholds[BrowThresholdsNames.left_common]


class RightBrow(Brow):
    name = FaceParts.brow_right

    state_to_file_mapping = {
        BrowState.UP: FileNames.brow_right_up,
        BrowState.NORMAL: FileNames.brow_right_normal,
        BrowState.DOWN: FileNames.brow_right_normal,
    }

    def _sync_fields(self):
        self.down = self.shapes[BrowIndexMapping.right_brow_down]
        self.outer_up = self.shapes[BrowIndexMapping.right_brow_outer_up]
        self.brow_threshold = self.thresholds[BrowThresholdsNames.right_common]


class Eyelid(Part):
    blendshapes_indexes = EyelidIndexMapping
    thresholds_names = EyelidThresholdsNames

    def __init__(self):
        super().__init__()

        self.blink: Shape | None = None
        self.squint: Shape | None = None
        self.wide: Shape | None = None
        self.blink_threshold: Threshold | None = None
        self.squint_threshold: Threshold | None = None
        self.wide_threshold: Threshold | None = None

    def calculate_state(self):
        self._sync_fields()

        if self.blink_threshold.do_exceeds(self.blink):
            return EyelidState.CLOSED

        if self.squint_threshold.do_exceeds(self.squint):
            return EyelidState.SQUINT

        if self.wide_threshold.do_exceeds(self.wide):
            return EyelidState.OPENED_FULL

        return EyelidState.OPENED_NORMAL

    def _sync_fields(self):
        raise NotImplementedError()


class LeftEyelid(Eyelid):
    name = FaceParts.eyelid_left

    state_to_file_mapping = {
        EyelidState.CLOSED: FileNames.eyelid_left_closed,
        EyelidState.SQUINT: FileNames.eyelid_left_squint,
        EyelidState.OPENED_FULL: FileNames.eyelid_left_opened_full,
        EyelidState.OPENED_NORMAL: FileNames.eyelid_left_opened_normal,
    }

    def _sync_fields(self):
        self.blink = self.shapes[EyelidIndexMapping.left_eyelid_blink]
        self.squint = self.shapes[EyelidIndexMapping.left_eyelid_squint]
        self.wide = self.shapes[EyelidIndexMapping.left_eyelid_wide]

        self.blink_threshold = self.thresholds[EyelidThresholdsNames.left_blink]
        self.squint_threshold = self.thresholds[EyelidThresholdsNames.left_squint]
        self.wide_threshold = self.thresholds[EyelidThresholdsNames.left_wide]


class RightEyelid(Eyelid):
    name = FaceParts.eyelid_right

    state_to_file_mapping = {
        EyelidState.CLOSED: FileNames.eyelid_right_closed,
        EyelidState.SQUINT: FileNames.eyelid_right_squint,
        EyelidState.OPENED_FULL: FileNames.eyelid_right_opened_full,
        EyelidState.OPENED_NORMAL: FileNames.eyelid_right_opened_normal,
    }

    def _sync_fields(self):
        self.blink = self.shapes[EyelidIndexMapping.right_eyelid_blink]
        self.squint = self.shapes[EyelidIndexMapping.right_eyelid_squint]
        self.wide = self.shapes[EyelidIndexMapping.right_eyelid_wide]

        self.blink_threshold = self.thresholds[EyelidThresholdsNames.right_blink]
        self.squint_threshold = self.thresholds[EyelidThresholdsNames.right_squint]
        self.wide_threshold = self.thresholds[EyelidThresholdsNames.right_wide]


class Gaze(Part):
    blendshapes_indexes = GazeIndexMapping
    thresholds_names = GazeThresholdsNames

    def __init__(self):
        super().__init__()

        self.look_down: Shape | None = None
        self.look_in: Shape | None = None
        self.look_out: Shape | None = None
        self.look_up: Shape | None = None
        self.up_threshold: Threshold | None = None
        self.down_threshold: Threshold | None = None
        self.in_threshold: Threshold | None = None
        self.out_threshold: Threshold | None = None

    def calculate_state(self):
        self._sync_fields()

        if self.up_threshold.do_exceeds(self.look_up):
            if self.in_threshold.do_exceeds(self.look_in):
                return GazeState.UP_IN
            if self.out_threshold.do_exceeds(self.look_out):
                return GazeState.UP_OUT
            return GazeState.UP

        if self.down_threshold.do_exceeds(self.look_down):
            if self.in_threshold.do_exceeds(self.look_in):
                return GazeState.DOWN_IN
            if self.out_threshold.do_exceeds(self.look_out):
                return GazeState.DOWN_OUT
            return GazeState.DOWN

        if self.in_threshold.do_exceeds(self.look_in):
            return GazeState.IN

        if self.out_threshold.do_exceeds(self.look_out):
            return GazeState.OUT

        return GazeState.CENTER

    def _sync_fields(self):
        raise NotImplementedError()


class LeftGaze(Gaze):
    name = FaceParts.gaze_left

    state_to_file_mapping = {
        GazeState.CENTER: FileNames.gaze_left_center,
        GazeState.UP: FileNames.gaze_left_up,
        GazeState.DOWN: FileNames.gaze_left_down,
        GazeState.IN: FileNames.gaze_left_in,
        GazeState.OUT: FileNames.gaze_left_out,
        GazeState.UP_IN: FileNames.gaze_left_up_in,
        GazeState.UP_OUT: FileNames.gaze_left_up_out,
        GazeState.DOWN_IN: FileNames.gaze_left_down_in,
        GazeState.DOWN_OUT: FileNames.gaze_left_down_out,
    }

    def _sync_fields(self):
        self.look_down = self.shapes[GazeIndexMapping.left_look_down]
        self.look_in = self.shapes[GazeIndexMapping.left_look_in]
        self.look_out = self.shapes[GazeIndexMapping.left_look_out]
        self.look_up = self.shapes[GazeIndexMapping.left_look_up]
        self.up_threshold = self.thresholds[GazeThresholdsNames.left_look_up]
        self.down_threshold = self.thresholds[GazeThresholdsNames.left_look_down]
        self.in_threshold = self.thresholds[GazeThresholdsNames.left_look_in]
        self.out_threshold = self.thresholds[GazeThresholdsNames.left_look_out]


class RightGaze(Gaze):
    name = FaceParts.gaze_right

    state_to_file_mapping = {
        GazeState.CENTER: FileNames.gaze_right_center,
        GazeState.UP: FileNames.gaze_right_up,
        GazeState.DOWN: FileNames.gaze_right_down,
        GazeState.IN: FileNames.gaze_right_in,
        GazeState.OUT: FileNames.gaze_right_out,
        GazeState.UP_IN: FileNames.gaze_right_up_in,
        GazeState.UP_OUT: FileNames.gaze_right_up_out,
        GazeState.DOWN_IN: FileNames.gaze_right_down_in,
        GazeState.DOWN_OUT: FileNames.gaze_right_down_out,
    }

    def _sync_fields(self):
        self.look_down = self.shapes[GazeIndexMapping.right_look_down]
        self.look_in = self.shapes[GazeIndexMapping.right_look_in]
        self.look_out = self.shapes[GazeIndexMapping.right_look_out]
        self.look_up = self.shapes[GazeIndexMapping.right_look_up]
        self.up_threshold = self.thresholds[GazeThresholdsNames.right_look_up]
        self.down_threshold = self.thresholds[GazeThresholdsNames.right_look_down]
        self.in_threshold = self.thresholds[GazeThresholdsNames.right_look_in]
        self.out_threshold = self.thresholds[GazeThresholdsNames.right_look_out]


class Mouth(Part):
    name = FaceParts.mouth
    blendshapes_indexes = MouthIndexMapping
    thresholds_names = MouthThresholdsNames

    def __init__(self):
        super().__init__()

        self.smile_left: Shape | None = None
        self.smile_right: Shape | None = None

        self.jaw_open: Shape | None = None
        self.mouth_pucker: Shape | None = None

        self.smile_left_threshold: Threshold | None = None
        self.smile_right_threshold: Threshold | None = None
        self.open_threshold: Threshold | None = None
        self.pucker_threshold: Threshold | None = None

    state_to_file_mapping = {
        MouthState.SMILE_OPENED: FileNames.mouth_smile_opened,
        MouthState.SMILE_CLOSED: FileNames.mouth_smile_closed,
        MouthState.NORMAL_OPENED: FileNames.mouth_normal_opened,
        MouthState.NORMAL_CLOSED: FileNames.mouth_normal_closed,
    }

    def calculate_state(self):
        self._sync_fields()

        is_smiling_left = self.smile_left_threshold.do_exceeds(self.smile_left)
        is_smiling_right = self.smile_right_threshold.do_exceeds(self.smile_right)

        is_smiling = is_smiling_left and is_smiling_right

        triggered_jaw_open = self.open_threshold.do_exceeds(self.jaw_open)
        triggered_mouth_pucker = self.pucker_threshold.do_exceeds(self.mouth_pucker)

        is_opened = any([
            triggered_jaw_open,
            triggered_mouth_pucker,
        ])

        if is_smiling:
            if not is_opened:
                return MouthState.SMILE_CLOSED
            else:
                return MouthState.SMILE_OPENED
        else:
            if not is_opened:
                return MouthState.NORMAL_CLOSED
            else:
                return MouthState.NORMAL_OPENED

    def _sync_fields(self):
        self.smile_left = self.shapes[MouthIndexMapping.smile_left]
        self.smile_right = self.shapes[MouthIndexMapping.smile_right]

        self.jaw_open = self.shapes[MouthIndexMapping.jaw_open]
        self.mouth_pucker = self.shapes[MouthIndexMapping.mouth_pucker]

        self.smile_left_threshold = self.thresholds[MouthThresholdsNames.smile_left]
        self.smile_right_threshold = self.thresholds[MouthThresholdsNames.smile_right]
        self.open_threshold = self.thresholds[MouthThresholdsNames.open]
        self.pucker_threshold = self.thresholds[MouthThresholdsNames.pucker]


class AvatarException(Exception):
    pass


class Layers(enum.StrEnum):
    base = 'base'
    brow_left = 'brow_left'
    brow_right = 'brow_right'
    gaze_left = 'gaze_left'
    gaze_right = 'gaze_right'
    eyelid_left = 'eyelid_left'
    eyelid_right = 'eyelid_right'
    mouth = 'mouth'


class FaceStates:
    STATIC_LAYERS_ORDER_PRIORITY = [
        Layers.base,
    ]

    DYNAMIC_LAYERS_ORDER_PRIORITY = [
        Layers.mouth,
        Layers.gaze_left,
        Layers.gaze_right,
        Layers.eyelid_left,
        Layers.eyelid_right,
        Layers.brow_left,
        Layers.brow_right,
    ]

    def __init__(self):
        self.parts_mapping = {
            Layers.mouth: Mouth(),
            Layers.gaze_left: LeftGaze(),
            Layers.gaze_right: RightGaze(),
            Layers.eyelid_left: LeftEyelid(),
            Layers.eyelid_right: RightEyelid(),
            Layers.brow_left: LeftBrow(),
            Layers.brow_right: RightBrow(),
        }

    def apply_thresholds(self, settings: [str, dict[str, ThresholdSettings]]):
        for face_part in self.parts_mapping.values():
            for name, threshold in face_part.thresholds.items():
                threshold.update(threshold_settings=settings[name])

    def update(self, detection_result: FaceLandmarkerResult):
        b = detection_result.face_blendshapes[0]

        for part in self.parts_mapping.values():
            part.update_blendshapes(blendshapes=b)

    def get_all_filenames(self, states: dict[str, str]):
        filenames = {
            Layers.base: FileNames.base,
        }

        for layer_name in self.DYNAMIC_LAYERS_ORDER_PRIORITY:
            state = states[layer_name]
            file_name = self.parts_mapping[layer_name].get_file_name(state=state)
            filenames[layer_name] = file_name

        return filenames

    def get_all_states(self) -> dict[str, str]:
        return {layer_name: part.calculate_state()
                for layer_name, part in self.parts_mapping.items()}


class StatesTransformer:
    def transform(self, states: dict[str, str]) -> dict[str, str]:
        raise NotImplementedError()


class DefaultStatesTransformer(StatesTransformer):
    EYES_STATES_TRANSITIONS: dict[tuple[str, str], tuple[str, str]] = {
        (GazeState.UP, EyelidState.SQUINT): (GazeState.UP, EyelidState.OPENED_NORMAL),
        (GazeState.UP_IN, EyelidState.SQUINT): (GazeState.UP_IN, EyelidState.OPENED_NORMAL),
        (GazeState.UP_OUT, EyelidState.SQUINT): (GazeState.UP_OUT, EyelidState.OPENED_NORMAL),
        (GazeState.DOWN, EyelidState.CLOSED): (GazeState.CENTER, EyelidState.CLOSED),
        (GazeState.DOWN_IN, EyelidState.CLOSED): (GazeState.CENTER, EyelidState.CLOSED),
        (GazeState.DOWN_OUT, EyelidState.CLOSED): (GazeState.CENTER, EyelidState.CLOSED),
    }

    def resolve_eye_state(self, gaze_state: str, eyelid_state: str
                          ) -> tuple[str, str]:
        return self.EYES_STATES_TRANSITIONS.get(
            (gaze_state, eyelid_state), (gaze_state, eyelid_state)
        )

    def transform(self, states: dict[str, str]) -> dict[str, str]:
        eyes_layers = [
            (Layers.gaze_left, Layers.eyelid_left),
            (Layers.gaze_right, Layers.eyelid_right)
        ]

        for gaze_layer, eyelid_layer in eyes_layers:
            states[gaze_layer], states[eyelid_layer] = self.resolve_eye_state(
                gaze_state=states[gaze_layer],
                eyelid_state=states[eyelid_layer],

            )

        return states


class AvatarCache:
    def __init__(self, max_size: int = 64):
        if max_size <= 8:
            raise ValueError(f'Minimal size of cache must be more than 8')

        self.cache: OrderedDict[tuple, np.ndarray] = OrderedDict()
        self.max_size = max_size

    @staticmethod
    def _make_key(d: dict[str, str]) -> tuple:
        return tuple(sorted(d.items()))

    def get_frame(self,
                  parts_to_filenames_mapping: dict[str, str]
                  ) -> np.ndarray | None:
        key = self._make_key(d=parts_to_filenames_mapping)

        if key in self.cache:
            self.cache.move_to_end(key)
            return self.cache[key]
        else:
            return None

    def register_frame(self,
                       parts_to_filenames_mapping: dict[str, str],
                       frame: np.ndarray
                       ) -> None:
        key = self._make_key(d=parts_to_filenames_mapping)

        if key in self.cache:
            raise ValueError(f'Already registered frame with hash: {key}')

        self.cache[key] = frame

        cache_len = len(self.cache)

        logger.debug(f'New frame registered. Cache length: {cache_len}')

        if cache_len > self.max_size:
            self.cache.popitem(last=False)
            logger.debug(f'Frame popped from cache')


class Avatar:
    def __init__(self, path_to: Path):

        # possible resolutions (affects performance)
        # 256 x 144
        # 384 x 216
        # 512 x 288
        # 640 x 360

        self.width = 640
        self.height = 360

        self.files_names = [name for name in FileNames]

        self.path_to_dir = path_to
        self._check_path_to_dir()

        self.images: dict[str, np.ndarray] = dict()
        self.load_images()

        self.cache: AvatarCache = AvatarCache()

    def _check_path_to_dir(self):
        if not self.path_to_dir.exists():
            raise AvatarException(f'Path does not exist: {self.path_to_dir}')

        if not self.path_to_dir.is_dir():
            raise AvatarException(f'Path is not dir: {self.path_to_dir}')

    @classmethod
    def _load_image(cls, file_path: Path) -> np.ndarray:
        img = cv2.imread(str(file_path), cv2.IMREAD_UNCHANGED)

        if img is None:
            raise ValueError(f"Failed to load image: {file_path}")

        return img

    def load_images(self):
        for name in self.files_names:
            logger.debug(f'loaded: {name}')

            p = self.path_to_dir.joinpath(name).with_suffix('.png')
            image = self._load_image(file_path=p)
            resized_image = fu.resize_image(image=image,
                                            width=self.width,
                                            height=self.height)

            self.images[name] = resized_image

    def rebuild_frame(self, parts_to_filenames_mapping: dict[str, str]) -> np.ndarray:
        # trying to get from cache
        avatar_frame = self.cache.get_frame(
            parts_to_filenames_mapping=parts_to_filenames_mapping
        )

        if avatar_frame is not None:
            return avatar_frame

        # constructing resulting frame
        parts_to_images_mapping: dict[str, np.ndarray] = {
            p: self.images[n] for p, n
            in parts_to_filenames_mapping.items()
        }

        avatar_frame = np.zeros((self.height, self.width, 4), dtype=np.uint8)

        for part, image in parts_to_images_mapping.items():
            avatar_frame = fu.overlay(avatar_frame, image)

        # register frame
        self.cache.register_frame(
            parts_to_filenames_mapping=parts_to_filenames_mapping,
            frame=avatar_frame.copy()
        )

        return avatar_frame

    def get_absent_frame(self):
        return self.images[FileNames.absent]
