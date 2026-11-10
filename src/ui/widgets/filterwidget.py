from PySide6.QtCore import Slot, Signal
from PySide6.QtWidgets import QHBoxLayout, QGroupBox, QCheckBox

from recommender.utils import clean_format


class FilterWidget(QGroupBox):
    OnToggled = Signal()

    def __init__(self, filters: list[str]):
        super().__init__()

        self._data = {f.lower(): True for f in filters}

        layout = QHBoxLayout()

        for f in filters:
            checkbox = QCheckBox(clean_format(f))
            checkbox.setChecked(True)
            checkbox.toggled.connect(self._on_toggled)
            layout.addWidget(checkbox)

        self.setLayout(layout)

    @Slot(bool)
    def _on_toggled(self, checked):
        sender = self.sender()
        if isinstance(sender, QCheckBox):
            self._data[sender.text().lower()] = checked
            self.OnToggled.emit()

    def get_data(self):
        return self._data
