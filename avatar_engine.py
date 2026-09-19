import time
from pathlib import Path

import cv2
import numpy as np
from mediapipe import Image, ImageFormat
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

import frame_utils as fu
import loggers
from avatar import FaceStates, Avatar, DefaultStatesTransformer
from capture import CaptureWrap
from settings import CommonSettings
from settings_manager import SettingsManager

logger = loggers.LoggerFactory.get_logger(name=__name__)


class AvatarEngine(SettingsManager):
    default_front_color = (0, 239, 0)
    default_points_color = (0, 127, 0)
    default_fill_value = 16

    def __init__(self, model_path: str,
                 avatar_path: str,
                 preview_mode: bool = True,
                 virtual_camera = None):
        super().__init__()

        self.fps = 30

        self.face_states = FaceStates()
        self.sates_transformer = DefaultStatesTransformer()
        self.avatar = Avatar(path_to=Path(avatar_path))

        self.absent_frame = self.avatar.get_absent_frame()

        self.testing_mode = preview_mode

        self.frames_to_drop = 0
        self.model_path = model_path

        self.virtual_camera = virtual_camera

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

        self.apply_settings()
        logger.info("Settings applied")

    def apply_settings(self):
        self.frames_to_drop = self.settings.get(setting=CommonSettings.frames_to_drop)

        thresholds_settings = self.settings.get_thresholds_settings()
        self.face_states.apply_thresholds(settings=thresholds_settings)

    def _launch(self):
        self.virtual_camera.start()

        self.capture_wrap = CaptureWrap(number=self.capture_number,
                                        width=self.cap_width,
                                        height=self.cap_height)
        self.capture_wrap.start()

        frame_drop_counter = 0
        while True:
            if self.testing_mode:
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

            raw_frame = self.capture_wrap.get_frame()

            # Optional frame skipping
            frame_drop_counter += 1
            if frame_drop_counter > self.frames_to_drop:
                frame_drop_counter = 0
            else:
                time.sleep(1 / self.fps)
                continue

            # Resize raw frame before processing
            frame = cv2.resize(raw_frame, (self.cap_width, self.cap_height))
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            mp_image = Image(image_format=ImageFormat.SRGB,
                             data=rgb_frame)

            detection_result = self.face_landmarker.detect(
                image=mp_image)

            if not detection_result.face_landmarks:
                logger.debug('No face detected!')
                self.virtual_camera.set_frame(frame=self.absent_frame)
                time.sleep(0.25)
                continue

            self.face_states.update(detection_result=detection_result)

            current_states = self.face_states.get_all_states()

            refined_states = self.sates_transformer.transform(states=current_states)

            current_filenames = self.face_states.get_all_filenames(
                states=refined_states)

            avatar_frame = self.avatar.rebuild_frame(
                parts_to_filenames_mapping=current_filenames)

            self.virtual_camera.set_frame(frame=avatar_frame)

            if self.testing_mode:
                current_states = self.face_states.get_all_states()
                current_states = [f'{k}: {v}' for k, v in current_states.items()]

                lines = ['q -- quit', ''] + current_states

                info_frame = self.create_info_frame(lines=lines)
                self.add_points_to_frame(detection_result=detection_result,
                                         frame=info_frame)

                first_frame = fu.pad_frame_to_resolution(
                    frame=info_frame,
                    target_w=self.frame_width,
                    target_h=self.frame_height,
                )

                frame_to_show = avatar_frame
                second_frame = fu.pad_frame_to_resolution(
                    frame=frame_to_show,
                    target_w=self.frame_width,
                    target_h=self.frame_height,
                )

                combined_frame = fu.combine_frames(
                    frame1=first_frame,
                    frame2=second_frame,
                    direction='horizontal'
                )

                cv2.imshow(winname=self.win_name, mat=combined_frame)

        logger.info('Exiting by hotkey from cv interface')
        self.graceful_shutdown()

    def graceful_shutdown(self):
        self.capture_wrap.stop()
        self.virtual_camera.stop()
        self.face_landmarker.close()

        if self.testing_mode:
            cv2.destroyAllWindows()

        # Time for all processes ending correctly
        # Otherwise Segfault may occur
        time.sleep(2)

    def launch(self):
        try:
            self._launch()
        except KeyboardInterrupt:
            logger.info('Exiting...')
            self.graceful_shutdown()
            exit(0)
        except Exception as e:
            logger.error('Something goes wrong!')
            logger.error(e)
            exit(1)

    def add_points_to_frame(self, detection_result, frame):
        for face_landmarks in detection_result.face_landmarks:
            h, w, _ = frame.shape
            landmarks_px = fu.get_landmarks_coordinates(face_landmarks, w, h)

            for i, (x, y, z) in enumerate(landmarks_px):
                cv2.circle(frame, (x, y), 1, self.default_points_color, -1)

            return frame

        return None

    def create_info_frame(self, lines: list[str]):
        frame = self.info_frame_back.copy()
        x0 = 30
        y0 = 30
        line_height = 30

        for i, line in enumerate(lines):
            x = x0
            y = y0 + i * line_height

            line = ' ' if line == '' else line
            cv2.putText(img=frame,
                        text=line,
                        org=(x, y),
                        fontFace=cv2.FONT_HERSHEY_SIMPLEX,
                        fontScale=1,
                        color=self.default_front_color,
                        thickness=1)

        return frame
