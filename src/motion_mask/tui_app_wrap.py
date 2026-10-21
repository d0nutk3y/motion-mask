import threading

from prompt_toolkit import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import HSplit, Layout, Window
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl

from motion_mask import loggers
from motion_mask.loggers import LoggerFactory, LoggingStreamSwitcher

logger = loggers.LoggerFactory.get_logger(name=__name__)


class LogToUiWidget:
    def __init__(self, append_func):
        self.append_func = append_func

    def write(self, text: str) -> int:
        if text.strip():
            for line in text.splitlines():
                if line.strip():
                    self.append_func(line)
        return len(text)

    def flush(self):
        pass


def tui_app_wrap(thread, exit_request_event: threading.Event):
    logger.debug('Starting app wrap...')
    # Bindings
    kb = KeyBindings()

    @kb.add("escape")
    def _(event):
        thread.stop()

    # Tui build
    hint = 'Press Escape to stop'
    ftc = FormattedTextControl(hint, focusable=True)
    hint_window = Window(content=ftc, height=1, dont_extend_height=True)

    log_buffer = Buffer(read_only=False)
    log_window = Window(
        content=BufferControl(buffer=log_buffer),
        # height=16,
        wrap_lines=True,

    )

    def append_log(line: str):
        log_buffer.text += line + '\n'
        log_buffer.cursor_position = len(log_buffer.text)

    root = HSplit([
        hint_window,
        log_window,
    ])

    layout = Layout(root, focused_element=ftc)

    def check_engine_done():
        if exit_request_event.is_set():
            this_tui.exit()

    this_tui = Application(layout=layout,
                           key_bindings=kb,
                           full_screen=True,
                           refresh_interval=0.5,
                           on_invalidate=lambda app: check_engine_done())

    log_stream = LogToUiWidget(append_log)

    lss = LoggingStreamSwitcher(
        initial_config=LoggerFactory.LOGGING_CONFIG,
        stream=log_stream
    )

    lss.change_stream()

    # Launch
    thread.start()
    try:
        this_tui.run()
    finally:
        thread.stop()
        thread.join()
