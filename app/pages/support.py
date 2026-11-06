from __future__ import annotations

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget

from app import __version__
from app.core.changelog import FIX, IMPROVED, NEW, RELEASES, Release
from app.pages.base import Page, card, divider, section_label
from app.widgets.buttons import AppButton

ORIGINAL_AUTHOR = "s0m3thing_matters"
VERSION_AUTHOR = "Uno_de_tres"
DISCORD_URL = "https://discord.gg/rsgserver"
DONATE_URL = "https://rbxl-skin-gallery.onrender.com/donate"

TAG_LABELS = {NEW: "NEW", IMPROVED: "IMPROVED", FIX: "FIX"}


def _release_block(release: Release) -> QWidget:
    block = QWidget()
    col = QVBoxLayout(block)
    col.setContentsMargins(0, 0, 0, 0)
    col.setSpacing(8)

    head = QHBoxLayout()
    head.setSpacing(10)
    version = QLabel(f"v{release.version}")
    version.setObjectName("changeVersion")
    head.addWidget(version)
    if release.version == __version__:
        current = QLabel("CURRENT")
        current.setObjectName("changeCurrent")
        head.addWidget(current)
    head.addStretch()
    if release.date:
        date = QLabel(release.date)
        date.setObjectName("changeDate")
        head.addWidget(date)
    col.addLayout(head)

    for kind, text in release.notes:
        row = QHBoxLayout()
        row.setSpacing(10)
        tag = QLabel(TAG_LABELS.get(kind, kind.upper()))
        tag.setObjectName("changeTag")
        tag.setProperty("kind", kind)
        tag.setFixedWidth(82)
        tag.setAlignment(Qt.AlignmentFlag.AlignCenter)
        body = QLabel(text)
        body.setObjectName("fieldHint")
        body.setWordWrap(True)
        row.addWidget(tag, 0, Qt.AlignmentFlag.AlignTop)
        row.addWidget(body, 1)
        col.addLayout(row)
    return block


class SupportPage(Page):
    def __init__(self, window) -> None:
        super().__init__()
        self.window = window

        actions = QHBoxLayout()
        back = AppButton("Back", "back", "ghost")
        back.clicked.connect(lambda: window.navigate("overview"))
        actions.addWidget(back)
        self.add_header("Support", "Contact, credits, and community links.", actions, eyebrow="Help")

        columns = QHBoxLayout()
        columns.setSpacing(18)

        credits_box = QVBoxLayout()
        credits_box.setSpacing(16)
        credits_box.addWidget(section_label("Credits"))

        original_row = QVBoxLayout()
        original_row.setSpacing(2)
        original_label = QLabel("Originally made by")
        original_label.setObjectName("fieldLabel")
        original_row.addWidget(original_label)
        original_name = QLabel(ORIGINAL_AUTHOR)
        original_name.setObjectName("supportName")
        original_row.addWidget(original_name)
        credits_box.addLayout(original_row)

        version_row = QVBoxLayout()
        version_row.setSpacing(2)
        version_label = QLabel("Version made by")
        version_label.setObjectName("fieldLabel")
        version_row.addWidget(version_label)
        version_name = QLabel(VERSION_AUTHOR)
        version_name.setObjectName("supportName")
        version_row.addWidget(version_name)
        credits_box.addLayout(version_row)

        credits_box.addStretch()
        columns.addWidget(card(credits_box, (22, 20, 22, 20)), 1)

        discord_box = QVBoxLayout()
        discord_box.setSpacing(8)
        discord_box.addWidget(section_label("Discord"))
        discord_link = QLabel(DISCORD_URL)
        discord_link.setObjectName("supportLink")
        discord_link.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        discord_link.setWordWrap(True)
        discord_box.addWidget(discord_link)
        open_discord = AppButton("Open Discord", "globe", "primary")
        open_discord.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(DISCORD_URL)))
        discord_box.addWidget(open_discord)
        discord_box.addStretch()
        columns.addWidget(card(discord_box, (22, 20, 22, 20)), 1)

        self.root.addLayout(columns)

        donate_row = QHBoxLayout()
        donate_row.setSpacing(16)
        donate_text = QVBoxLayout()
        donate_text.setSpacing(4)
        donate_text.addWidget(section_label("Support the project"))
        donate_hint = QLabel("RSG LocalHost is free. If it helps you, a donation keeps it going. It is completely optional.")
        donate_hint.setObjectName("fieldHint")
        donate_hint.setWordWrap(True)
        donate_text.addWidget(donate_hint)
        donate_row.addLayout(donate_text, 1)
        donate = AppButton("Donate", "heart", "primary")
        donate.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(DONATE_URL)))
        donate_row.addWidget(donate, 0, Qt.AlignmentFlag.AlignVCenter)
        self.root.addWidget(card(donate_row, (22, 16, 22, 16)))

        log_box = QVBoxLayout()
        log_box.setSpacing(12)
        log_box.addWidget(section_label("Changelog"))
        scroll = QScrollArea()
        scroll.setObjectName("changeScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        body = QWidget()
        body.setObjectName("changeBody")
        body_col = QVBoxLayout(body)
        body_col.setContentsMargins(0, 0, 8, 0)
        body_col.setSpacing(14)
        for index, release in enumerate(RELEASES):
            if index:
                body_col.addWidget(divider())
            body_col.addWidget(_release_block(release))
        body_col.addStretch()
        scroll.setWidget(body)
        log_box.addWidget(scroll, 1)
        self.root.addWidget(card(log_box, (22, 18, 14, 16)), 1)
