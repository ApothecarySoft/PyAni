from PySide6.QtWidgets import (
    QWidget,
    QTextEdit,
    QLabel,
    QVBoxLayout,
    QPushButton,
)

from recommender.pythonapi import get_watch_party
from ui.reclistwidget import RecommendationListWidget


class WatchPartyTab(QWidget):
    def __init__(self):
        super().__init__()

        self.descriptionLabel = QLabel(
            "Watch Party!\nGot friends over to watch anime? Put everyone's AniList usernames below and I'll suggest what to watch!\nPut each username on a separate line please :)"
        )
        self.userNamesEntry = QTextEdit()
        self.submitButton = QPushButton("Submit")
        self.submitButton.clicked.connect(self.on_submit_clicked)
        self.listWidget = RecommendationListWidget()

        layout = QVBoxLayout()
        layout.addWidget(self.descriptionLabel)
        layout.addWidget(self.userNamesEntry)
        layout.addWidget(self.submitButton)
        layout.addWidget(self.listWidget)
        self.setLayout(layout)

    def on_submit_clicked(self):
        party_list, origins = get_watch_party(
            user_names=self.userNamesEntry.toPlainText().split("\n"),
            use={
                "tags": True,
                "staff": True,
                "studios": True,
                "genres": True,
                "decades": True,
            },
            force_refresh=False,
        )
        self.listWidget.set_list(party_list, "ANIME", origins)
