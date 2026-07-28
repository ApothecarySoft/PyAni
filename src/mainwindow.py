import os.path
import sys

from PySide6.QtWidgets import QMainWindow, QTabWidget, QApplication

from database.db import LadybugManager
from recommender.cachefiles import get_cache_directory
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


class MainView(QTabWidget):
    def __init__(self):
        super().__init__()
        # self.tabBar().hide()
        self.addTab(WhatToWatchTab(), "What To Watch")
        self.addTab(AniHunterTab(), "AniHunter")


if __name__ == "__main__":
    app = QApplication(sys.argv)

    db_manager = LadybugManager()
    try:
        db_manager.initialize(f"{get_cache_directory()}{os.path.sep}db")
    except Exception as e:
        print(f"CRITICAL: Failed to initialize Neo4j: {e}", file=sys.stderr)
        sys.exit(1)

    window = MainWindow()
    window.show()

    db_manager.close()
    sys.exit(app.exec())
