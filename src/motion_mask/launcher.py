import TermTk as ttk
from TermTk import TTkColor



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


class ParamSelectionMenuItem(MenuItem):
    def __init__(self, parent,
                 button_text: str = 'test button',
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

        if max_height < 16:
            self.setMaximumHeight(maxh=max_height)

        self._selected_item = None

        self.list_view = ttk.TTkListWidget(parent=self,
                                           style=self.LIST_STYLE,
                                           showSearch=True

                                           )

        for item in self.items:
            self.list_view.addItem(item)

        self.list_view.textClicked.connect(self._on_item_selected)

    def show_instead(self):
        self.parent_to_swap.hide()
        self.list_view.setFocus()
        self.show()
        self.update()

    def show_back(self):
        self.hide()
        self.parent_to_swap.show()
        self.parent_to_swap.mi_param_selection.setFocus()
        self.parent_to_swap.update()

    def _on_item_selected(self):
        labels = self.list_view.selectedLabels()
        if labels:
            self._selected_item = labels[0]

        self.show_back()

    @property
    def selected_item(self):
        return self._selected_item


class MainWindow(Stylable):
    def __init__(self, parent, **kwargs):
        super().__init__(parent=parent, **kwargs)
        self.root = parent

        self.grid = self.layout_factory.create()
        self.setLayout(self.grid)

        self.mi_param_selection = ParamSelectionMenuItem(
            parent=self,
            action=lambda: self.list_window.show_instead())

        self.mi_quit = QuitMenuItem(parent=self)

        self.menu_items = [
            self.mi_param_selection,
            self.mi_quit,
        ]

        self.menu_items += [self.create_blank_label(text="") for _ in range(20)]

        for i, menu_item in enumerate(self.menu_items):
            self.grid.addWidget(widget=menu_item, row=i, col=0)

        self.list_items = [
            "list item 1",
            "list item 2",
            "list item 3",
            "list item 4",
            "list item 5",
            "list item 6",
            "list item x",
            "list item x",
            "list item x",
            "list item x",
            "list item x",
            "list item x",
        ]

        self.list_window: ListSelectWindow = ListSelectWindow(
            items=self.list_items,
            parent_to_swap=self,
            root=self.root,
            pos=(2, 2),
            size=(60, 16),
            maxWidth=60,
            maxHeight=16,
        )

    def show(self) -> None:
        super().show()
        self.update_from_selections()

    def update_from_selections(self):
        self.mi_param_selection.set_value_text(
            text=self.list_window.selected_item)


class Launcher:
    layout_factory: LayoutFactory = DefaultLayoutFactory()

    def __init__(self):
        self.root = ttk.TTk(title='')

    def start(self):
        main_window = MainWindow(
            parent=self.root,
            pos=(2, 2),
            size=(60, 16),
            maxWidth=60,
            maxHeight=16,
        )

        self.root.mainloop()


def main():
    gui = Launcher()
    gui.start()


if __name__ == "__main__":
    main()
