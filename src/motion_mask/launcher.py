import sys

import TermTk as ttk
from TermTk import TTkColor

from motion_mask import loggers
from motion_mask.launch_settings import LaunchSettings, SettingName, Choice

logger = loggers.LoggerFactory.get_logger(name=__name__)

MAX_LINES = 10
DEFAULT_POS = (1, 1)


class LayoutFactory:
    def create(self) -> ttk.TTkGridLayout:
        raise NotImplementedError()

    def create_vertical(self) -> ttk.TTkGridLayout:
        raise NotImplementedError()


class DefaultLayoutFactory(LayoutFactory):
    def create(self) -> ttk.TTkGridLayout:
        return ttk.TTkGridLayout(
            columnMinWidth=10,
            rowMinHeight=10,
            minWidth=5,
            maxWidth=70,
            maxHeight=20,
        )

    def create_vertical(self) -> ttk.TTkGridLayout:
        return ttk.TTkVBoxLayout(
            columnMinWidth=10,
            rowMinHeight=10,
            minWidth=5,
            maxWidth=70,
            maxHeight=20,
        )


class C:
    FG_RED = TTkColor.fg('#D81E00')
    FG_GREEN = TTkColor.fg('#5EA702')
    FG_YELLOW = TTkColor.fg('#CFAE00')
    FG_BLUE = TTkColor.fg('#427AB3')
    FG_TEAL = TTkColor.fg('#00A7AA')
    FG_SILVER = TTkColor.fg('#C1C4BE')
    FG_DIM_GRAY = TTkColor.fg('#686a66')
    FG_BLACK = TTkColor.fg("#111111")

    BG_RED = TTkColor.bg('#D81E00')
    BG_GREEN = TTkColor.bg('#5EA702')
    BG_YELLOW = TTkColor.bg('#CFAE00')
    BG_BLUE = TTkColor.bg('#427AB3')
    BG_TEAL = TTkColor.bg('#00A7AA')
    BG_SILVER = TTkColor.bg('#C1C4BE')
    BG_DIM_GRAY = TTkColor.bg('#686a66')
    BG_BLACK = TTkColor.bg("#111111")

    NORMAL_FG = FG_SILVER
    NORMAL_BG = BG_BLACK
    NORMAL_PAIR = NORMAL_FG + NORMAL_BG

    HIGHLIGHTED_FG = FG_BLACK
    HIGHLIGHTED_BG = BG_SILVER
    HIGHLIGHTED_PAIR = HIGHLIGHTED_FG + HIGHLIGHTED_BG + TTkColor.BOLD

    SELECTED_FG = FG_GREEN
    SELECTED_BG = BG_BLACK
    SELECTED_PAIR = SELECTED_FG + SELECTED_BG + TTkColor.BOLD

    DISABLED_FG = FG_DIM_GRAY
    DISABLED_BG = BG_BLACK
    DISABLED_PAIR = DISABLED_FG + DISABLED_BG

    BORDERS = FG_DIM_GRAY + BG_BLACK

    WHITE_FG = TTkColor.fg("#ffffff")
    WHITE_BG = TTkColor.bg("#ffffff")


class Stylable(ttk.TTkFrame):
    layout_factory: LayoutFactory

    STYLE = {
        'default': {'color': C.NORMAL_PAIR,
                    'fillColor': C.FG_BLACK,
                    'borderColor': C.BORDERS},
        'disabled': {'color': C.FG_SILVER,
                     'fillColor': C.FG_BLACK,
                     'borderColor': C.BORDERS}
    }

    LIST_STYLE = {'default': {
        'color': C.NORMAL_PAIR,
        'selected': C.SELECTED_PAIR,
        'highlighted': C.HIGHLIGHTED_PAIR,
        # ???
        'hovered': C.HIGHLIGHTED_PAIR,
        'searchColor': C.FG_BLUE + C.BG_BLACK,
    }}

    BUTTON_STYLE = {
        'default': {'color': C.NORMAL_PAIR,
                    'borderColor': C.BORDERS,
                    'grid': 1},
        'disabled': {'color': C.DISABLED_PAIR,
                     'borderColor': C.BORDERS,
                     'grid': 0},
        'hover': {'color': C.HIGHLIGHTED_PAIR,
                  'borderColor': C.BORDERS + TTkColor.BOLD,
                  'grid': 1},
        'checked': {'color': C.SELECTED_PAIR,
                    'borderColor': C.BORDERS + TTkColor.BOLD,
                    'grid': 0},
        'unchecked': {'color': C.DISABLED_PAIR,
                      'borderColor': TTkColor.BOLD,
                      'grid': 3},
        'clicked': {'color': C.SELECTED_PAIR,
                    'borderColor': C.BORDERS + TTkColor.BOLD,
                    'grid': 0},
        'focus': {'color': C.HIGHLIGHTED_PAIR,
                  'borderColor': C.BORDERS + TTkColor.BOLD,
                  'grid': 1},
    }

    def __init__(self, **kwargs):
        super().__init__(addStyle=self.STYLE, **kwargs)

        self.layout_factory = DefaultLayoutFactory()

    def create_blank_label(self, text: str) -> ttk.TTkLabel:
        label = ttk.TTkLabel(
            parent=self,
            text=text,
            style=self.STYLE,
        )

        return label


