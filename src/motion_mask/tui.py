import asyncio
import enum

from prompt_toolkit.application import Application
from prompt_toolkit.application import get_app
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding.bindings.focus import (
    focus_next,
    focus_previous)
from prompt_toolkit.layout import (
    Dimension, Float,
    FloatContainer,
    HSplit,
    Layout)
from prompt_toolkit.layout import (
    FormattedTextControl,
    VSplit,
    Window)
from prompt_toolkit.output import ColorDepth
from prompt_toolkit.styles import (
    AdjustBrightnessStyleTransformation,
    Style)
from prompt_toolkit.widgets import (
    Box,
    Button,
    Dialog,
    RadioList)
from prompt_toolkit.widgets import Frame

from motion_mask import loggers
from motion_mask.launch_settings import (
    LaunchSettings, SettingName)

logger = loggers.LoggerFactory.get_logger(name=__name__)


class LaunchResult(enum.StrEnum):
    exit = 'exit'
    save = 'save'


class ButtonWithText:
    def __init__(self,
                 name: str,
                 initial_text="",
                 handler=None,
                 button_width: int = 16):
        self.name = name

        self.button = Button(
            name,
            handler=handler,
            left_symbol='[',
            right_symbol=']',
            width=button_width
        )

        padding = Window(
            content=FormattedTextControl(text=""),
            height=1,
            width=2,
        )

        self.text_control = FormattedTextControl(
            text="",
        )

        self.text_window = Window(
            content=self.text_control,
            height=1,
        )

        self.container = VSplit([
            self.button,
            padding,
            self.text_window,
        ])

        self.set_text(new_text=initial_text)

    def __pt_container__(self):
        # Ключевой момент: возвращаем внутренний контейнер
        return self.container

    # Предоставляем удобный метод для обновления текста
    def set_text(self, new_text):
        self.text_control.text = new_text

    def set_handler(self, handler):
        self.button.handler = handler


class ListSelection:
    def __init__(self, name: str, items: list[tuple[str, str]] | None = None):
        self.name = name
        self.max_width = 64
        self.items = items or [("no value", "no value")]
        self.selected_item: str | None = None
        self.future: asyncio.Future | None = None

    def create_dialog(self) -> Dialog:
        if self.future is None:
            raise RuntimeError("ListSelection.create_dialog() called before show()")

        radio_list = RadioList(
            values=self.items,
            select_on_focus=True,
            open_character="[",
            select_character="*",
            close_character="]",
        )

        def _select_handler():
            self.selected_item = radio_list.current_value
            if not self.future.done():
                self.future.set_result(self.selected_item)

        def _cancel_handler():
            self.selected_item = None
            if not self.future.done():
                self.future.set_result(None)

        buttons = [
            Button(text="Select",
                   handler=_select_handler,
                   left_symbol='[',
                   right_symbol=']',
                   width=10),
            Button(text="Cancel",
                   handler=_cancel_handler,
                   left_symbol='[',
                   right_symbol=']',
                   width=10),
        ]

        return Dialog(
            modal=True,
            title="Selection",
            body=radio_list,
            width=self.max_width,
            buttons=buttons,
        )

    async def show(self) -> str | None:
        self.future = asyncio.get_running_loop().create_future()
        self.create_dialog()


class Tui:
    max_width: int = 64

    def __init__(self, launch_settings: LaunchSettings):
        self._launch_settings = launch_settings

        self.bindings: KeyBindings | None = None
        self._init_bindings()

        self.style: Style | None = None
        self._init_style()

        self.app: Application | None = None
        self.menu_items: list[ButtonWithText] | None = None
        self._build_tui()

        self._reflect_settings_to_ui()

    def _init_bindings(self):
        bindings = KeyBindings()

        bindings.add('tab')(focus_next)
        bindings.add('down')(focus_next)
        bindings.add('s-tab')(focus_previous)
        bindings.add('up')(focus_previous)

        self.bindings = bindings

    def _init_style(self):
        self.style = None

    def create_main_menu_items(self) -> list[Button]:

        names = [
            SettingName.mode,
            SettingName.camera,
            SettingName.virtual_camera,
            SettingName.avatar_name,
        ]

        button_width = 4 + max([len(str(n)) for n in names])

        selection_buttons = [self.create_button_with_text(name=name, button_width=button_width)
                             for name in names]

        self.menu_items = selection_buttons

        buttons_with_text = [
            ButtonWithText(name='Quit',
                           initial_text='',
                           handler=lambda: self.quit(),
                           button_width=button_width),

            *selection_buttons,

            ButtonWithText(name='Save',
                           initial_text='',
                           handler=lambda: self.save(),
                           button_width=button_width),
        ]

        return buttons_with_text

    def _build_tui(self):
        main_menu_items = self.create_main_menu_items()

        content_container = HSplit(main_menu_items)

        inner_layout = Frame(
            Box(
                content_container,
                padding_left=1,
                padding_right=1,
                padding_bottom=0,
                padding_top=0,
                width=Dimension(preferred=self.max_width, max=self.max_width)
            ),
            title='Launch settings editor',
            width=Dimension(preferred=self.max_width, max=self.max_width),
        )

        limited_layout = VSplit([
            inner_layout,
        ], width=Dimension(preferred=self.max_width, max=self.max_width))

        self.float_container = FloatContainer(
            content=limited_layout,
            floats=[],
        )

        layout = Layout(self.float_container)

        self.app = Application(
            layout=layout,
            key_bindings=self.bindings,
            style=self.style,
            full_screen=True,
            color_depth=ColorDepth.DEPTH_1_BIT,
            style_transformation=AdjustBrightnessStyleTransformation(
                min_brightness=0.5,
                max_brightness=1.0,
            )
        )

    def show_list_selection(self,
                            list_selection: ListSelection,
                            button_with_text: ButtonWithText):
        loop = asyncio.get_running_loop()
        list_selection.future = loop.create_future()

        dialog = list_selection.create_dialog()
        float_ = Float(content=dialog, top=2, left=2)

        self.float_container.floats.insert(0, float_)

        app = get_app()
        focused_before = app.layout.current_window
        app.layout.focus(dialog)

        async def wait_and_cleanup():
            try:
                result = await list_selection.future
            finally:
                if float_ in self.float_container.floats:
                    self.float_container.floats.remove(float_)

                app.layout.focus(focused_before)

            if result is not None:
                r = str(result)
                n = SettingName(button_with_text.name)

                button_with_text.set_text(new_text=r)
                self._launch_settings.set_current_choice(
                    name=n,
                    new_value=r
                )

            return result

        return asyncio.create_task(wait_and_cleanup())

    def launch(self):
        try:
            return self.app.run()
        except Exception as e:
            logger.error(f'Something goes wrong with tui: {e}')

    def quit(self):
        self.app.exit(result=LaunchResult.exit)

    def save(self):
        self.app.exit(result=LaunchResult.save)

    def _reflect_settings_to_ui(self):
        settings_dict = self._launch_settings.to_dict()

        for mi in self.menu_items:
            value = settings_dict.get(SettingName(mi.name))

            if value:
                mi.set_text(new_text=value)

    def create_button_with_text(self, name: str, button_width: int):
        bwt = ButtonWithText(name=name,
                             initial_text='-',
                             button_width=button_width)

        choices = self._launch_settings.get_available_choices(
            name=SettingName(name))

        bwt.set_handler(
            handler=lambda: self.show_list_selection(
                ListSelection(
                    name=name,
                    items=choices),
                button_with_text=bwt))

        return bwt

    def get_updated_launch_settings(self) -> LaunchSettings:
        return self._launch_settings
