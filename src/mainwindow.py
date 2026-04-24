import sys

from PySide6.QtWidgets import QMainWindow, QTabWidget, QApplication

from ui.watchpartytab import WatchPartyTab


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("AniList Toolkit")
        self.mainView = MainView()
        self.setCentralWidget(self.mainView)


class MainView(QTabWidget):
    def __init__(self):
        super().__init__()
        # self.tabBar().hide()
        self.addTab(WatchPartyTab(), "Watch Party")


app = QApplication(sys.argv)
window = MainWindow()
window.show()
app.exec()
