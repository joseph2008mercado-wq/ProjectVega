"""A staged editor: nothing reaches the runtime until Save is accepted."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QSpinBox, QTabWidget, QVBoxLayout, QWidget,
)

from vega.music.fret_sets import FACTORY_FRET_SETS, FretSet, validate_sets


class FretSetEditor(QDialog):
    def __init__(self, sets: tuple[FretSet, ...], active: int = 1, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Fret Sets")
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.result_sets = validate_sets(sets)
        outer = QVBoxLayout(self)
        self.tabs = QTabWidget()
        self.names: list[QLineEdit] = []
        self.slots: list[list[QSpinBox]] = []
        for i, mapping in enumerate(sets):
            page = QWidget()
            layout = QVBoxLayout(page)
            layout.addWidget(QLabel("Name"))
            name = QLineEdit()
            name.setMaxLength(40)
            name.setAccessibleName(f"Set {i + 1} name")
            self.names.append(name)
            layout.addWidget(name)
            grid = QGridLayout()
            row = []
            for slot in range(8):
                spin = QSpinBox()
                spin.setRange(1, 24)
                spin.setAccessibleName(f"Set {i + 1} FACE_{slot + 1} fret")
                grid.addWidget(QLabel(f"FACE_{slot + 1}"), (slot // 4) * 2, slot % 4)
                grid.addWidget(spin, (slot // 4) * 2 + 1, slot % 4)
                row.append(spin)
            self.slots.append(row)
            layout.addLayout(grid)
            self.tabs.addTab(page, f"Set {i + 1}")
            self.set_fields(i, mapping)
        self.tabs.setCurrentIndex(active - 1)
        outer.addWidget(self.tabs)
        hint = QLabel("Frets 1–24. Duplicate values are allowed. No held buttons plays open strings.")
        hint.setWordWrap(True)
        outer.addWidget(hint)
        resets = QHBoxLayout()
        self.reset_this = QPushButton("Reset This Set")
        self.reset_all = QPushButton("Reset All Sets")
        resets.addWidget(self.reset_this)
        resets.addWidget(self.reset_all)
        outer.addLayout(resets)
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.reset_this.clicked.connect(lambda: self.reset_set(self.tabs.currentIndex()))
        self.reset_all.clicked.connect(self.reset_sets)
        outer.addWidget(self.buttons)
        self.resize(390, 350)

    def set_fields(self, index: int, mapping: FretSet) -> None:
        self.names[index].setText(mapping.name)
        for spin, fret in zip(self.slots[index], mapping.frets):
            spin.setValue(fret)

    def reset_set(self, index: int) -> None:
        self.set_fields(index, FACTORY_FRET_SETS[index])

    def reset_sets(self) -> None:
        for index in range(3):
            self.reset_set(index)

    def accept(self) -> None:
        # Interpret a still-focused spin edit before reading its value.
        for row in self.slots:
            for spin in row:
                spin.interpretText()
        self.result_sets = validate_sets(tuple(
            FretSet(name.text().strip() or f"Set {i + 1}", tuple(spin.value() for spin in self.slots[i]))
            for i, name in enumerate(self.names)
        ))
        super().accept()
