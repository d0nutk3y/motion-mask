import enum
import threading
import time

from mediapipe.tasks.python.vision import FaceLandmarkerResult

from common import (index_to_name_mapping,
                    EyelidIndexMapping, EyelidThresholdsNames,
                    BrowThresholdsNames, BrowIndexMapping,
                    GazeIndexMapping, GazeThresholdsNames,
                    MouthIndexMapping, MouthThresholdsNames)

from settings import ThresholdSettings
from shapes import ShapeForCalibration

import loggers

logger = loggers.LoggerFactory.get_logger(name=__name__)


class ShapesCollector(threading.Thread):
    def __init__(self, results_count: int, detection_result_getter):
        super().__init__()
        self.end_callback = lambda: None
        self.results_count = results_count

        self.fps = 10
        self.results_counter = 0
        self.detection_result_getter = detection_result_getter

        self.landmarks = None
        self.blendshapes = None

        self.index_to_shape_mapping: dict[int, ShapeForCalibration] = {
            i: ShapeForCalibration(i)
            for i in index_to_name_mapping.keys()}

    def run(self):
        while True:
            if self.results_counter >= self.results_count:
                break

            detection_result = self.detection_result_getter()
            self.update(detection_result=detection_result)

            time.sleep(1 / self.fps)

        logger.debug(f'collected results: {self.results_counter}/{self.results_count}')
        self.results_counter = 0
        self.end_callback()

    def update(self, detection_result: FaceLandmarkerResult):
        self.blendshapes = detection_result.face_blendshapes[0]
        self.landmarks = detection_result.face_landmarks

        for i in self.index_to_shape_mapping:
            self.index_to_shape_mapping[i].update(blendshapes=self.blendshapes)

        self.results_counter += 1

    def set_end_callback(self, callback):
        self.end_callback = callback

    def get_result(self) -> dict[int, ShapeForCalibration]:
        return self.index_to_shape_mapping


class StepSelection:
    def __init__(self):
        self.result = None
        self.process_status = 'None process status'

    def get_instructions(self):
        raise NotImplementedError()

    def process(self):
        raise NotImplementedError()

    def get_result(self):
        return self.result


class ThresholdRatioValues(float, enum.Enum):
    narrow = 0.1
    medium = 0.2
    wide = 0.3


class AnalyticsStep(StepSelection):
    instructions: str = 'Analytics'

    def get_instructions(self):
        return self.instructions

    def __init__(self):
        super().__init__()
        self.diff_threshold = 0.25
        self.collector = None
        self.process_status = ''
        self.previous_mapping: dict[int, ShapeForCalibration] = dict()

    def set_collector(self, collector: ShapesCollector):
        self.collector = collector

    def process_mapping(self, mapping: dict[int, ShapeForCalibration]):
        result: dict[str, float] = {}

        if not self.previous_mapping:
            logger.info('No previous mapping to process')
            return result

        for i, curr_shape in mapping.items():
            prev_shape = self.previous_mapping[i]

            curr_max = curr_shape.max
            prev_max = prev_shape.max
            diff = abs(curr_max - prev_max)

            current_name = index_to_name_mapping[i]

            if diff >= self.diff_threshold:
                info = f'{current_name}: from {prev_max:0.2f} to {curr_max:0.2f} -> {diff:0.1%}'
                logger.info(info)

                result[current_name] = round(diff, 3)

        result = dict(sorted(
            result.items(),
            key=lambda item: -item[1]))

        return result

    def end_process(self, collector: ShapesCollector):
        logger.info(f'{self.__class__.__name__}: done')

        mapping = collector.get_result()
        result = self.process_mapping(mapping=mapping)

        logger.info(result)
        self.previous_mapping = mapping
        self.result = result

    def process(self):
        logger.info(f'{self.__class__.__name__}: starting')

        self.collector.set_end_callback(
            callback=lambda: self.end_process(collector=self.collector))

        self.collector.start()


