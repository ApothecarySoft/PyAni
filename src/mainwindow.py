import sys

from PySide6.QtWidgets import QMainWindow, QTabWidget, QApplication

from ui.tabs.anihuntertab import AniHunterTab
from ui.tabs.whattowatchtab import WhatToWatchTab


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("AniList Toolkit")
        self.setMinimumSize(800, 600)
        self.resize(800, 800)
        self.mainView = MainView()
        self.setCentralWidget(self.mainView)

        # screen_geometry = self.screen().availableGeometry()
        # current_geometry = self.geometry()
        #
        # self.setGeometry(
        #     current_geometry.x(),
        #     screen_geometry.top(),
        #     current_geometry.width(),
        #     screen_geometry.height(),
        # )


class MainView(QTabWidget):
    def __init__(self):
        super().__init__()
        # self.tabBar().hide()
        self.addTab(WhatToWatchTab(), "What To Watch")
        self.addTab(AniHunterTab(), "AniHunter")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
