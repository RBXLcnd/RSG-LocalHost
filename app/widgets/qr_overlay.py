from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from app.widgets.buttons import AppButton


class QrView(QWidget):
    """Paints a QR matrix on a white tile. Integer module size keeps edges crisp."""

    QUIET = 4  # quiet-zone modules required by the QR spec

    def __init__(self, matrix: list[list[bool]], size: int = 236) -> None:
        super().__init__()
        self.matrix = matrix
        self.setFixedSize(size, size)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#ffffff"))
        painter.drawRoundedRect(self.rect(), 12, 12)

        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        count = len(self.matrix)
        module = max(1, self.width() // (count + self.QUIET * 2))
        origin = (self.width() - module * count) // 2
        dark = QColor("#050a14")
        for y, row in enumerate(self.matrix):
            for x, cell in enumerate(row):
                if cell:
                    painter.fillRect(QRect(origin + x * module, origin + y * module, module, module), dark)


class QrOverlay(QWidget):
    """Modal-style panel drawn over the main window. Esc, the Close button or a
    click outside the card dismiss it."""

    def __init__(self, parent: QWidget, on_copy: Callable[[str, QWidget], None]) -> None:
        super().__init__(parent)
        self._on_copy = on_copy
        self._tunnel = ""
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)

        self.card = QFrame()
        self.card.setObjectName("card")
        self.card.setFixedWidth(340)
        self.card_layout = QVBoxLayout(self.card)
        self.card_layout.setContentsMargins(26, 22, 26, 20)
        self.card_layout.setSpacing(10)

        title = QLabel("Tunnel QR code")
        title.setObjectName("qrTitle")
        hint = QLabel("Scan with your phone to get the address.")
        hint.setObjectName("fieldHint")
        hint.setWordWrap(True)
        self.address = QLabel("")
        self.address.setObjectName("pathLabel")
        self.address.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.address.setWordWrap(True)
        self.address.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        self.view_holder = QHBoxLayout()
        buttons = QHBoxLayout()
        buttons.setSpacing(10)
        copy = AppButton("Copy address", "copy", "secondary")
        copy.clicked.connect(lambda: self._on_copy(self._tunnel, copy))
        close = AppButton("Close", None, "ghost")
        close.clicked.connect(self.close_overlay)
        buttons.addWidget(copy, 1)
        buttons.addWidget(close)

        self.card_layout.addWidget(title)
        self.card_layout.addWidget(hint)
        self.card_layout.addSpacing(4)
        self.card_layout.addLayout(self.view_holder)
        self.card_layout.addWidget(self.address)
        self.card_layout.addSpacing(4)
        self.card_layout.addLayout(buttons)

        outer = QVBoxLayout(self)
        outer.addStretch()
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(self.card)
        row.addStretch()
        outer.addLayout(row)
        outer.addStretch()
        self.hide()

    def open_for(self, tunnel: str, matrix: list[list[bool]]) -> None:
        self._tunnel = tunnel
        self.address.setText(tunnel)
        while self.view_holder.count():
            item = self.view_holder.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.view_holder.addStretch()
        self.view_holder.addWidget(QrView(matrix))
        self.view_holder.addStretch()
        self.setGeometry(self.parentWidget().rect())
        self.raise_()
        self.show()
        self.setFocus()

    def close_overlay(self) -> None:
        self.hide()

    def paintEvent(self, event) -> None:
        QPainter(self).fillRect(self.rect(), QColor(3, 6, 13, 200))

    def mousePressEvent(self, event) -> None:
        if not self.card.geometry().contains(event.position().toPoint()):
            self.close_overlay()
        event.accept()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close_overlay()
            return
        super().keyPressEvent(event)