class MenuItem(Stylable):
    button: ttk.TTkButton
    value_label: ttk.TTkLabel
    hint_text_label: ttk.TTkLabel

    def __init__(self, parent, button_text: str, **kwargs):
        super().__init__(parent=parent, **kwargs)
        self.parent: MainWindow = parent

        self.setBorder(False)
        self.setFocusPolicy(policy=ttk.TTkK.FocusPolicy.ParentFocus)

        layout = self.layout_factory.create()

        self.setLayout(layout=layout)

        self.button = ttk.TTkButton(
            parent=self,
            text=button_text,
            style=self.BUTTON_STYLE,
            minWidth=9,
            maxWidth=18,
        )

        self.button.clicked.connect(self.do_action)

        layout.addWidget(widget=self.button, row=0, col=0)

        spacer_label = ttk.TTkLabel(
            parent=self,
            text="   ",
            minWidth=3,
            maxWidth=3,
            style=self.STYLE,
        )

        layout.addWidget(widget=spacer_label, row=0, col=1)

        self.value_label = ttk.TTkLabel(
            parent=self,
            text='',
            style=self.STYLE,
        )
        layout.addWidget(widget=self.value_label, row=0, col=2)

    def do_action(self):
        self.parent.last_widget = self.button
        self._do_action()

    def _do_action(self):
        raise NotImplementedError()

    def set_value_label_text(self, text: str):
        self.value_label.setText(text=text)

    def update_label_text_from_selected(self):
        raise NotImplementedError()


class QuitMenuItem(MenuItem):
    def __init__(self, parent,
                 button_text: str = 'Quit',

                 **kwargs):
        super().__init__(parent, button_text, **kwargs)

    def _do_action(self):
        ttk.TTkHelper.quit()
        sys.exit(0)

    def update_label_text_from_selected(self):
        pass


class LaunchMenuItem(MenuItem):
    def __init__(self, parent,
                 button_text: str = 'Launch',
                 **kwargs):
        super().__init__(parent, button_text, **kwargs)

    def _do_action(self):
        self.save_settings()
        ttk.TTkHelper.quit()

    def update_label_text_from_selected(self):
        pass

    def save_settings(self):
        pass


class ListSelectWindow(Stylable):
    def __init__(self,
                 items: list[Choice],
                 parent_to_swap: 'MainWindow',
                 root,
                 **kwargs):
        self.callback = lambda: None
        self.items = items
        self.parent_to_swap = parent_to_swap
        self.root = root

        super().__init__(parent=self.root, title="", **kwargs)
        self.hide()

        layout = self.layout_factory.create_vertical()
        self.setLayout(layout)

        max_height = 2 + len(self.items)

        if max_height < MAX_LINES:
            self.setMaximumHeight(maxh=max_height)

        self._selected_item: ttk.TTkListItem | None = None

        self.list_view = ttk.TTkListWidget(parent=self,
                                           style=self.LIST_STYLE,
                                           showSearch=True,
                                           )

        for item in self.items:
            self.list_view.addItem(
                ttk.TTkListItem(
                    text=item.label, data=item.value))

        self.list_view.textClicked.connect(self._on_item_selected)

    def show_instead(self):
        self.parent_to_swap.hide()
        self.list_view.setFocus()
        self.show()

    def show_back(self):
        self.hide()
        self.callback()
        self.parent_to_swap.last_widget.setFocus()
        self.parent_to_swap.show()

    def _on_item_selected(self):
        items = self.list_view.selectedItems()

        if items:
            self._selected_item = items[0]

        self.show_back()

    @property
    def selected_item(self) -> ttk.TTkListItem:
        return self._selected_item

    def set_callback(self, callback):
        self.callback = callback


