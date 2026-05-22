from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QWidget,
    QPushButton,
    QDialog,
    QTextEdit,
    QVBoxLayout,
    QLabel,
    QMessageBox,
)

from recommender.cachefiles import load_tags_from_cache, save_tags_to_cache
from recommender.pythonapi import HunterThread
from recommender.utils import get_english_title_or_user_preferred, clean_format
from ui.widgets.medialistwidget import (
    PaginatedListWidget,
    FetchProgressDialog,
    BaseWhyDialog,
    BaseMediaViewWidget,
)


class AniHunterTab(QWidget):
    def __init__(self):
        super().__init__()

        self.hunter_label = QLabel(
            "Find interesting upcoming releases before they're out!\nGive me a list of your favorite AniList tags and let me loose.\nI'll find relevant upcoming releases you might not have heard of yet!\nI might not show you the same thing twice, so if it looks interesting make sure to save it!"
        )
        self.edit_tags_button = QPushButton("Edit tags")
        self.edit_tags_button.clicked.connect(self.edit_tags)
        self.run_button = QPushButton("Go hunt!")
        self.run_button.clicked.connect(self.go_hunt)
        self.list_widget = PaginatedListWidget(
            lambda item, metadata: HunterMediaViewWidget(item, metadata)
        )
        layout = QVBoxLayout()
        layout.addWidget(self.hunter_label)
        layout.addWidget(self.edit_tags_button)
        layout.addWidget(self.run_button)
        layout.addWidget(self.list_widget)
        self.setLayout(layout)

    @Slot()
    def go_hunt(self):
        fetch_dialog = FetchProgressDialog(
            parent=self,
            fetch_thread=HunterThread(),
        )
        if fetch_dialog.exec() == QDialog.DialogCode.Accepted:
            self.list_widget.set_list(fetch_dialog.result, {})
            if len(fetch_dialog.result) == 0:
                msg_box = QMessageBox(parent=self)
                msg_box.setIcon(QMessageBox.Icon.Information)
                msg_box.setText(
                    "Nothing new found for your tags since last time.\nCheck back later!"
                )
                msg_box.setWindowTitle("All caught up!")
                msg_box.exec()

    @Slot()
    def edit_tags(self):
        dialog = EditTagsDialog(self)
        dialog.exec()


class EditTagsDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent=parent)

        self.setWindowTitle("Edit tags")
        self.text_edit = QTextEdit()
        self.original_tags = "".join(load_tags_from_cache())
        self.text_edit.setText(self.original_tags)
        self.save_tags_button = QPushButton("Save tags")
        self.save_tags_button.clicked.connect(self.save_tags)

        layout = QVBoxLayout()
        layout.addWidget(self.text_edit)
        layout.addWidget(self.save_tags_button)
        self.setLayout(layout)

    @Slot()
    def save_tags(self):
        save_tags_to_cache(self.text_edit.toPlainText())
        self.accept()

    def closeEvent(self, event):
        if self.text_edit.toPlainText() != self.original_tags:
            confirm_dialog = QMessageBox(parent=self)
            confirm_dialog.setIcon(QMessageBox.Icon.Warning)
            confirm_dialog.setWindowTitle("Unsaved changes!")
            confirm_dialog.setText("Would you like to save your changes?")
            confirm_dialog.setStandardButtons(
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel
            )
            reply = confirm_dialog.exec()
            if reply == QMessageBox.StandardButton.Save:
                self.save_tags()
            elif reply == QMessageBox.StandardButton.Discard:
                self.accept()
            event.ignore()


class HunterWhyDialog(BaseWhyDialog):
    def __init__(self, parent, media):
        super().__init__(parent, media, media)

        why_string = self.get_why_string(media)
        text_view = QTextEdit()
        text_view.setReadOnly(True)
        text_view.setText(why_string)
        self.tabView.addTab(text_view, "")
        self.tabView.tabBar().hide()

    def get_why_string(self, metadata=None):
        if metadata is None:
            return "Not enough information"
        else:
            string = (
                "New media containing your tags!\n"
                if metadata.setdefault("new", True)
                else "New tags have been added!\n"
            )
            for tag in metadata.setdefault("new_tags", []):
                string += f"{tag}\n"
            return string


class HunterMediaViewWidget(BaseMediaViewWidget):
    def __init__(self, media, metadata):
        super().__init__(media, metadata)

        self.set_title(
            f"{get_english_title_or_user_preferred(self.media['title'])} ({clean_format(self.media['format'])})"
        )

    def _show_why(self):
        HunterWhyDialog(self, self.media).exec()
