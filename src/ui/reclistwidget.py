from functools import partial
from math import ceil

from PySide6.QtCore import Signal, Slot, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QMessageBox,
    QProgressBar,
    QWidget,
    QLineEdit,
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
    QLabel,
)

from recommender.pythonapi import FetchThread
from recommender.utils import get_english_title_or_user_preferred, clean_format


class FetchProgressDialog(QDialog):
    def __init__(self, parent, user_names, use, force_refresh=False):
        super().__init__(parent=parent)

        self.statusLabel = QLabel()
        self.progressBar = QProgressBar()

        layout = QVBoxLayout()
        layout.addWidget(self.statusLabel)
        layout.addWidget(self.progressBar)

        self.setLayout(layout)

        self.result = None
        self.progress = 0
        self.status = "Fetching data"
        self.update_window_title()

        self.fetch_thread = FetchThread(
            user_names=user_names, use=use, force_refresh=force_refresh
        )
        self.fetch_thread.ResultSignal.connect(self.on_result)
        self.fetch_thread.ProgressSignal.connect(self.on_progress_update)
        self.fetch_thread.StatusSignal.connect(self.on_status_update)
        self.fetch_thread.ErrorSignal.connect(self.on_error)
        self.fetch_thread.start()

    def update_window_title(self):
        self.setWindowTitle(f"{self.status} ({self.progress}%)")

    @Slot(str)
    def on_status_update(self, new_status):
        self.status = new_status
        self.statusLabel.setText(self.status)
        self.update_window_title()

    @Slot(int)
    def on_progress_update(self, new_progress):
        self.progress = new_progress
        self.update_window_title()
        self.progressBar.setValue(self.progress)

    def on_result(self, result):
        print("FetchProgressDialog on_result")
        self.result = result
        self.accept()

    @Slot(str)
    def on_error(self, error_message):
        print(f"FetchProgressDialog on_error: {error_message}")
        error_box = QMessageBox()
        error_box.setIcon(QMessageBox.Critical)
        error_box.setText(error_message)
        error_box.setWindowTitle("Error")
        error_box.exec()
        self.reject()


class RecommendationListWidget(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()

        self.listWidget = _RecommendationListWidget()
        self.pageWidget = _PageWidget()
        self.listWidget.PageCountChanged.connect(self.pageWidget.on_page_count_changed)
        self.pageWidget.PageSelected.connect(self.listWidget.set_page)

        layout.addWidget(self.listWidget)
        layout.addWidget(self.pageWidget)

        self.setLayout(layout)

    def set_list(self, party_list, media_type, origins):
        self.listWidget.set_list(party_list, media_type, origins)


class _PageWidget(QWidget):
    PageSelected = Signal(int)

    def __init__(self):
        super().__init__()

        self.page_count = 0
        self.max_page_buttons = 10
        self.page_entry = QLineEdit()
        self.page_entry.returnPressed.connect(
            lambda: self.PageSelected.emit(int(self.page_entry.text()) - 1)
        )

    @Slot(int)
    def on_page_count_changed(self, new_page_count):
        self.page_count = new_page_count

        layout = QHBoxLayout()

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
            page_button.clicked.connect(partial(self.PageSelected.emit, i))
            layout.addWidget(page_button)
            if too_big and i + 1 == halfway_point:
                layout.addWidget(self.page_entry)

        self.setLayout(layout)


class _RecommendationListWidget(QWidget):
    PageCountChanged = Signal(int)

    def __init__(self):
        super().__init__()

        self.party_list = None
        self.origins = None
        self.items_per_page = 5
        self.media_type = None
        self.list_container = None
        self.setLayout(QVBoxLayout())

    @Slot(int)
    def set_page(self, page_num) -> bool:
        print(f"Setting page: {page_num}")
        if self.party_list is None or self.origins is None:
            return False

        if self.list_container:
            self.list_container.setParent(None)
            self.list_container.deleteLater()

        self.list_container = QWidget()
        layout = QVBoxLayout(self.list_container)
        self.layout().addWidget(self.list_container)

        first_item = page_num * self.items_per_page

        for item in self.party_list[first_item : first_item + self.items_per_page]:
            item_widget = _RecommendationItemWidget(
                item=item, media_type=self.media_type, origins=self.origins
            )
            layout.addWidget(item_widget)

        return True

    def set_list(self, party_list, media_type, origins):
        print(f"Setting list with {len(party_list)} items")
        self.party_list = party_list
        self.origins = origins
        self.media_type = media_type
        self.PageCountChanged.emit(ceil(len(party_list) / self.items_per_page))
        self.set_page(0)


class _RecommendationItemWidget(QWidget):
    def __init__(self, item, media_type, origins):
        super().__init__()

        media = item["recMedia"]

        self.infoWidget = ItemInfoWidget(media, media_type, origins)
        self.imageWidget = _ItemImageWidget()
        self.scoreWidget = _ItemScoreWidget(item["recScore"])

        layout = QHBoxLayout()

        layout.addWidget(self.imageWidget)
        layout.addWidget(self.infoWidget)
        layout.addWidget(self.scoreWidget)

        self.setLayout(layout)


class ItemInfoWidget(QWidget):
    def __init__(self, media, media_type, origins):
        super().__init__()

        title = get_english_title_or_user_preferred(media["title"])
        media_format = media["format"]
        year = media["startDate"]["year"]
        url = f"https://anilist.co/{media_type.lower()}/{media['id']}"

        self.titleLabel = QLabel()
        self.titleLabel.setText(f"{title} ({clean_format(media_format)}, {year})")

        self.openAnilistButton = QPushButton("Open AniList page")
        self.openAnilistButton.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(url)))

        layout = QVBoxLayout()
        layout.addWidget(self.titleLabel)
        layout.addWidget(self.openAnilistButton)

        self.setLayout(layout)


class _ItemImageWidget(QWidget):
    def __init__(self, image_url=None):
        super().__init__()


class _ItemScoreWidget(QWidget):
    def __init__(self, score):
        super().__init__()

        self.score_label = QLabel(f"{score}% match{'!' if score > 75 else ''}")

        layout = QVBoxLayout()

        layout.addWidget(self.score_label)

        self.setLayout(layout)

        if score > 75:
            background_color = "green"
            text_color = "white"
        elif score > 50:
            background_color = "yellow"
            text_color = "black"
        elif score > 25:
            background_color = "orange"
            text_color = "white"
        else:
            background_color = "red"
            text_color = "white"

        self.setStyleSheet(f"background-color: {background_color}; color: {text_color}")
