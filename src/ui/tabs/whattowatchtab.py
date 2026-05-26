from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QDialog,
    QWidget,
    QTextEdit,
    QLabel,
    QVBoxLayout,
    QPushButton,
    QCheckBox,
    QHBoxLayout,
    QGroupBox,
)

from recommender.output import generate_origin_string_for_user
from recommender.pythonapi import RecThread
from recommender.utils import get_english_title_or_user_preferred, clean_format
from ui.widgets.medialistwidget import (
    FetchProgressDialog,
    PaginatedListWidget,
    BaseWhyDialog,
    BaseMediaViewWidget,
)


class WhatToWatchTab(QWidget):
    def __init__(self):
        super().__init__()

        self.descriptionLabel = QLabel(
            "Not sure what to watch? Enter your AniList username below and I'll help you out!\nGot friends over to watch anime? Even better!\nPut everyone's AniList usernames below and I'll take everyone's tastes into account!\nPut each username on a separate line please :)"
        )
        self.userNamesEntry = QTextEdit()
        self.userNamesEntry.setMaximumHeight(100)
        self.usesWidget = UsesWidget()
        self.submitButton = QPushButton("Submit")
        self.submitButton.clicked.connect(self.on_submit_clicked)
        self.listWidget = PaginatedListWidget(
            lambda item, metadata: RecommendedMediaViewWidget(item, metadata)
        )

        layout = QVBoxLayout()
        layout.addWidget(self.descriptionLabel)
        layout.addWidget(self.userNamesEntry)
        layout.addWidget(self.usesWidget)
        layout.addWidget(self.submitButton)
        layout.addWidget(self.listWidget)
        self.setLayout(layout)

    def on_submit_clicked(self):
        user_names = self.userNamesEntry.toPlainText().split("\n")
        fetch_dialog = FetchProgressDialog(
            parent=self,
            fetch_thread=RecThread(
                user_names=user_names,
                use=self.usesWidget.get_data(),
            ),
        )
        if fetch_dialog.exec() == QDialog.DialogCode.Accepted:
            print("Fetch dialog accepted")
            result = fetch_dialog.result
            self.listWidget.set_list(
                result[0], {"origins": result[1], "usernames": user_names}
            )


class UsesWidget(QGroupBox):
    def __init__(self):
        super().__init__()

        self._data = {
            "genres": True,
            "tags": True,
            "decades": True,
            "studios": True,
            "staff": True,
        }

        layout = QHBoxLayout()

        self.setTitle("Use:")

        for option in self._data.keys():
            checkbox = QCheckBox(option.capitalize())
            checkbox.setChecked(True)
            checkbox.toggled.connect(self._on_toggled)
            layout.addWidget(checkbox)

        self.setLayout(layout)

    @Slot(bool)
    def _on_toggled(self, checked):
        sender = self.sender()
        if isinstance(sender, QCheckBox):
            self._data[sender.text().lower()] = checked

    def get_data(self):
        return self._data


class RecWhyDialog(BaseWhyDialog):
    def __init__(self, parent, media, metadata):
        super().__init__(parent, media, metadata)

        usernames = metadata["usernames"]
        for index, username in enumerate(usernames):
            why_string = self.get_why_string(
                {
                    "username": username,
                    "origins": metadata["origins"][index],
                    "party": len(usernames) > 1,
                }
            )
            text_view = QTextEdit()
            text_view.setReadOnly(True)
            text_view.setText(why_string)
            self.tabView.addTab(text_view, username)

        if len(usernames) == 1:
            self.tabView.tabBar().hide()

    def get_why_string(self, metadata=None):
        old_why_string = generate_origin_string_for_user(
            self.media, metadata["origins"], metadata["username"]
        )
        new_why_string = ""
        for line in old_why_string.split("\n")[1:-1]:
            rated_by_you = "You rated it" in line
            if rated_by_you and not metadata["party"]:
                continue
            new_why_string += f"- {line.strip()}\n\n"
            if rated_by_you and metadata["party"]:
                break

        if not new_why_string:
            new_why_string = "Not enough information"
        return new_why_string


class RecommendedMediaViewWidget(BaseMediaViewWidget):
    def __init__(self, item, metadata):
        super().__init__(item["recMedia"], metadata)

        self.set_title(
            f"{get_english_title_or_user_preferred(self.media['title'])} ({clean_format(self.media['format'])}, {self.media['startDate']['year']})"
        )
        self.set_data_widget(_ItemScoreWidget(item["recScore"]))

    def _show_why(self):
        RecWhyDialog(self, self.media, self.metadata).exec()


class _ItemScoreWidget(QWidget):
    def __init__(self, score):
        super().__init__()

        self.score_label = QLabel(f"{score:.2f}% match{'!' if score > 75 else ''}")

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