class OptionSelectionMenuItem(MenuItem):
    def __init__(self, parent,
                 list_window: ListSelectWindow,
                 option_name,
                 button_text: str = 'button',
                 **kwargs):
        super().__init__(parent, button_text, **kwargs)
        self.option_name = option_name
        self.list_window = list_window

    def _do_action(self):
        self.list_window.set_callback(self.update_label_text_from_selected)
        self.list_window.show_instead()

    def update_label_text_from_selected(self):
        item: ttk.TTkListItem = self.list_window.selected_item
        new_label_value = item.text()

        self.set_value_label_text(text=str(new_label_value))

    def get_current_name_value_pair(self):
        name = self.option_name

        if not self.list_window.selected_item is None:
            value = self.list_window.selected_item.data()
        else:
            value = None

        return name, value


class MainWindow(Stylable):
    def __init__(self,
                 launch_settings: LaunchSettings,
                 parent,
                 **kwargs):
        super().__init__(parent=parent, **kwargs)
        self.launch_settings = launch_settings
        self.root = parent

        self.grid = self.layout_factory.create()
        self.setLayout(self.grid)

        self.quit_mi = QuitMenuItem(parent=self)
        self.launch_mi = LaunchMenuItem(parent=self)

        self.last_widget = self.launch_mi

        setting_names = [
            SettingName.mode,
            SettingName.camera,
            SettingName.virtual_camera,
            SettingName.avatar_name,
        ]

        self.option_selection_mi_list = [self.create_option_selection_mi(name=n)
                                         for n in setting_names]

        padding_mi_list = [self.create_blank_label(text="") for _ in range(10)]

        self.menu_items = [
            self.quit_mi,
            *self.option_selection_mi_list,
            self.launch_mi,
            *padding_mi_list,
        ]

        for i, menu_item in enumerate(self.menu_items):
            self.grid.addWidget(widget=menu_item, row=i, col=0)

    def create_option_selection_mi(self, name: SettingName):
        option = self.launch_settings.get_option(name=name)

        available_choices = option.available_choices.values()
        current_choice = option.current_choice

        if not available_choices:
            available_choices = [Choice(value='', label='')]

        list_window: ListSelectWindow = ListSelectWindow(
            items=available_choices,
            parent_to_swap=self,
            root=self.root,
            pos=DEFAULT_POS,
            size=(70, MAX_LINES),
            maxWidth=70,
            maxHeight=MAX_LINES,
        )

        option_selection = OptionSelectionMenuItem(
            list_window=list_window,
            option_name=name,
            button_text=name,
            parent=self)

        option_selection.set_value_label_text(text=current_choice.label)

        return option_selection

    def get_current_settings_from_ui(self):
        settings = dict()
        for psmi in self.option_selection_mi_list:

            name, value = psmi.get_current_name_value_pair()

            if value is not None:
                settings[name] = value

        return settings


class Launcher:
    def __init__(self, launch_settings: LaunchSettings):
        self._launch_settings = launch_settings
        self.main_window: MainWindow | None = None

    def run(self):
        try:
            self._run()
        except Exception as e:
            logger.error(f'Something goes wrong with launcher: {e}')

    def _run(self):
        root = ttk.TTk(title='')

        self.main_window = MainWindow(
            launch_settings=self._launch_settings,
            parent=root,
            pos=DEFAULT_POS,
            size=(70, MAX_LINES),
            maxWidth=70,
            maxHeight=MAX_LINES,
        )

        root.mainloop()

    def get_updated_launch_settings(self) -> LaunchSettings:
        settings_dict = self.main_window.get_current_settings_from_ui()

        self._launch_settings.apply_settings(settings=settings_dict)

        return self._launch_settings


def main():
    launcher = Launcher()
    launcher.run()


if __name__ == "__main__":
    main()
