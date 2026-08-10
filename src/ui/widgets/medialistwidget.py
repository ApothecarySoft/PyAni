import sys
from functools import partial
from math import ceil

from PySide6.QtCore import Signal, Slot, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QGridLayout,
    QMessageBox,
    QProgressBar,
    QWidget,
    QLineEdit,
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QTextEdit,
)

from recommender.pythonapi import BaseThread
from recommender.utils import get_english_title_or_user_preferred
from ui.widgets.netimagewidget import NetImageWidget


class FetchProgressWidget(QWidget):
    def __init__(self):
        super().__init__()

        self.v_layout = QVBoxLayout()

        self.setLayout(self.v_layout)

    def _add_progressbar(self):
        progress_bar = QProgressBar()
        progress_bar.setMaximum(100)
        progress_bar.setValue(0)
        self.v_layout.addWidget(progress_bar)
        return progress_bar

    def _remove_progress_bars_after(self, after_layer):
        bars_to_remove = self.v_layout.findChildren(QProgressBar)[after_layer:]
        for bar in bars_to_remove:
            self.v_layout.removeWidget(bar)

    def update_progress(self, progress: int, layer: int):
        bars = self.v_layout.findChildren(QProgressBar)

        if len(bars) < layer:
            print(
                f"Can not skip progress bar layers ({len(bars) - 1} -> {layer})",
                file=sys.stderr,
            )
            return

        if len(bars) == layer:
            bar = self._add_progressbar()
        else:
            bar = bars[layer]

        bar.setValue(progress)

        if len(bars) > layer + 1:
            self._remove_progress_bars_after(layer)


class FetchProgressDialog(QDialog):
    def __init__(self, parent, fetch_thread: BaseThread):
        super().__init__(parent=parent)

        self.statusText = QTextEdit()
        self.statusText.setReadOnly(True)
        self.progressBars = FetchProgressWidget()

        layout = QVBoxLayout()
        layout.addWidget(self.statusText)
        layout.addWidget(self.progressBars)

        self.setLayout(layout)

        self.resize(400, 100)

        self.result = None
        self.status = ""
        self.update_window_title(0)

        self.fetch_thread = fetch_thread
        self.fetch_thread.ResultSignal.connect(self.on_result)
        self.fetch_thread.ProgressSignal.connect(self.on_progress_update)
        self.fetch_thread.StatusSignal.connect(self.on_status_update)
        self.fetch_thread.ErrorSignal.connect(self.on_error)
        self.fetch_thread.CooldownSignal.connect(self.on_cooldown)
        self.fetch_thread.start()

    def update_window_title(self, progress):
        self.setWindowTitle(f"Fetching data ({progress}%)")

    @Slot(str, int)
    def on_status_update(self, new_status, layer):
        self.status = new_status
        self.statusText.append(f"{self.status}\n")

    @Slot(int, int)
    def on_progress_update(self, new_progress, layer):
        self.update_window_title(new_progress)
        self.progressBars.update_progress(new_progress, layer)

    @Slot(object)
    def on_result(self, result):
        self.result = result
        self.accept()

    @Slot(str)
    def on_error(self, error_message):
        error_box = QMessageBox(parent=self)
        error_box.setIcon(QMessageBox.Icon.Critical)
        error_box.setText(error_message)
        error_box.setWindowTitle("Error")
        error_box.exec()
        self.reject()

    @Slot(str)
    def on_cooldown(self, cooldown_message):
        cooldown_dialog = CooldownProgressDialog(
            parent=self, cooldown_message=cooldown_message
        )
        self.fetch_thread.CooldownProgressSignal.connect(
            cooldown_dialog.on_cooldown_progress
        )
        cooldown_dialog.exec()


class CooldownProgressDialog(QDialog):
    def __init__(self, parent, cooldown_message):
        super().__init__(parent=parent)

        self.setWindowTitle("Cooldown")

        self.messageLabel = QLabel(cooldown_message)
        self.progressBar = QProgressBar()
        self.progressBar.setMaximum(100)
        self.progressBar.setValue(0)
        self.progressBar.setTextVisible(False)
        self.maximum = None

        layout = QVBoxLayout()
        layout.addWidget(self.messageLabel)
        layout.addWidget(self.progressBar)
        self.setLayout(layout)

    @Slot(int)
    def on_cooldown_progress(self, seconds):
        if seconds <= 1:
            self.accept()

        if self.maximum is None:
            self.maximum = seconds
            self.progressBar.setMaximum(seconds)
            self.progressBar.setFormat("%v / %ms")
            self.progressBar.setTextVisible(True)

        self.progressBar.setValue(self.maximum - seconds + 1)


class PaginatedListWidget(QWidget):
    def __init__(self, make_media_view):
        super().__init__()

        layout = QVBoxLayout()

        self.listWidget = _ListWidget(make_media_view=make_media_view)
        self.pageWidget = _PageWidget()
        self.listWidget.PageCountChanged.connect(self.pageWidget.on_page_count_changed)
        self.pageWidget.PageSelected.connect(self.listWidget.set_page)

        layout.addWidget(self.listWidget)
        layout.addWidget(self.pageWidget)

        self.setLayout(layout)

    def set_list(self, main_list, metadata):
        self.listWidget.set_list(main_list, metadata)


