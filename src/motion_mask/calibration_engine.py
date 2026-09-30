import textwrap
import time

import cv2
import numpy as np
from mediapipe import Image, ImageFormat
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

import frame_utils as fu
from calibration import logger, Calibrator
from capture import CaptureWrap
from settings_manager import SettingsManager


class CalibrationEngine(SettingsManager):
    default_front_color = (239, 239, 239)
    default_points_color = (127, 127, 127)
    default_fill_value = 16

    def __init__(self, model_path: str):
        super().__init__()

        self.results_count_default = 30
        self.model_path = model_path

        self.win_name = 'Capture'
        self.cap_width = 640
        self.cap_height = 360

        self.frame_width = 640
        self.frame_height = 360
        self.info_frame_back = np.full(
            (self.frame_height, self.frame_width, 4),
            self.default_fill_value,
            dtype=np.uint8)

        base_options = python.BaseOptions(model_asset_path=model_path)

        options = vision.FaceLandmarkerOptions(
            base_options=base_options,
            output_face_blendshapes=True,
            output_facial_transformation_matrixes=True,
            num_faces=1,
            min_face_detection_confidence=0.5,
            min_tracking_confidence=0.5,
            running_mode=vision.RunningMode.IMAGE,
        )

        self.face_landmarker = vision.FaceLandmarker.create_from_options(options)

        self.capture_number = 0

    def set_thresholds_mapping(self, mapping):
        self.update_thresholds_mapping(mapping=mapping)
        self.save_settings()

    def _launch(self):
        logger.info("Calibration mode")

        self.capture_wrap = CaptureWrap(number=self.capture_number,
                                        width=self.cap_width,
                                        height=self.cap_height)
        self.capture_wrap.start()

        calibrator = Calibrator(settings_setter=lambda x: self.set_thresholds_mapping(x))

        while True:
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break

            raw_frame = self.capture_wrap.get_frame()
            resized_frame = cv2.resize(
                raw_frame, (self.cap_width, self.cap_height))
            rgb_frame = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)

            mp_image = Image(image_format=ImageFormat.SRGB,
                             data=rgb_frame)

            detection_result = self.face_landmarker.detect(
                image=mp_image)

            if not detection_result.face_landmarks:
                logger.debug('No face detected!')
                time.sleep(0.25)
                continue

            if key == ord('a'):
                calibrator.prev()
            elif key == ord('s'):
                calibrator.next()
            elif key == ord('d'):
                calibrator.process_current(detection_result_getter=lambda: detection_result)

            info_lines = [
                'q -- quit',
                'a -- prev',
                's -- next',
                'd -- process',
            ]

            step_number_info = f'{calibrator.step_number}/{calibrator.total_items}'
            text_lines = [
                f'Step ({step_number_info}): {calibrator.get_step_instructions()}',
                f'{calibrator.get_process_status()}',
            ]

            info_frame = self.create_info_frame(lines=info_lines)
            text_frame = self.create_info_frame(lines=text_lines)

            self.add_points_to_frame(detection_result=detection_result,
                                     frame=info_frame)

            first_frame = fu.pad_frame_to_resolution(
                frame=info_frame,
                target_w=self.frame_width,
                target_h=self.frame_height,
            )

            second_frame = fu.pad_frame_to_resolution(
                frame=text_frame,
                target_w=self.frame_width,
                target_h=self.frame_height,
            )

            combined_frame = fu.combine_frames(
                frame1=first_frame,
                frame2=second_frame,
                direction='horizontal'
            )

            cv2.imshow(winname=self.win_name, mat=combined_frame)

        self.quit_routine()

    def quit_routine(self):
        self.capture_wrap.stop()
        self.face_landmarker.close()
        cv2.destroyAllWindows()

        time.sleep(1.5)

    def launch(self):
        try:
            self._launch()
        except Exception as e:
            logger.error('Something goes wrong')
            message = f'{type(e)} : {e}'
            logger.error(message)
            self.quit_routine()
            exit(1)

    def add_points_to_frame(self, detection_result, frame):
        for face_landmarks in detection_result.face_landmarks:
            h, w, _ = frame.shape
            landmarks_px = fu.get_landmarks_coordinates(face_landmarks, w, h)

            # Визуализация ориентиров
            for i, (x, y, z) in enumerate(landmarks_px):
                # Основные ориентиры лица (по аналогии со старым API)
                cv2.circle(frame, (x, y), 1, self.default_points_color, -1)

            return frame

    @staticmethod
    def split_lines(lines: list[str], max_length: int) -> list[str]:
        result = []
        for line in lines:
            result.extend(textwrap.wrap(line, width=max_length))
        return result

    def create_info_frame(self, lines: list[str]):
        lines = self.split_lines(lines=lines, max_length=30)

        frame = self.info_frame_back.copy()
        x0 = 30
        y0 = 30
        line_height = 30

        for i, line in enumerate(lines):
            x = x0
            y = y0 + i * line_height

            cv2.putText(img=frame,
                        text=line,
                        org=(x, y),
                        fontFace=cv2.FONT_HERSHEY_SIMPLEX,
                        fontScale=1.0,
                        color=self.default_front_color,
                        thickness=1)

        return frame
