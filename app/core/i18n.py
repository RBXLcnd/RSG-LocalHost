"""Language switch (English / Português).

All texts in the app are written in English. `tr()` looks them up in the Portuguese table
(app/core/i18n_pt.py) when the language is "pt" and returns them unchanged otherwise, so unknown
or dynamic text (file names, tunnel addresses, log lines) always stays as it is.

Qt hooks: `install_qt_hooks()` makes labels, buttons, tooltips, placeholders, menus and dialogs
translate whatever text they are given, and remembers the English original so the language can be
switched back and forth while the app is running (`retranslate_all()`). Widgets created later are
translated when they are first shown.
"""
from __future__ import annotations

import re

LANGUAGES = {"en": "English", "pt": "Português", "pt-BR": "Português (Brasil)", "es": "Español"}
SHORT = {"en": "EN", "pt": "PT", "pt-BR": "BR", "es": "ES"}  # letters on the language button

_lang = "en"
_cache: dict[str, str] = {}
EXACT: dict[str, str] = {}
PATTERNS: dict[str, str] = {}
_upper: dict[str, str] = {}
_reverse: dict[str, str] = {}
_patterns: list = []


def _tables(lang: str) -> tuple[dict[str, str], dict[str, str]]:
    """The (exact, pattern) translation tables of a language, imported when first needed."""
    if lang == "pt":
        from app.core import i18n_pt as module
    elif lang == "pt-BR":
        from app.core import i18n_ptbr as module
    elif lang == "es":
        from app.core import i18n_es as module
    else:
        return {}, {}
    return module.EXACT, module.PATTERNS


def _compile(template: str) -> re.Pattern[str]:
    parts = re.split(r"\{\d*\}", template)
    return re.compile("^" + "(.+?)".join(re.escape(p) for p in parts) + "$", re.DOTALL)


_table_re = re.compile(r'^(<table width="[^"]*"><tr><td>)(.*)(</td></tr></table>)$', re.DOTALL)


def get_language() -> str:
    return _lang


def set_language(lang: str) -> None:
    global _lang, EXACT, PATTERNS, _upper, _reverse, _patterns
    _lang = lang if lang in LANGUAGES else "en"
    EXACT, PATTERNS = _tables(_lang)
    _upper = {k.upper(): v for k, v in EXACT.items()}
    _reverse = {v: k for k, v in EXACT.items()}
    _patterns = sorted(((_compile(k), v) for k, v in PATTERNS.items()), key=lambda kv: -len(kv[0].pattern))
    _cache.clear()


def _fill(template: str, groups: tuple[str, ...]) -> str:
    counter = iter(groups)

    def put(match: re.Match[str]) -> str:
        index = match.group(1)
        value = groups[int(index) - 1] if index else next(counter, "")
        return tr(value)

    return re.sub(r"\{(\d*)\}", put, template)


def _translate(text: str) -> str:
    hit = EXACT.get(text)
    if hit is not None:
        return hit
    core = text.strip()
    if core != text and core:
        start = text.index(core)
        return text[:start] + tr(core) + text[start + len(core):]
    table = _table_re.match(text)
    if table:
        return table.group(1) + tr(table.group(2)) + table.group(3)
    if core.isupper():
        hit = _upper.get(core)
        if hit is not None:
            return hit.upper()
    for pattern, template in _patterns:
        match = pattern.match(text)
        if match:
            return _fill(template, match.groups())
    return text


def tr(text):
    """Translate `text` for the current language (non-strings pass through)."""
    if _lang == "en" or not isinstance(text, str) or not text.strip():
        return text
    hit = _cache.get(text)
    if hit is None:
        hit = _cache[text] = _translate(text)
    return hit


def untr(text: str) -> str:
    """Best effort back to English (exact table entries only)."""
    return _reverse.get(text, text) if isinstance(text, str) else text


# --------------------------------------------------------------------------------------
# Qt integration
# --------------------------------------------------------------------------------------
_installed = False
_actions: list = []  # QActions created through the patched QMenu.addAction

P_TEXT, P_TIP, P_HOLD = "_i18n_text", "_i18n_tip", "_i18n_ph"


def _remember(obj, prop: str, text) -> str:
    """Store the English source of `text` on the object (dynamic Qt property) and return it."""
    src = untr(text)
    try:
        obj.setProperty(prop, src)
    except Exception:
        pass
    return src


