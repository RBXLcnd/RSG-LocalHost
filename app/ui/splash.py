from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QTimer, Signal

from app.core import motion
from PySide6.QtWidgets import QLabel, QProgressBar, QVBoxLayout, QWidget

from app.styles import palette
from app.widgets.brand import BrandMark, GlowBackground


class StartupSplash(QWidget):
    finished = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(420, 260)
        self._value = 0

        self.panel = GlowBackground(self)
        self.panel.radius = 14
        self.panel.setObjectName("splashPanel")
        self.panel.setGeometry(0, 0, self.width(), self.height())
        layout = QVBoxLayout(self.panel)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(12)

        mark = BrandMark(96)
        title = QLabel("LocalHost")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setObjectName("splashTitle")
        status = QLabel("Loading workspace")
        status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status.setObjectName("splashStatus")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setTextVisible(False)
        self.progress.setObjectName("splashProgress")

        layout.addStretch()
        layout.addWidget(mark, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(title)
        layout.addWidget(status)
        layout.addWidget(self.progress)
        layout.addStretch()

        self.setStyleSheet(
            palette.qss("""
            QLabel#splashTitle {
              color: #f4f8ff;
              font-family: "Bahnschrift", "Segoe UI";
              font-size: 20pt;
              font-weight: 650;
            }
            QLabel#splashStatus {
              color: #8ea2c7;
              font-family: "Bahnschrift", "Segoe UI";
              font-size: 9pt;
            }
            QProgressBar#splashProgress {
              background: #081022;
              border: 1px solid #173164;
              border-radius: 5px;
              min-height: 8px;
              max-height: 8px;
            }
            QProgressBar#splashProgress::chunk {
              background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #00b2ff, stop:1 #1f4fff);
              border-radius: 4px;
            }
            """)
        )

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)

    def start(self) -> None:
        self._center()
        self.show()
        if not motion.enabled():  # no motion: no fake loading bar, hand over at once
            self.progress.setValue(100)
            QTimer.singleShot(0, self.finished.emit)
            return
        self.timer.start(24)

    def _center(self) -> None:
        screen = self.screen()
        if not screen:
            return
        geo = screen.availableGeometry()
        self.move(
            geo.x() + (geo.width() - self.width()) // 2,
            geo.y() + (geo.height() - self.height()) // 2,
        )

    def _tick(self) -> None:
        if self._value < 72:
            self._value += 4
        elif self._value < 94:
            self._value += 2
        else:
            self._value += 1

        self.progress.setValue(min(self._value, 100))
        if self._value >= 100:
            self.timer.stop()
            self._fade_out()

    def _fade_out(self) -> None:
        self.anim = QPropertyAnimation(self, b"windowOpacity", self)
        self.anim.setDuration(160)
        self.anim.setStartValue(1.0)
        self.anim.setEndValue(0.0)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.finished.connect(self.finished.emit)
        self.anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
