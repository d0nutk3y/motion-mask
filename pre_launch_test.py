# Dependencies check
try:
    import pyvirtualcam
    import mediapipe as mp

    print('[OK] pyvirtualcam version:', pyvirtualcam.__version__)
    print('[OK] mediapipe version:', mp.__version__)
except Exception as e:
    print('[FAILED] some dependencies import failed')
    print(f'Exception: {e}')

# Virtual camera check
try:
    with pyvirtualcam.Camera(width=1280, height=720, fps=10) as cam:
        print('[OK] virtual cam is avaliable')
except Exception as e:
    print('[FAILED] failed to use virtual camera')
    print(f'Exception: {e}')

