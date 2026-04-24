from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QTextEdit,
    QLabel,
    QVBoxLayout,
    QPushButton,
    QHBoxLayout,
)

from recommender.pythonapi import get_watch_party
from recommender.utils import get_english_title_or_user_preferred, clean_format


class WatchPartyTab(QWidget):
    def __init__(self):
        super().__init__()

        self.descriptionLabel = QLabel(
            "Watch Party!\nGot friends over to watch anime? Put everyone's AniList usernames below and I'll suggest what to watch!\nPut each username on a separate line please :)"
        )
        self.userNamesEntry = QTextEdit()
        self.submitButton = QPushButton("Submit")
        self.submitButton.clicked.connect(self.on_submit_clicked)
        self.listWidget = WatchPartyListWidget()

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


class WatchPartyListWidget(QWidget):
    def __init__(self):
        super().__init__()

        self.party_list = None
        self.origins = None
        self.items_per_page = 5
        self.media_type = None

    def set_page(self, page_num) -> bool:
        if self.party_list is None or self.origins is None:
            return False

        layout = QVBoxLayout()

        first_item = page_num * self.items_per_page

        for item in self.party_list[first_item : first_item + self.items_per_page]:
            item_widget = WatchPartyListItemWidget(
                item=item, media_type=self.media_type, origins=self.origins
            )
            layout.addWidget(item_widget)

        self.setLayout(layout)
        return True

    def set_list(self, party_list, media_type, origins):
        self.party_list = party_list
        self.origins = origins
        self.media_type = media_type
        self.set_page(0)


class WatchPartyListItemWidget(QWidget):
    def __init__(self, item, media_type, origins):
        super().__init__()

        media = item["recMedia"]

        self.infoWidget = ItemInfoWidget(media, media_type, origins)
        self.imageWidget = ItemImageWidget()

        layout = QHBoxLayout()

        layout.addWidget(self.imageWidget)
        layout.addWidget(self.infoWidget)

        self.setLayout(layout)


class ItemInfoWidget(QWidget):
    def __init__(self, media, media_type, origins):
        super().__init__()

        title = get_english_title_or_user_preferred(media["title"])
        media_format = media["format"]
        year = media["startDate"]["year"]
        url = f"https://anilist.co/{media_type.lower()}/{media['id']}"

        self.titleLabel = QLabel()
        self.titleLabel.setText(
            f'<a href="{url}">{title} ({clean_format(media_format)}, {year})</a>'
        )
        self.titleLabel.setOpenExternalLinks(True)
        self.titleLabel.setTextFormat(Qt.RichText)
        self.titleLabel.setTextInteractionFlags(
            Qt.TextBrowserInteraction | Qt.LinksAccessibleByMouse
        )

        layout = QVBoxLayout()

        layout.addWidget(self.titleLabel)

        self.setLayout(layout)


class ItemImageWidget(QWidget):
    def __init__(self, image_url=None):
        super().__init__()


class ItemScoreWidget(QWidget):
    def __init__(self, score):
        super().__init__()
