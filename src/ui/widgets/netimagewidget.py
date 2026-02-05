from PySide6.QtGui import QPixmap, QPixmapCache
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PySide6.QtWidgets import QLabel


## Simple QWidget for displaying an image based on a URL. Images are cached for performance!
class NetImageWidget(QLabel):
    def __init__(self, url: str):
        super().__init__()
        self._manager = QNetworkAccessManager()
        self._manager.finished.connect(self.handle_finished)
        self._pixmap = QPixmap()
        self._url = url
        if QPixmapCache.find(url, self._pixmap):
            self.setPixmap(self._pixmap)
        else:
            self._manager.get(QNetworkRequest(url))

    def handle_finished(self, reply):
        if reply.error() != QNetworkReply.NetworkError.NoError:
            print("error: ", reply.errorString())
            return
        self._pixmap.loadFromData(reply.readAll())
        QPixmapCache.insert(self._url, self._pixmap)
        self.setPixmap(self._pixmap)