def install_qt_hooks() -> None:
    global _installed
    if _installed:
        return
    _installed = True

    from PySide6.QtCore import QEvent, QObject
    from PySide6.QtWidgets import (
        QAbstractButton, QApplication, QFileDialog, QInputDialog, QLabel, QLineEdit, QMenu, QMessageBox,
        QSystemTrayIcon, QWidget,
    )

    def wrap_setter(cls, name: str, prop: str) -> None:
        original = getattr(cls, name)

        def setter(self, text, *args, **kwargs):
            if isinstance(text, str):
                _remember(self, prop, text)
                text = tr(text)
            return original(self, text, *args, **kwargs)

        setattr(cls, name, setter)

    wrap_setter(QLabel, "setText", P_TEXT)
    wrap_setter(QAbstractButton, "setText", P_TEXT)
    wrap_setter(QLineEdit, "setPlaceholderText", P_HOLD)
    wrap_setter(QWidget, "setToolTip", P_TIP)
    wrap_setter(QWidget, "setWindowTitle", P_TEXT)
    wrap_setter(QMessageBox, "setText", P_TEXT)
    wrap_setter(QMessageBox, "setInformativeText", P_HOLD)

    tray_tip = QSystemTrayIcon.setToolTip
    QSystemTrayIcon.setToolTip = lambda self, text: tray_tip(self, tr(text))

    show_message = QSystemTrayIcon.showMessage

    def tray_show_message(self, title, message, *args, **kwargs):
        return show_message(self, tr(title), tr(message), *args, **kwargs)

    QSystemTrayIcon.showMessage = tray_show_message

    add_button = QMessageBox.addButton

    def message_add_button(self, *args):
        if args and isinstance(args[0], str):
            args = (tr(args[0]),) + args[1:]
        return add_button(self, *args)

    QMessageBox.addButton = message_add_button

    add_action = QMenu.addAction

    def menu_add_action(self, *args, **kwargs):
        text_index = next((i for i, a in enumerate(args) if isinstance(a, str)), None)
        source = None
        if text_index is not None:
            source = args[text_index]
            args = args[:text_index] + (tr(source),) + args[text_index + 1:]
        action = add_action(self, *args, **kwargs)
        if source is not None and action is not None:
            action.setProperty(P_TEXT, untr(source))
            _actions.append(action)
        return action

    QMenu.addAction = menu_add_action

    def wrap_static(cls, name: str, indexes: tuple[int, ...]) -> None:
        original = getattr(cls, name)

        def static(*args, **kwargs):
            args = list(args)
            for i in indexes:
                if i < len(args) and isinstance(args[i], str):
                    args[i] = tr(args[i])
            return original(*args, **kwargs)

        setattr(cls, name, staticmethod(static))

    wrap_static(QFileDialog, "getOpenFileName", (1, 3))
    wrap_static(QFileDialog, "getOpenFileNames", (1, 3))
    wrap_static(QFileDialog, "getSaveFileName", (1, 3))
    wrap_static(QInputDialog, "getText", (1, 2))

    label_set, button_set, edit_set, tip_set = QLabel.setText, QAbstractButton.setText, QLineEdit.setPlaceholderText, QWidget.setToolTip

    def retranslate_widget(widget) -> None:
        """Translate a widget from its English source (the source is its current text the first time)."""
        try:
            if isinstance(widget, QLabel):
                src = widget.property(P_TEXT) or widget.text()
                if src:
                    widget.setProperty(P_TEXT, untr(src))
                    label_set(widget, tr(untr(src)))
            elif isinstance(widget, QAbstractButton):
                src = widget.property(P_TEXT) or widget.text()
                if src:
                    widget.setProperty(P_TEXT, untr(src))
                    button_set(widget, tr(untr(src)))
            elif isinstance(widget, QLineEdit):
                src = widget.property(P_HOLD) or widget.placeholderText()
                if src:
                    widget.setProperty(P_HOLD, untr(src))
                    edit_set(widget, tr(untr(src)))
            tip = widget.property(P_TIP) or widget.toolTip()
            if tip:
                widget.setProperty(P_TIP, untr(tip))
                tip_set(widget, tr(untr(tip)))
        except RuntimeError:
            pass  # the C++ object is already gone

    class ShowFilter(QObject):
        def eventFilter(self, obj, event):
            if event.type() == QEvent.Type.Show and _lang != "en" and isinstance(obj, QWidget):
                retranslate_widget(obj)
            return False

    app = QApplication.instance()
    global _filter
    _filter = ShowFilter(app)
    app.installEventFilter(_filter)

    def retranslate_all() -> None:
        for widget in QApplication.allWidgets():
            retranslate_widget(widget)
        alive = []
        for action in _actions:
            try:
                src = action.property(P_TEXT)
                if src:
                    action.setText(tr(src))
                alive.append(action)
            except RuntimeError:
                pass
        _actions[:] = alive

    global _retranslate_all
    _retranslate_all = retranslate_all


_filter = None
_retranslate_all = None


def register_action(action, english: str) -> None:
    """A QAction built with a constructor text (tray menu): translate it now and on every language switch."""
    action.setProperty(P_TEXT, english)
    action.setText(tr(english))
    _actions.append(action)


def source_text(widget) -> str:
    """The English text of a label/button (what the code set), whatever language is showing."""
    return widget.property(P_TEXT) or widget.text()


def retranslate_all() -> None:
    """Re-apply the current language to every widget that exists right now."""
    if _retranslate_all is not None:
        _retranslate_all()