class CalibrationStep(StepSelection):
    instructions: str = 'instructions'
    index_to_threshold_name_mapping = {}
    ratio = ThresholdRatioValues.medium.value
    acceptable_percent_diff = 0.10
    do_asymmetry_check = False

    def __init__(self):
        super().__init__()
        self.collector = None
        self.process_status = 'not completed'

    def get_instructions(self):
        return self.instructions

    def set_collector(self, collector: ShapesCollector):
        self.collector = collector

    def process_mapping(self, mapping: dict[int, ShapeForCalibration]):
        result: dict[str, ThresholdSettings] = dict()

        for i, threshold_name in self.index_to_threshold_name_mapping.items():
            shape = mapping[i]

            low = shape.max * (1.0 - self.ratio)
            high = shape.max * 0.95

            result[threshold_name] = ThresholdSettings(
                high=round(high, 6),
                low=round(low, 6)
            )

        return result

    def end_process(self, collector: ShapesCollector):
        self.process_status = 'completed'
        logger.info(f'{self.__class__.__name__}: done')

        mapping = collector.get_result()
        result = self.process_mapping(mapping=mapping)

        logger.info(result)
        self.result = result

        if self.do_asymmetry_check:
            self.check_asymmetry()

    def process(self):
        self.process_status = 'running'
        logger.info(f'{self.__class__.__name__}: starting')

        self.collector.set_end_callback(
            callback=lambda: self.end_process(collector=self.collector))

        self.collector.start()

    def check_asymmetry(self):
        if len(self.result) != 2:
            return

        threshold_settings = list(self.result.values())

        first = threshold_settings[0]
        second = threshold_settings[1]

        percent_diff = second.percent_diff(other=first)
        if percent_diff > self.acceptable_percent_diff:
            msg = f'Asymmetry difference more than acceptable: {percent_diff:0.1%}'
            logger.warning(msg)


class BrowUpStep(CalibrationStep):
    instructions = 'BROWS UP'
    ratio = ThresholdRatioValues.wide.value
    do_asymmetry_check = True

    index_to_threshold_name_mapping = {
        BrowIndexMapping.left_brow_outer_up: BrowThresholdsNames.left_common,
        BrowIndexMapping.right_brow_outer_up: BrowThresholdsNames.right_common,
    }


class BlinkLeftEyelidStep(CalibrationStep):
    instructions = 'BLINKING LEFT'
    ratio = ThresholdRatioValues.medium.value

    index_to_threshold_name_mapping = {
        EyelidIndexMapping.left_eyelid_blink: EyelidThresholdsNames.left_blink,
    }


class BlinkRightEyelidStep(CalibrationStep):
    instructions = 'BLINKING RIGHT'
    ratio = ThresholdRatioValues.medium.value

    index_to_threshold_name_mapping = {
        EyelidIndexMapping.right_eyelid_blink: EyelidThresholdsNames.right_blink,
    }


class OpenedFullEyelidStep(CalibrationStep):
    instructions = 'EYES WIDE OPENED'
    ratio = ThresholdRatioValues.wide.value
    do_asymmetry_check = True

    index_to_threshold_name_mapping = {
        EyelidIndexMapping.left_eyelid_wide: EyelidThresholdsNames.left_wide,
        EyelidIndexMapping.right_eyelid_wide: EyelidThresholdsNames.right_wide,
    }


class SquintEyelidStep(CalibrationStep):
    instructions = 'SQUINT'
    ratio = ThresholdRatioValues.narrow.value
    do_asymmetry_check = True

    index_to_threshold_name_mapping = {
        EyelidIndexMapping.left_eyelid_squint: EyelidThresholdsNames.left_squint,
        EyelidIndexMapping.right_eyelid_squint: EyelidThresholdsNames.right_squint,
    }


class GazeUpStep(CalibrationStep):
    instructions = 'GAZE UP'
    ratio = ThresholdRatioValues.medium.value
    do_asymmetry_check = True

    index_to_threshold_name_mapping = {
        GazeIndexMapping.left_look_up: GazeThresholdsNames.left_look_up,
        GazeIndexMapping.right_look_up: GazeThresholdsNames.right_look_up,
    }


class GazeDownStep(CalibrationStep):
    instructions = 'GAZE DOWN'
    ratio = ThresholdRatioValues.medium.value
    do_asymmetry_check = True

    index_to_threshold_name_mapping = {
        GazeIndexMapping.left_look_down: GazeThresholdsNames.left_look_down,
        GazeIndexMapping.right_look_down: GazeThresholdsNames.right_look_down,
    }


