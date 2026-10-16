import dataclasses
import sys

import TermTk as ttk
from TermTk import TTkColor

from motion_mask import loggers
from motion_mask.launch_settings import LaunchSettings, SettingName

logger = loggers.LoggerFactory.get_logger(name=__name__)

MAX_LINES = 10


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
            maxWidth=60,
            maxHeight=20,
        )

    def create_vertical(self) -> ttk.TTkGridLayout:
        return ttk.TTkVBoxLayout(
            columnMinWidth=10,
            rowMinHeight=10,
            minWidth=5,
            maxWidth=60,
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
            text="---",
            style=self.STYLE,
        )
        layout.addWidget(widget=self.value_label, row=0, col=2)

    def do_action(self):
        self.parent.last_widget = self.button
        self._do_action()

    def _do_action(self):
        raise NotImplementedError()

    def set_value_text(self, text: str):
        self.value_label.setText(text=text)


class QuitMenuItem(MenuItem):
    def __init__(self, parent,
                 button_text: str = 'Quit',
                 **kwargs):
        super().__init__(parent, button_text, **kwargs)

    def _do_action(self):
        ttk.TTkHelper.quit()
        sys.exit(0)


class LaunchMenuItem(MenuItem):
    def __init__(self, parent,
                 button_text: str = 'Launch',
                 **kwargs):
        super().__init__(parent, button_text, **kwargs)

    def _do_action(self):
        ttk.TTkHelper.quit()


class ParamSelectionMenuItem(MenuItem):
    def __init__(self, parent,
                 button_text: str = 'button',
                 action=None,
                 **kwargs):
        super().__init__(parent, button_text, **kwargs)
        self.action = action

    def _do_action(self):
        self.action()


class ListSelectWindow(Stylable):
    def __init__(self, items, parent_to_swap: 'MainWindow', root, **kwargs):
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

        self._selected_item = None

        self.list_view = ttk.TTkListWidget(parent=self,
                                           style=self.LIST_STYLE,
                                           showSearch=True,
                                           )

        for item in self.items:
            self.list_view.addItem(item)

        self.list_view.textClicked.connect(self._on_item_selected)

    def show_instead(self):
        self.parent_to_swap.hide()
        self.list_view.setFocus()
        self.show()

    def show_back(self):
        self.hide()
        self.parent_to_swap.last_widget.setFocus()
        self.parent_to_swap.show()

    def _on_item_selected(self):
        labels = self.list_view.selectedLabels()
        if labels:
            self._selected_item = labels[0]

        self.show_back()

    @property
    def selected_item(self):
        return self._selected_item


@dataclasses.dataclass
class Updatable:
    list_window: ListSelectWindow
    param_selection: ParamSelectionMenuItem


class MainWindow(Stylable):
    def create_updatable(self, name: SettingName):
        option = self.launch_settings.get_option(name=name)

        list_window: ListSelectWindow = ListSelectWindow(
            items=option.available_choices,
            parent_to_swap=self,
            root=self.root,
            pos=(2, 2),
            size=(60, MAX_LINES),
            maxWidth=60,
            maxHeight=MAX_LINES,
        )

        param_selection = ParamSelectionMenuItem(
            button_text=name,
            parent=self,
            action=lambda: list_window.show_instead())

        return Updatable(
            list_window=list_window,
            param_selection=param_selection
        )

    def __init__(self,
                 launch_settings: LaunchSettings,
                 parent,
                 **kwargs):
        super().__init__(parent=parent, **kwargs)
        self.launch_settings = launch_settings
        self.root = parent

        self.grid = self.layout_factory.create()
        self.setLayout(self.grid)

        self.mi_quit = QuitMenuItem(parent=self)
        self.mi_launch = LaunchMenuItem(parent=self)

        self.last_widget = self.mi_launch

        self.updatable_list = [
            self.create_updatable(name=SettingName.mode),
            self.create_updatable(name=SettingName.camera),
            self.create_updatable(name=SettingName.virtual_camera),
            self.create_updatable(name=SettingName.avatar_name),
        ]

        self.menu_items_with_lists = [x.param_selection
                                      for x in self.updatable_list]

        padding = [self.create_blank_label(text="") for _ in range(10)]

        self.menu_items = [
            self.mi_quit,
            *self.menu_items_with_lists,
            self.mi_launch,
            *padding,
        ]

        for i, menu_item in enumerate(self.menu_items):
            self.grid.addWidget(widget=menu_item, row=i, col=0)

    def show(self) -> None:
        super().show()
        self.update_from_selections()

    def update_from_selections(self):
        for u in self.updatable_list:
            t = u.list_window.selected_item
            u.param_selection.set_value_text(text=t)


class Launcher:
    def __init__(self, launch_settings: LaunchSettings):
        self.launch_settings = launch_settings

    def run(self):
        try:
            self._run()
        except Exception as e:
            logger.error(f'Something goes wrong with launcher: {e}')

    def _run(self):
        root = ttk.TTk(title='')

        main_window = MainWindow(
            launch_settings=self.launch_settings,
            parent=root,
            pos=(2, 2),
            size=(60, MAX_LINES),
            maxWidth=60,
            maxHeight=MAX_LINES,
        )

        root.mainloop()


def main():
    launcher = Launcher()
    launcher.run()


if __name__ == "__main__":
    main()
