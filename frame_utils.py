import cv2
import numpy as np

import loggers

logger = loggers.LoggerFactory.get_logger(name=__name__)


def get_landmarks_coordinates(landmarks, frame_width, frame_height):
    """Конвертирует нормализованные координаты в пиксельные"""
    result = []
    for landmark in landmarks:
        x = int(landmark.x * frame_width)
        y = int(landmark.y * frame_height)
        z = landmark.z
        result.append((x, y, z))
    return result


def pad_frame_to_resolution(frame, target_w, target_h,
                            position='center',
                            background_color=None):
    # Get original dimensions
    if len(frame.shape) == 2:
        h, w = frame.shape
        channels = 1
    else:
        h, w, channels = frame.shape

    # Автоматический подбор background_color
    if background_color is None:
        if channels == 1:
            background_color = 0
        elif channels == 3:
            background_color = (0, 0, 0)  # BGR black
        elif channels == 4:
            background_color = (0, 0, 0, 255)  # BGRA black (fully opaque)
        else:
            background_color = 0
    elif len(background_color) == 3 and channels == 4:
        # Если передан BGR, но каналов 4 — добавляем alpha=255
        background_color = (*background_color, 255)

    # Guard clause
    if target_h < h or target_w < w:
        raise ValueError(
            f"Cannot pad to smaller resolution. "
            f"Target: {target_w}x{target_h}, Original: {h}x{w}. "
            f"Consider using cv2.resize() first if downscaling is needed."
        )

    # Create background canvas
    if channels == 1:
        padded = np.full((target_h, target_w), background_color, dtype=frame.dtype)
    else:
        padded = np.full((target_h, target_w, channels), background_color, dtype=frame.dtype)

    # Calculate position offsets
    if position == 'center':
        y_offset = (target_h - h) // 2
        x_offset = (target_w - w) // 2
    elif position == 'top-left':
        y_offset, x_offset = 0, 0
    elif position == 'top-right':
        y_offset = 0
        x_offset = target_w - w
    elif position == 'bottom-left':
        y_offset = target_h - h
        x_offset = 0
    elif position == 'bottom-right':
        y_offset = target_h - h
        x_offset = target_w - w
    else:
        raise ValueError(f"Unknown position: {position}")

    # Place original frame onto padded canvas
    padded[y_offset:y_offset + h, x_offset:x_offset + w] = frame

    return padded


def combine_frames(frame1, frame2, direction='vertical'):
    """
    Combine two results_count either horizontally or vertically.

    Args:
        frame1: first frame (H, W, 3)
        frame2: second frame (H, W, 3)
        direction: 'horizontal' (left-right) or 'vertical' (top-bottom)

    Returns:
        Combined frame
    """
    if direction == 'horizontal':
        # Приводим к одинаковой высоте
        h1, w1 = frame1.shape[:2]
        h2, w2 = frame2.shape[:2]

        if h1 != h2:
            frame2 = cv2.resize(frame2, (w2, h1))

        return np.hstack((frame1, frame2))

    elif direction == 'vertical':
        # Приводим к одинаковой ширине
        h1, w1 = frame1.shape[:2]
        h2, w2 = frame2.shape[:2]

        if w1 != w2:
            frame2 = cv2.resize(frame2, (w1, h2))

        return np.vstack((frame1, frame2))

    else:
        raise ValueError("direction must be 'horizontal' or 'vertical'")


def combine_frames_old(left_frame, right_frame):
    """
    Combine two results_count side-by-side horizontaly.

    Args:
        left_frame: first frame (H, W, 3)
        right_frame: second frame (H, W, 3)

    Returns:
        Combined frame (H, W*2, 3)
    """
    f_right_h, f_right_w = left_frame.shape[:2]
    f_left_h, f_left_w = right_frame.shape[:2]

    if f_right_h != f_left_h:
        # Resize to match heights (preserve aspect low)
        right_frame = cv2.resize(right_frame, (f_left_w, f_right_h))

    # Concatenate horizontally
    combined = np.hstack((left_frame, right_frame))
    return combined


def resize_image(image: np.ndarray, width: int, height: int) -> np.ndarray:
    if image.shape[1] == width and image.shape[0] == height:
        return image

    return cv2.resize(image, (width, height), interpolation=cv2.INTER_NEAREST)


def _ensure_4channels(img: np.ndarray) -> np.ndarray:
    """Быстрое приведение к 4 каналам (BGRA)"""
    if img.shape[2] == 4:
        return img

    logger.warning('Non optimal conversion to 4 channels! It can slowdown image processing')

    if img.ndim == 2:
        # Grayscale -> BGRA
        return cv2.cvtColor(img, cv2.COLOR_GRAY2BGRA)

    if img.shape[2] == 3:
        # BGR -> BGRA
        return cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)

    raise ValueError(f"Invalid number of channels: {img.shape[2]}")


def _match_sizes(bg: np.ndarray, fg: np.ndarray) -> tuple:
    """Приводит изображения к одинаковому размеру (оптимизированно)"""
    h_bg, w_bg = bg.shape[:2]
    h_fg, w_fg = fg.shape[:2]

    if h_bg == h_fg and w_bg == w_fg:
        return bg, fg

    # Определяем максимальные размеры
    h = max(h_bg, h_fg)
    w = max(w_bg, w_fg)

    # Создаем только если нужно
    if h_bg != h or w_bg != w:
        new_bg = np.zeros((h, w, 4), dtype=np.uint8)
        new_bg[:h_bg, :w_bg] = bg
        bg = new_bg

    if h_fg != h or w_fg != w:
        new_fg = np.zeros((h, w, 4), dtype=np.uint8)
        new_fg[:h_fg, :w_fg] = fg
        fg = new_fg

    return bg, fg


def overlay(background: np.ndarray, foreground: np.ndarray) -> np.ndarray:
    # Приводим к 4 каналам (только если нужно)
    fg = _ensure_4channels(foreground)
    bg = _ensure_4channels(background)

    # Приводим размеры (только если нужно)
    if bg.shape[:2] != fg.shape[:2]:
        bg, fg = _match_sizes(bg, fg)

    # === Наложение RGB ===
    # Используем broadcasting: alpha[:, :, np.newaxis] автоматически расширяется до (H, W, 3)
    alpha = fg[:, :, 3:4].astype(np.float32) * (1.0 / 255.0)  # (H, W, 1)

    # Инвертированная альфа
    inv_alpha = 1.0 - alpha  # (H, W, 1)

    # Смешивание одной формулой через broadcasting
    # bg_rgb * (1 - alpha) + fg_rgb * alpha
    # Результат сразу в uint8 через .astype
    result_rgb = (
            bg[:, :, :3].astype(np.float32) * inv_alpha +
            fg[:, :, :3].astype(np.float32) * alpha
    ).astype(np.uint8)

    # === Альфа-канал ===
    # Сложение с насыщением через np.minimum (быстрее чем clip)
    result_alpha = np.minimum(
        bg[:, :, 3].astype(np.uint16) + fg[:, :, 3].astype(np.uint16),
        255
    ).astype(np.uint8)

    # === Сборка результата ===
    # np.concatenate быстрее cv2.merge
    return np.concatenate([
        result_rgb,
        result_alpha[:, :, np.newaxis]
    ], axis=2)