class GazeLeftStep(CalibrationStep):
    instructions = 'GAZE LEFT'
    ratio = ThresholdRatioValues.medium.value

    index_to_threshold_name_mapping = {
        GazeIndexMapping.left_look_out: GazeThresholdsNames.left_look_out,
        GazeIndexMapping.right_look_in: GazeThresholdsNames.right_look_in,
    }


class GazeRightStep(CalibrationStep):
    instructions = 'GAZE RIGHT'
    ratio = ThresholdRatioValues.medium.value

    index_to_threshold_name_mapping = {
        GazeIndexMapping.left_look_in: GazeThresholdsNames.left_look_in,
        GazeIndexMapping.right_look_out: GazeThresholdsNames.right_look_out,
    }


class MouthOpenedStep(CalibrationStep):
    instructions = 'MOUTH OPENED (speech case)'
    ratio = ThresholdRatioValues.narrow.value

    index_to_threshold_name_mapping = {
        MouthIndexMapping.jaw_open: MouthThresholdsNames.open,
        MouthIndexMapping.mouth_pucker: MouthThresholdsNames.pucker,
    }


class MouthSmileStep(CalibrationStep):
    instructions = 'SMILE (mouth closed)'
    ratio = ThresholdRatioValues.narrow.value
    do_asymmetry_check = True

    index_to_threshold_name_mapping = {
        MouthIndexMapping.smile_left: MouthThresholdsNames.smile_left,
        MouthIndexMapping.smile_right: MouthThresholdsNames.smile_right,
    }


class SaveSettingsStepSelection(StepSelection):
    def __init__(self, calibration_steps: list[CalibrationStep]):
        super().__init__()
        self.calibration_steps: list[CalibrationStep] = calibration_steps
        self.process_status = 'not processed'

    def get_instructions(self):
        return 'Save settings'

    def process(self):
        results_list = [x.get_result() for x in self.calibration_steps]

        mapping: dict[str, ThresholdSettings] = {}
        for results in results_list:
            if results is None:
                continue

            for name, item in results.items():
                mapping[name] = item

        logger.info(f'Collected {len(mapping)} thresholds to save')

        self.process_status = 'processed'
        self.result = mapping


class Calibrator:
    def __init__(self, settings_setter):
        self.settings_setter = settings_setter

        self.calibration_results: dict[str, ThresholdSettings] | None = None
        self.results_count = 10

        self.analytic_step = AnalyticsStep()

        self.calibration_steps: list[CalibrationStep] = [
            BrowUpStep(),
            BlinkLeftEyelidStep(),
            BlinkRightEyelidStep(),
            OpenedFullEyelidStep(),
            SquintEyelidStep(),
            GazeUpStep(),
            GazeDownStep(),
            GazeLeftStep(),
            GazeRightStep(),
            MouthOpenedStep(),
            MouthSmileStep()
        ]

        self.save_settings_step = SaveSettingsStepSelection(
            calibration_steps=self.calibration_steps)

        self.steps: list[StepSelection] = (
                [self.analytic_step] +
                self.calibration_steps +
                [self.save_settings_step]
        )

        self.start = 0
        self.stop = len(self.steps) - 1

        self.i = self.start
        self._total_items = len(self.steps)

    def get_step_instructions(self):
        return self.current().get_instructions()

    def process_current(self, detection_result_getter):
        current_step = self.current()

        if isinstance(current_step, AnalyticsStep):
            collector = ShapesCollector(
                results_count=self.results_count,
                detection_result_getter=detection_result_getter
            )

            current_step.set_collector(collector=collector)

        if isinstance(current_step, CalibrationStep):
            collector = ShapesCollector(
                results_count=self.results_count,
                detection_result_getter=detection_result_getter
            )
            current_step.set_collector(collector=collector)

        current_step.process()

        if isinstance(current_step, SaveSettingsStepSelection):
            calibration_results = current_step.get_result()
            self.settings_setter(calibration_results)

    def current(self):
        return self.steps[self.i]

    @property
    def step_number(self):
        return self.i + 1

    @property
    def total_items(self):
        return self._total_items

    def next(self):
        self.i += 1

        if self.i >= self.stop:
            self.i = self.stop

        return self.steps[self.i]

    def prev(self):
        self.i -= 1

        if self.i <= self.start:
            self.i = self.start

        return self.steps[self.i]

    def get_process_status(self):
        return self.current().process_status
