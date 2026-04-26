from PySide6.QtWidgets import (
    QDialog,
    QWidget,
    QTextEdit,
    QLabel,
    QVBoxLayout,
    QPushButton,
    QProgressBar,
)

from ui.reclistwidget import FetchProgressDialog, RecommendationListWidget


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
        fetch_dialog = FetchProgressDialog(
            parent=self,
            user_names=self.userNamesEntry.toPlainText().split("\n"),
            use={
                "tags": True,
                "staff": True,
                "studios": True,
                "genres": True,
                "decades": True,
            }
        )
        if fetch_dialog.exec() == QDialog.Accepted:
            print("Fetch dialog accepted")
            result = fetch_dialog.result
            self.listWidget.set_list(result[0], "ANIME", result[1])