class _PageWidget(QWidget):
    _PageSelectedInternal = Signal(int)
    PageSelected = Signal(int)

    def __init__(self):
        super().__init__()

        self.page_count = 0
        self.max_page_buttons = 10
        self.current_page = 0
        self.page_entry = QLineEdit()
        self.page_entry.returnPressed.connect(
            lambda: self._PageSelectedInternal.emit(int(self.page_entry.text()) - 1)
        )
        self._PageSelectedInternal.connect(self._on_page_selected)
        self.page_entry.setText("1")
        self.page_buttons_container = None

        self.prev_page_button = QPushButton("<-")
        self.prev_page_button.clicked.connect(
            lambda: self._PageSelectedInternal.emit(self.current_page - 1)
        )
        self.next_page_button = QPushButton("->")
        self.next_page_button.clicked.connect(
            lambda: self._PageSelectedInternal.emit(self.current_page + 1)
        )

        layout = QHBoxLayout()

        layout.addWidget(self.prev_page_button)
        layout.addWidget(self.next_page_button)

        self.setLayout(layout)

        self.setVisible(False)

    @Slot(int)
    def _on_page_selected(self, page_num):
        if 0 <= page_num <= self.page_count - 1:
            self.current_page = page_num
            self.PageSelected.emit(page_num)
        self.page_entry.setText(str(self.current_page + 1))

    @Slot(int)
    def on_page_count_changed(self, new_page_count):
        self.page_count = new_page_count
        self.setVisible(self.page_count >= 1)

        if self.page_buttons_container:
            self.page_buttons_container.setParent(None)
            self.page_buttons_container.deleteLater()

        self.page_buttons_container = QWidget()
        layout = QHBoxLayout(self.page_buttons_container)
        base_layout = self.layout()
        if isinstance(base_layout, QHBoxLayout):
            base_layout.insertWidget(1, self.page_buttons_container)
        else:
            raise RuntimeError("Wrong layout type")

        halfway_point = int(self.max_page_buttons / 2)
        too_big = self.page_count > self.max_page_buttons

        if too_big:
            button_nums = [
                *range(0, halfway_point),
                *range(self.page_count - halfway_point, self.page_count),
            ]
        else:
            button_nums = range(self.page_count)

        for i in button_nums:
            page_button = QPushButton(f"{i + 1}")
            page_button.clicked.connect(partial(self._PageSelectedInternal.emit, i))
            page_button.setMaximumWidth(30)
            layout.addWidget(page_button)
            if too_big and i + 1 == halfway_point:
                layout.addWidget(self.page_entry)

        self.setLayout(layout)
        self._PageSelectedInternal.emit(0)


class _ListWidget(QWidget):
    PageCountChanged = Signal(int)

    def __init__(self, make_media_view):
        super().__init__()

        self.make_media_view = make_media_view

        self.metadata = None
        self.main_list = None
        self.items_per_page = 5
        self.list_container = None
        layout = QVBoxLayout()
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        layout.addWidget(self.scroll_area)
        self.setLayout(layout)

    @Slot(int)
    def set_page(self, page_num) -> bool:
        print(f"Setting page: {page_num}")
        if self.main_list is None:
            return False

        if self.list_container:
            self.list_container.setParent(None)
            self.list_container.deleteLater()

        self.list_container = QWidget()
        layout = QVBoxLayout(self.list_container)
        self.scroll_area.setWidget(self.list_container)

        first_item = page_num * self.items_per_page

        for item in self.main_list[first_item : first_item + self.items_per_page]:
            item_widget = self.make_media_view(item=item, metadata=self.metadata)
            layout.addWidget(item_widget)

        return True

    def set_list(self, main_list, metadata):
        print(f"Setting list with {len(main_list)} items")
        self.metadata = metadata
        self.main_list = main_list
        self.PageCountChanged.emit(ceil(len(main_list) / self.items_per_page))


class BaseMediaViewWidget(QWidget):
    def __init__(self, media, metadata):
        super().__init__()

        self.media = media

        self.metadata = metadata

        media_type = self.media["type"]

        self.imageWidget = NetImageWidget(self.media["coverImage"]["medium"])
        self.imageWidget.setMaximumWidth(100)
        self.dataWidget = QWidget()
        self.titleLabel = QLabel()
        self.titleLabel.setWordWrap(True)
        self.openAnilistButton = QPushButton("Open")
        self.openAnilistButton.clicked.connect(
            lambda: QDesktopServices.openUrl(
                QUrl(f"https://anilist.co/{media_type.lower()}/{self.media['id']}")
            )
        )
        self.openAnilistButton.setSizePolicy(
            QSizePolicy.Policy.Maximum, QSizePolicy.Policy.MinimumExpanding
        )
        self.whyButton = QPushButton("Why?")
        self.whyButton.clicked.connect(self._show_why)

        layout = QGridLayout()

        layout.addWidget(self.imageWidget, 0, 0, 3, 1)
        layout.addWidget(self.titleLabel, 0, 1)
        layout.addWidget(self.dataWidget, 1, 1)
        layout.addWidget(self.whyButton, 2, 1)
        layout.addWidget(self.openAnilistButton, 0, 2, 3, 1)

        self.setLayout(layout)

    def set_data_widget(self, widget):
        layout = self.layout()
        if layout is not None:
            layout.replaceWidget(self.dataWidget, widget)

    def set_title(self, title: str):
        self.titleLabel.setText(title)

    def _show_why(self):
        pass


class BaseWhyDialog(QDialog):
    def __init__(self, parent, media, metadata):
        super().__init__(parent=parent)
        self.setWindowTitle(
            f"Why {'watch' if media['type'] == 'ANIME' else 'read'} {get_english_title_or_user_preferred(media['title'])}?"
        )
        self.media = media
        self.metadata = metadata
        self.setMinimumWidth(400)

        self.tabView = QTabWidget()

        layout = QVBoxLayout()

        layout.addWidget(self.tabView)

        self.setLayout(layout)

    def get_why_string(self, metadata=None):
        return ""
