import os
import sys
import json
import math
import logging
from datetime import datetime
from string import Template
import requests
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QPointF, QEvent, QTimer, QRect
from PyQt6.QtGui import QPainter, QColor, QFont, QPixmap, QIcon, QAction, QPolygonF, QPen, QGuiApplication
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QSlider, QScrollArea, QListWidget,
    QSpinBox, QFrame, QSizePolicy, QSpacerItem, QGraphicsDropShadowEffect,
    QSystemTrayIcon, QMenu,
    QDialog, QDialogButtonBox, QFormLayout, QComboBox, QCheckBox,
    QPlainTextEdit, QMessageBox, QListWidgetItem, QAbstractItemView
)
from metadata import MetadataFetcher
import i18n
from i18n import t

log = logging.getLogger('radiocast.gui')

# Shown in the About dialog and the window title hover.
APP_VERSION = "1.0.0"

def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

# Color palettes per theme. The purple accent (#7c3aed family) is shared by both.
PALETTES = {
    "dark": {
        "window_bg": "#0d0d11", "panel_bg": "#13131a", "border": "#23232f",
        "text": "#e2e2e9", "text_strong": "#ffffff", "text_muted": "#9ca3af", "text_faint": "#6b7280",
        "card_bg": "#1c1c24", "card_border": "#2a2a35", "card_selected_bg": "#242038",
        "card_hover_bg": "#252530", "card_hover_border": "#3f3f50",
        "input_focus_bg": "#202029",
        "btn_bg": "#252530", "btn_border": "#323242", "btn_hover_bg": "#2d2d3a",
        "btn_hover_border": "#4b5563", "btn_pressed_bg": "#1c1c24",
        "scroll_handle": "#2a2a35", "scroll_handle_hover": "#4b5563", "logo_bg": "#13131a",
    },
    "light": {
        "window_bg": "#f4f4f7", "panel_bg": "#ffffff", "border": "#e2e2e8",
        "text": "#1f2330", "text_strong": "#0d0d11", "text_muted": "#6b7280", "text_faint": "#9ca3af",
        "card_bg": "#ffffff", "card_border": "#e2e2e8", "card_selected_bg": "#f3effe",
        "card_hover_bg": "#f0f0f4", "card_hover_border": "#c9c9d4",
        "input_focus_bg": "#ffffff",
        "btn_bg": "#ffffff", "btn_border": "#d8d8e0", "btn_hover_bg": "#f0f0f4",
        "btn_hover_border": "#c9c9d4", "btn_pressed_bg": "#e8e8ee",
        "scroll_handle": "#d0d0d8", "scroll_handle_hover": "#b0b0bc", "logo_bg": "#eeeef2",
    },
}

# Stylesheet template; $tokens are filled from the active palette (string.Template).
_STYLE_TEMPLATE = Template("""
QMainWindow {
    background-color: $window_bg;
}
QWidget {
    color: $text;
    font-family: 'Segoe UI', -apple-system, sans-serif;
    font-size: 13px;
}
QFrame#sidebar {
    background-color: $panel_bg;
    border-right: 1px solid $border;
}
QFrame#playbar {
    background-color: $panel_bg;
    border-top: 1px solid $border;
}
QFrame#recentPanel {
    background-color: $panel_bg;
    border-left: 1px solid $border;
}
QScrollArea {
    border: none;
    background-color: transparent;
}
QWidget#scrollContent {
    background-color: transparent;
}
/* Station Card styling */
QFrame#stationCard {
    background-color: $card_bg;
    border: 1px solid $card_border;
    border-radius: 12px;
}
QFrame#stationCard[selected="true"] {
    border: 2px solid #7c3aed;
    background-color: $card_selected_bg;
}
QFrame#stationCard:hover {
    background-color: $card_hover_bg;
    border-color: $card_hover_border;
}
QLabel#cardLogo {
    border-radius: 8px;
    background-color: $logo_bg;
}
QLabel#stationTitle {
    font-size: 15px;
    font-weight: bold;
    color: $text_strong;
}
QLabel#stationGenre {
    font-size: 11px;
    font-weight: bold;
    color: #a78bfa;
    background-color: #2e1065;
    border-radius: 6px;
    padding: 3px 8px;
}
QLabel#stationDesc {
    font-size: 12px;
    color: $text_muted;
}
/* Custom Scrollbars */
QScrollBar:vertical {
    background-color: transparent;
    width: 8px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background-color: $scroll_handle;
    min-height: 20px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background-color: $scroll_handle_hover;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
}
/* Input search field */
QLineEdit#searchBar {
    background-color: $card_bg;
    border: 1px solid $card_border;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 13px;
    color: $text_strong;
}
QLineEdit#searchBar:focus {
    border: 1px solid #7c3aed;
    background-color: $input_focus_bg;
}
/* Standard Buttons */
QPushButton {
    background-color: $btn_bg;
    border: 1px solid $btn_border;
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: bold;
    color: $text;
}
QPushButton:hover {
    background-color: $btn_hover_bg;
    border-color: $btn_hover_border;
}
QPushButton:pressed {
    background-color: $btn_pressed_bg;
}
QPushButton#scanBtn {
    background-color: #7c3aed;
    border: none;
    color: #ffffff;
}
QPushButton#scanBtn:hover {
    background-color: #8b5cf6;
}
QPushButton#scanBtn:pressed {
    background-color: #6d28d9;
}
QPushButton#scanBtn:disabled {
    background-color: #4c1d95;
    color: #c4b5fd;
}
/* Media Buttons */
QPushButton#playBtn {
    background-color: #7c3aed;
    border: none;
    border-radius: 20px;
    padding: 0px;
}
QPushButton#playBtn:hover {
    background-color: #8b5cf6;
}
QPushButton#playBtn:pressed {
    background-color: #6d28d9;
}
QPushButton#playBtn:disabled {
    background-color: $btn_border;
}
/* Device list */
QListWidget#deviceList {
    background-color: $card_bg;
    border: 1px solid $card_border;
    border-radius: 8px;
    padding: 4px;
    color: $text;
    outline: none;
}
QListWidget#deviceList::item {
    padding: 8px 10px;
    border-radius: 6px;
    margin: 2px;
}
QListWidget#deviceList::item:hover {
    background-color: $card_hover_bg;
}
QListWidget#deviceList::item:selected {
    background-color: #7c3aed;
    color: #ffffff;
}
/* Recently played history list */
QListWidget#recentList {
    background-color: $card_bg;
    border: 1px solid $card_border;
    border-radius: 8px;
    padding: 4px;
    color: $text;
    outline: none;
    font-size: 11px;
}
QListWidget#recentList::item {
    padding: 6px 8px;
    border-radius: 6px;
    margin: 1px;
}
/* Favorite toggle on cards */
QPushButton#favBtn {
    background-color: transparent;
    border: none;
    padding: 0px;
}
QPushButton#favBtn:hover {
    background-color: $card_hover_bg;
    border-radius: 14px;
}
/* Theme toggle */
QPushButton#themeBtn {
    background-color: $btn_bg;
    border: 1px solid $btn_border;
    border-radius: 8px;
    padding: 6px 12px;
    color: $text;
}
QPushButton#themeBtn:hover {
    background-color: $btn_hover_bg;
    border-color: $btn_hover_border;
}
/* Favorites filter button */
QPushButton#favFilterBtn {
    background-color: $card_bg;
    border: 1px solid $card_border;
    border-radius: 8px;
    padding: 8px 14px;
    color: $text_muted;
}
QPushButton#favFilterBtn:checked {
    background-color: #2e1065;
    border-color: #7c3aed;
    color: #fbbf24;
}
/* Sidebar & playbar labels (themed via object names) */
QLabel#appTitle { font-size: 22px; font-weight: 800; color: $text_strong; }
QFrame#sep { background-color: $border; border: none; }
QLabel#sectionLabel, QLabel#sectionLabelMt { font-size: 11px; font-weight: bold; color: $text_faint; }
QLabel#sectionLabelMt { margin-top: 15px; }
QFrame#statusFrame { background-color: $card_bg; border-radius: 8px; border: 1px solid $card_border; }
QLabel#statusLabel { font-size: 12px; color: $text; }
QLabel#helpNote { font-size: 11px; color: $text_faint; }
QLabel#aboutVersion { font-size: 12px; font-weight: bold; color: #a78bfa; }
QLabel#aboutBody { font-size: 13px; color: $text; }
QLabel#aboutMeta { font-size: 12px; color: $text_muted; }
QLabel#pbLogo { border-radius: 6px; background-color: $logo_bg; }
QLabel#pbTitle { font-size: 14px; font-weight: bold; color: $text_strong; }
QLabel#pbDesc { font-size: 11px; color: $text_muted; }
QLabel#pbTrack { font-size: 11px; font-weight: bold; color: #7c3aed; }
QLabel#stateLabel { font-size: 10px; font-weight: bold; color: $text_muted; }
/* Proxy port input */
QSpinBox#portSpin {
    background-color: $card_bg;
    border: 1px solid $card_border;
    border-radius: 6px;
    padding: 4px 6px;
    color: $text;
}
QSpinBox#portSpin:focus {
    border: 1px solid #7c3aed;
}
QPushButton#applyPortBtn {
    padding: 5px 12px;
}
/* Sliders */
QSlider::groove:horizontal {
    height: 4px;
    background: $card_border;
    border-radius: 2px;
}
QSlider::sub-page:horizontal {
    background: #7c3aed;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #7c3aed;
    width: 12px;
    height: 12px;
    margin: -4px 0;
    border-radius: 6px;
}
QSlider::handle:horizontal:hover {
    background: #c084fc;
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}
""")

def build_stylesheet(theme):
    """Builds the full QSS for the given theme name, falling back to dark."""
    palette = PALETTES.get(theme, PALETTES["dark"])
    return _STYLE_TEMPLATE.substitute(palette)

class LogoDownloader(QThread):
    """Downloads logos asynchronously and emits data to prevent GUI thread block."""
    logo_downloaded = pyqtSignal(str, bytes)

    def __init__(self, station_id, url):
        super().__init__()
        self.station_id = station_id
        self.url = url

    def run(self):
        try:
            if not self.url or "favicons" in self.url:
                # We skip Google's favicon service redirects to use beautiful fallback colors
                return
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            r = requests.get(self.url, headers=headers, timeout=5)
            if r.status_code == 200 and len(r.content) > 0:
                self.logo_downloaded.emit(self.station_id, r.content)
        except Exception:
            pass

def create_fallback_logo(name):
    """Draws a beautiful initials-based colorful logo dynamically when URL is missing or fails."""
    pixmap = QPixmap(100, 100)
    pixmap.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    # Selection of modern pastel/deep colors based on name hash
    colors = [
        QColor('#6d28d9'), QColor('#0369a1'), QColor('#0f766e'),
        QColor('#b45309'), QColor('#be123c'), QColor('#1d4ed8'),
        QColor('#047857'), QColor('#a21caf'), QColor('#c2410c')
    ]
    color_index = abs(hash(name)) % len(colors)
    bg_color = colors[color_index]
    
    # Draw rounded rect background
    painter.setBrush(bg_color)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(5, 5, 90, 90, 16, 16)
    
    # Draw initials text
    painter.setPen(QColor('#ffffff'))
    font = QFont('Segoe UI', 30, QFont.Weight.Bold)
    painter.setFont(font)
    
    initials = "".join([part[0] for part in name.split() if part])[:2].upper()
    painter.drawText(5, 5, 90, 90, Qt.AlignmentFlag.AlignCenter, initials)
    painter.end()
    
    return pixmap

def create_star_icon(filled):
    """Draws a star icon (filled gold when favorite, outlined grey otherwise)."""
    pixmap = QPixmap(24, 24)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    cx, cy, outer, inner = 12, 12, 9.5, 4.0
    points = []
    for i in range(10):
        angle = -math.pi / 2 + i * math.pi / 5
        radius = outer if i % 2 == 0 else inner
        points.append(QPointF(cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    star = QPolygonF(points)

    if filled:
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor('#fbbf24'))
    else:
        pen = QPen(QColor('#6b7280'))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.setBrush(Qt.GlobalColor.transparent)
    painter.drawPolygon(star)
    painter.end()
    return pixmap

def slugify(name):
    """Turns a station name into a url-safe ascii id (e.g. 'Radio ZU' -> 'radio-zu')."""
    import re
    import unicodedata
    # Strip diacritics (ă -> a, ț -> t, ...) then keep alphanumerics
    normalized = unicodedata.normalize('NFKD', name)
    ascii_name = normalized.encode('ascii', 'ignore').decode('ascii').lower()
    slug = re.sub(r'[^a-z0-9]+', '-', ascii_name).strip('-')
    return slug or 'post'


# Content types offered in the editor; the stream's actual header still wins at playback.
CONTENT_TYPES = ["audio/mpeg", "audio/aac", "audio/ogg", "audio/x-mpegurl"]


class StationFormDialog(QDialog):
    """Add/edit form for a single radio station. Returns a station dict via get_data()."""

    def __init__(self, parent=None, station=None, existing_ids=None):
        super().__init__(parent)
        # station is None for "add", or the dict being edited for "edit".
        self.station = station
        self.existing_ids = existing_ids or set()
        self.is_edit = station is not None

        self.setWindowTitle(t("form.title_edit") if self.is_edit else t("form.title_add"))
        self.setMinimumWidth(460)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        form = QFormLayout()
        form.setSpacing(10)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        s = self.station or {}

        self.name_input = QLineEdit(s.get('name', ''), self)
        self.name_input.setPlaceholderText(t("form.name_ph"))
        form.addRow(t("form.name"), self.name_input)

        self.genre_input = QLineEdit(s.get('genre', ''), self)
        self.genre_input.setPlaceholderText(t("form.genre_ph"))
        form.addRow(t("form.genre"), self.genre_input)

        self.desc_input = QPlainTextEdit(s.get('description', ''), self)
        self.desc_input.setPlaceholderText(t("form.description_ph"))
        self.desc_input.setFixedHeight(64)
        form.addRow(t("form.description"), self.desc_input)

        self.url_input = QLineEdit(s.get('url', ''), self)
        self.url_input.setPlaceholderText(t("form.url_ph"))
        form.addRow(t("form.url"), self.url_input)

        self.logo_input = QLineEdit(s.get('logo') or '', self)
        self.logo_input.setPlaceholderText(t("form.logo_ph"))
        form.addRow(t("form.logo"), self.logo_input)

        self.type_combo = QComboBox(self)
        self.type_combo.setEditable(True)
        self.type_combo.addItems(CONTENT_TYPES)
        current_type = s.get('content_type', 'audio/mpeg')
        if current_type in CONTENT_TYPES:
            self.type_combo.setCurrentText(current_type)
        else:
            self.type_combo.setEditText(current_type)
        form.addRow(t("form.content_type"), self.type_combo)

        self.proxy_check = QCheckBox(t("form.proxy_checkbox"), self)
        self.proxy_check.setChecked(bool(s.get('proxy', False)))
        form.addRow(t("form.proxy_label"), self.proxy_check)

        layout.addLayout(form)

        # OK / Cancel
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel,
            self
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText(t("common.save"))
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(t("common.cancel"))
        buttons.accepted.connect(self.on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def on_accept(self):
        name = self.name_input.text().strip()
        url = self.url_input.text().strip()

        if not name:
            QMessageBox.warning(self, t("form.required_title"), t("form.name_required"))
            return
        if not url:
            QMessageBox.warning(self, t("form.required_title"), t("form.url_required"))
            return

        # Keep the existing id when editing; generate a unique one when adding.
        if self.is_edit:
            station_id = self.station['id']
        else:
            station_id = self._unique_id(slugify(name))

        self.result_data = {
            'id': station_id,
            'name': name,
            'description': self.desc_input.toPlainText().strip(),
            'genre': self.genre_input.text().strip() or t("common.general"),
            'url': url,
            'logo': self.logo_input.text().strip() or None,
            'content_type': self.type_combo.currentText().strip() or 'audio/mpeg',
            'proxy': self.proxy_check.isChecked(),
        }
        self.accept()

    def _unique_id(self, base):
        """Appends -2, -3, ... if the slug collides with an existing station id."""
        if base not in self.existing_ids:
            return base
        i = 2
        while f"{base}-{i}" in self.existing_ids:
            i += 1
        return f"{base}-{i}"

    def get_data(self):
        return self.result_data


class StationManagerDialog(QDialog):
    """Lists all stations with Add / Edit / Delete actions, delegating persistence
    to the parent MainWindow."""

    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.setWindowTitle(t("manager.title"))
        self.setMinimumSize(420, 480)
        self.init_ui()
        self.refresh_list()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title = QLabel(t("manager.heading"), self)
        title.setObjectName("appTitle")
        layout.addWidget(title)

        self.list_widget = QListWidget(self)
        self.list_widget.setObjectName("deviceList")
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.list_widget.itemDoubleClicked.connect(lambda *_: self.edit_selected())
        layout.addWidget(self.list_widget)

        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self.add_btn = QPushButton(t("manager.add"), self)
        self.add_btn.setObjectName("scanBtn")
        self.add_btn.clicked.connect(self.add_station)
        btn_row.addWidget(self.add_btn)

        self.edit_btn = QPushButton(t("manager.edit"), self)
        self.edit_btn.clicked.connect(self.edit_selected)
        btn_row.addWidget(self.edit_btn)

        self.delete_btn = QPushButton(t("manager.delete"), self)
        self.delete_btn.clicked.connect(self.delete_selected)
        btn_row.addWidget(self.delete_btn)
        layout.addLayout(btn_row)

        close_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, self)
        close_box.button(QDialogButtonBox.StandardButton.Close).setText(t("common.close"))
        close_box.rejected.connect(self.accept)
        layout.addWidget(close_box)

    def refresh_list(self):
        self.list_widget.clear()
        for station in self.window.sorted_stations():
            label = station.get('name', t("manager.no_name"))
            genre = station.get('genre')
            if genre:
                label += f"  —  {genre}"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, station['id'])
            self.list_widget.addItem(item)

    def _selected_station(self):
        item = self.list_widget.currentItem()
        if not item:
            return None
        station_id = item.data(Qt.ItemDataRole.UserRole)
        return next((s for s in self.window.stations if s['id'] == station_id), None)

    def add_station(self):
        existing_ids = {s['id'] for s in self.window.stations}
        dialog = StationFormDialog(self, station=None, existing_ids=existing_ids)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.window.add_station(dialog.get_data())
            self.refresh_list()

    def edit_selected(self):
        station = self._selected_station()
        if not station:
            QMessageBox.information(self, t("manager.select_title"), t("manager.select_to_edit"))
            return
        existing_ids = {s['id'] for s in self.window.stations}
        dialog = StationFormDialog(self, station=station, existing_ids=existing_ids)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.window.update_station(station['id'], dialog.get_data())
            self.refresh_list()

    def delete_selected(self):
        station = self._selected_station()
        if not station:
            QMessageBox.information(self, t("manager.select_title"), t("manager.select_to_delete"))
            return
        reply = QMessageBox.question(
            self, t("manager.confirm_delete_title"),
            t("manager.confirm_delete_msg", name=station['name']),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.window.delete_station(station['id'])
            self.refresh_list()


class AboutDialog(QDialog):
    """Simple 'About' window: app branding, version, description and credits."""

    def __init__(self, parent=None, app_icon=None):
        super().__init__(parent)
        self.setWindowTitle(t("about.title"))
        self.setMinimumWidth(420)
        self.init_ui(app_icon)

    def init_ui(self, app_icon):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 24)
        layout.setSpacing(12)

        # Logo + name header, centered
        if app_icon is not None and not app_icon.isNull():
            logo = QLabel(self)
            logo.setPixmap(app_icon.pixmap(72, 72))
            logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(logo)

        name = QLabel("RadioCast", self)
        name.setObjectName("appTitle")
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(name)

        version = QLabel(t("about.version", version=APP_VERSION), self)
        version.setObjectName("aboutVersion")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version)

        tagline = QLabel(t("about.tagline"), self)
        tagline.setObjectName("aboutMeta")
        tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tagline.setWordWrap(True)
        layout.addWidget(tagline)

        sep = QFrame(self)
        sep.setObjectName("sep")
        sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep)

        body = QLabel(t("about.description"), self)
        body.setObjectName("aboutBody")
        body.setWordWrap(True)
        layout.addWidget(body)

        author = QLabel(t("about.author"), self)
        author.setObjectName("aboutMeta")
        author.setWordWrap(True)
        author.setOpenExternalLinks(True)
        author.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(author)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, self)
        buttons.button(QDialogButtonBox.StandardButton.Close).setText(t("common.close"))
        buttons.rejected.connect(self.accept)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)


class StationCard(QFrame):
    """Individual widget representing a radio station in a card layout."""
    clicked = pyqtSignal(dict)
    double_clicked = pyqtSignal(dict)
    favorite_toggled = pyqtSignal(dict, bool)

    def __init__(self, station_data):
        super().__init__()
        self.station_data = station_data
        self.is_favorite = bool(station_data.get('favorite', False))
        self.setObjectName("stationCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setProperty("selected", "false")
        # Keep a constant tile width so cards never stretch to fill the row,
        # even when a single station is shown.
        self.setFixedWidth(280)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Top bar with favorite (star) toggle, right-aligned
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)
        top_bar.addStretch()
        self.fav_btn = QPushButton(self)
        self.fav_btn.setObjectName("favBtn")
        self.fav_btn.setFixedSize(28, 28)
        self.fav_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.fav_btn.setToolTip(t("card.add_fav"))
        self.fav_btn.clicked.connect(self.toggle_favorite)
        self.update_fav_icon()
        top_bar.addWidget(self.fav_btn)
        layout.addLayout(top_bar)

        # Image/Logo Label
        self.logo_label = QLabel(self)
        self.logo_label.setObjectName("cardLogo")
        self.logo_label.setFixedSize(100, 100)
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Default logo while downloading or as fallback
        self.set_logo_pixmap(create_fallback_logo(self.station_data['name']))
        
        # Centering the logo label inside card layout
        logo_layout = QHBoxLayout()
        logo_layout.addStretch()
        logo_layout.addWidget(self.logo_label)
        logo_layout.addStretch()
        layout.addLayout(logo_layout)

        # Title
        self.title_label = QLabel(self.station_data['name'], self)
        self.title_label.setObjectName("stationTitle")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setWordWrap(True)
        layout.addWidget(self.title_label)

        # Genre badge layout
        genre_layout = QHBoxLayout()
        genre_layout.addStretch()
        self.genre_label = QLabel(self.station_data.get('genre', t("common.general")), self)
        self.genre_label.setObjectName("stationGenre")
        self.genre_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        genre_layout.addWidget(self.genre_label)
        genre_layout.addStretch()
        layout.addLayout(genre_layout)

        # Description
        desc_text = self.station_data.get('description', '')
        if len(desc_text) > 60:
            desc_text = desc_text[:57] + "..."
        self.desc_label = QLabel(desc_text, self)
        self.desc_label.setObjectName("stationDesc")
        self.desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.desc_label.setWordWrap(True)
        layout.addWidget(self.desc_label)

        # Fix spacing at the bottom
        layout.addStretch()

    def set_logo_pixmap(self, pixmap):
        self.logo_label.setPixmap(pixmap.scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def set_selected(self, selected):
        self.setProperty("selected", "true" if selected else "false")
        self.style().unpolish(self)
        self.style().polish(self)

    def update_fav_icon(self):
        self.fav_btn.setIcon(QIcon(create_star_icon(self.is_favorite)))
        self.fav_btn.setIconSize(QSize(20, 20))
        self.fav_btn.setToolTip(t("card.remove_fav") if self.is_favorite else t("card.add_fav"))

    def toggle_favorite(self):
        self.is_favorite = not self.is_favorite
        self.station_data['favorite'] = self.is_favorite
        self.update_fav_icon()
        self.favorite_toggled.emit(self.station_data, self.is_favorite)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.station_data)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit(self.station_data)

class MainWindow(QMainWindow):
    """Main window of the RadioChromecast application."""

    MAX_RECENT = 5  # number of "recently played" tracks kept in the sidebar

    def __init__(self, stations, cast_controller, proxy_server, stations_path=None, config=None):
        super().__init__()
        self.stations = stations
        self.cast_controller = cast_controller
        self.proxy_server = proxy_server
        self.stations_path = stations_path
        self.config = config if config is not None else {}

        # Active theme ("dark" or "light"); persisted in config.json
        self.theme = self.config.get('theme', 'dark')
        if self.theme not in PALETTES:
            self.theme = 'dark'
        self.palette_colors = PALETTES[self.theme]

        # Load saved favorites; ordering (favorites first, then alphabetical) is
        # applied by sorted_stations() when the grid is built.
        self.load_favorites()

        self.selected_station = None
        self.active_station = None
        self.is_playing = False
        self.is_muted = False
        self.current_volume = 0.5
        # Tracks the current connection so retranslate_ui() can restore the right
        # default status text when the user switches language while idle.
        self._is_connected = False

        # Auto-reconnect to the last used device / resume the last station, once
        self._auto_connect_pending = bool(self.config.get('last_device'))
        self._auto_play_pending = bool(self.config.get('last_station'))

        self.card_widgets = {}
        self.downloaders = []
        self.metadata_fetcher = None
        # Recently played history: newest first, capped at MAX_RECENT. Each entry
        # is {'title', 'station', 'time'} so we can show relative timestamps.
        self.recent_entries = []

        self.setWindowTitle("RadioChromecast")
        self.setMinimumSize(1000, 700)
        self.setStyleSheet(build_stylesheet(self.theme))

        # Set window icon
        icon_path = get_resource_path("icon.png")
        self.app_icon = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()
        if not self.app_icon.isNull():
            self.setWindowIcon(self.app_icon)

        # When True, closeEvent really quits instead of hiding to the tray.
        self._really_quit = False

        self.init_ui()
        self.setup_connections()
        self.setup_tray()
        self.restore_window_geometry()

        # Preselect the last played station (highlight + playbar); playback resumes
        # automatically once the Chromecast connects (see on_connection_status_changed)
        self.select_last_station()

        # Start initial discovery of Chromecast devices
        self.scan_chromecasts()

    def select_last_station(self):
        last_id = self.config.get('last_station')
        if not last_id:
            return
        station = next((s for s in self.stations if s.get('id') == last_id), None)
        if station and station['id'] in self.card_widgets:
            self.select_station(station)

    def init_ui(self):
        # Central widget
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Upper container (Sidebar + Content)
        upper_layout = QHBoxLayout()
        upper_layout.setSpacing(0)

        # --- Sidebar (Chromecast controls) ---
        sidebar = QFrame(self)
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(280)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(20, 30, 20, 30)
        sidebar_layout.setSpacing(20)

        # App Logo & Name. The title sits on its own row above the compact
        # control buttons so a longer name is never overlapped by them.
        header_layout = QVBoxLayout()
        header_layout.setSpacing(10)

        self.app_title = QLabel("RadioCast", self)
        self.app_title.setObjectName("appTitle")
        header_layout.addWidget(self.app_title)

        # Compact control buttons, right-aligned: About / language / theme.
        controls_row = QHBoxLayout()
        controls_row.setSpacing(8)
        controls_row.addStretch()

        # About button (ⓘ) — opens the About dialog
        self.about_btn = QPushButton("ⓘ", self)
        self.about_btn.setObjectName("themeBtn")
        self.about_btn.setFixedSize(34, 30)
        self.about_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.about_btn.setToolTip(t("about.tooltip"))
        controls_row.addWidget(self.about_btn)

        # Language toggle button (RO / EN)
        self.lang_btn = QPushButton(self)
        self.lang_btn.setObjectName("themeBtn")
        self.lang_btn.setFixedSize(40, 30)
        self.lang_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_lang_button()
        controls_row.addWidget(self.lang_btn)

        # Theme toggle button
        self.theme_btn = QPushButton(self)
        self.theme_btn.setObjectName("themeBtn")
        self.theme_btn.setFixedSize(34, 30)
        self.theme_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_theme_button()
        controls_row.addWidget(self.theme_btn)

        header_layout.addLayout(controls_row)
        sidebar_layout.addLayout(header_layout)

        # Separator line
        sep = QFrame()
        sep.setObjectName("sep")
        sep.setFrameShape(QFrame.Shape.HLine)
        sidebar_layout.addWidget(sep)

        # Chromecast Title Section
        self.cast_section_label = QLabel(t("sidebar.devices"), self)
        self.cast_section_label.setObjectName("sectionLabel")
        sidebar_layout.addWidget(self.cast_section_label)

        # Chromecast Device List
        self.device_list = QListWidget(self)
        self.device_list.setObjectName("deviceList")
        self.device_list.setMaximumHeight(180)
        self.device_list.addItem(t("sidebar.disconnected_item"))
        self.device_list.setCurrentRow(0)
        sidebar_layout.addWidget(self.device_list)

        # Scan Button
        self.scan_btn = QPushButton(t("sidebar.scan"), self)
        self.scan_btn.setObjectName("scanBtn")
        sidebar_layout.addWidget(self.scan_btn)

        # Chromecast connection status display
        self.status_title = QLabel(t("sidebar.connection_status"), self)
        self.status_title.setObjectName("sectionLabelMt")
        sidebar_layout.addWidget(self.status_title)

        # Status badge frame
        self.status_frame = QFrame(self)
        self.status_frame.setObjectName("statusFrame")
        status_frame_layout = QHBoxLayout(self.status_frame)
        status_frame_layout.setContentsMargins(10, 10, 10, 10)
        
        # Status LED
        self.status_led = QFrame(self)
        self.status_led.setFixedSize(10, 10)
        self.set_led_state("grey")
        status_frame_layout.addWidget(self.status_led)

        self.status_label = QLabel(t("sidebar.not_connected"), self)
        self.status_label.setObjectName("statusLabel")
        self.status_label.setWordWrap(True)
        status_frame_layout.addWidget(self.status_label)
        sidebar_layout.addWidget(self.status_frame)

        # Settings section: proxy port
        self.settings_label = QLabel(t("sidebar.settings"), self)
        self.settings_label.setObjectName("sectionLabelMt")
        sidebar_layout.addWidget(self.settings_label)

        port_row = QHBoxLayout()
        port_row.setSpacing(8)
        self.port_label = QLabel(t("sidebar.proxy_port"), self)
        self.port_label.setObjectName("statusLabel")
        port_row.addWidget(self.port_label)

        self.port_spin = QSpinBox(self)
        self.port_spin.setObjectName("portSpin")
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(self.proxy_server.port)
        port_row.addWidget(self.port_spin)

        self.apply_port_btn = QPushButton(t("sidebar.apply"), self)
        self.apply_port_btn.setObjectName("applyPortBtn")
        port_row.addWidget(self.apply_port_btn)
        sidebar_layout.addLayout(port_row)

        # Spacer to push everything to the top
        sidebar_layout.addStretch()

        # Instructions / Help note
        self.help_note = QLabel(t("sidebar.help_note"), self)
        self.help_note.setObjectName("helpNote")
        self.help_note.setWordWrap(True)
        sidebar_layout.addWidget(self.help_note)

        upper_layout.addWidget(sidebar)

        # --- Content Area (Stations list) ---
        content_widget = QWidget(self)
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(30, 30, 30, 30)
        content_layout.setSpacing(20)

        # Search bar header
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit(self)
        self.search_input.setObjectName("searchBar")
        self.search_input.setPlaceholderText(t("content.search_ph"))
        search_layout.addWidget(self.search_input)

        # Favorites-only filter toggle
        self.fav_filter_btn = QPushButton(t("content.fav_filter"), self)
        self.fav_filter_btn.setObjectName("favFilterBtn")
        self.fav_filter_btn.setCheckable(True)
        self.fav_filter_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        search_layout.addWidget(self.fav_filter_btn)

        # Open the CRUD manager for radio stations
        self.manage_btn = QPushButton(t("content.manage"), self)
        self.manage_btn.setObjectName("scanBtn")
        self.manage_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.manage_btn.setToolTip(t("content.manage_tooltip"))
        search_layout.addWidget(self.manage_btn)

        content_layout.addLayout(search_layout)

        # Scroll Area for station cards
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        
        self.scroll_content = QWidget()
        self.scroll_content.setObjectName("scrollContent")
        self.grid_layout = QGridLayout(self.scroll_content)
        self.grid_layout.setSpacing(15)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        
        # Populate radio stations grid
        self.populate_grid(self.stations)
        
        scroll_area.setWidget(self.scroll_content)
        content_layout.addWidget(scroll_area)

        upper_layout.addWidget(content_widget)

        # --- Recently played panel (right side) ---
        # In-app history of the last few "now playing" titles, mirroring the
        # Windows notifications. Lives in its own panel so the left sidebar stays
        # focused on the Chromecast connection.
        recent_panel = QFrame(self)
        recent_panel.setObjectName("recentPanel")
        recent_panel.setFixedWidth(240)
        recent_panel_layout = QVBoxLayout(recent_panel)
        recent_panel_layout.setContentsMargins(20, 30, 20, 30)
        recent_panel_layout.setSpacing(12)

        self.recent_title = QLabel(t("sidebar.recent"), self)
        self.recent_title.setObjectName("sectionLabel")
        recent_panel_layout.addWidget(self.recent_title)

        self.recent_list = QListWidget(self)
        self.recent_list.setObjectName("recentList")
        self.recent_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.recent_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        recent_panel_layout.addWidget(self.recent_list)
        self.render_recent()

        # Refresh the relative timestamps ("5 min ago") periodically so they
        # stay accurate without the user touching anything.
        self.recent_timer = QTimer(self)
        self.recent_timer.timeout.connect(self.render_recent)
        self.recent_timer.start(30000)

        upper_layout.addWidget(recent_panel)
        main_layout.addLayout(upper_layout)

        # --- Playbar (Bottom Spotify-style playback controls) ---
        self.playbar = QFrame(self)
        self.playbar.setObjectName("playbar")
        self.playbar.setFixedHeight(90)
        playbar_layout = QHBoxLayout(self.playbar)
        playbar_layout.setContentsMargins(20, 10, 20, 10)

        # Left section: Selected station details
        self.playbar_details = QWidget(self)
        self.playbar_details.setFixedWidth(280)
        details_layout = QHBoxLayout(self.playbar_details)
        details_layout.setContentsMargins(0, 0, 0, 0)
        details_layout.setSpacing(12)

        self.pb_logo = QLabel(self)
        self.pb_logo.setObjectName("pbLogo")
        self.pb_logo.setFixedSize(56, 56)
        self.pb_logo.setPixmap(create_fallback_logo("").scaled(56, 56, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        details_layout.addWidget(self.pb_logo)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        text_layout.addStretch()
        self.pb_title = QLabel(t("playbar.select_station"), self)
        self.pb_title.setObjectName("pbTitle")
        text_layout.addWidget(self.pb_title)

        self.pb_desc = QLabel(t("playbar.no_station"), self)
        self.pb_desc.setObjectName("pbDesc")
        text_layout.addWidget(self.pb_desc)

        # "Now playing" track info from ICY stream metadata (StreamTitle).
        self.pb_track = QLabel("", self)
        self.pb_track.setObjectName("pbTrack")
        self.pb_track.hide()
        text_layout.addWidget(self.pb_track)
        text_layout.addStretch()
        details_layout.addLayout(text_layout)
        playbar_layout.addWidget(self.playbar_details)

        # Center section: Playback buttons
        play_controls = QWidget(self)
        controls_layout = QVBoxLayout(play_controls)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(4)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        # Play/Stop Button
        self.play_btn = QPushButton(self)
        self.play_btn.setObjectName("playBtn")
        self.play_btn.setFixedSize(40, 40)
        self.play_btn.setEnabled(False)
        self.set_play_icon(False)
        btn_layout.addWidget(self.play_btn)
        
        btn_layout.addStretch()
        controls_layout.addLayout(btn_layout)

        # Playing State string indicator
        self.state_label = QLabel(t("state.disconnected"), self)
        self.state_label.setObjectName("stateLabel")
        self.state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        controls_layout.addWidget(self.state_label)
        
        playbar_layout.addWidget(play_controls)

        # Right section: Volume controls
        volume_widget = QWidget(self)
        volume_widget.setFixedWidth(220)
        volume_layout = QHBoxLayout(volume_widget)
        volume_layout.setContentsMargins(0, 0, 0, 0)
        volume_layout.setSpacing(10)

        # Mute button
        self.mute_btn = QPushButton(self)
        self.mute_btn.setFixedSize(32, 32)
        self.mute_btn.setStyleSheet("background-color: transparent; border: none; padding: 0px;")
        self.set_mute_icon(False)
        volume_layout.addWidget(self.mute_btn)

        # Volume slider
        self.volume_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(int(self.current_volume * 100))
        self.volume_slider.setEnabled(False)
        self.volume_slider.setMinimumHeight(20)
        volume_layout.addWidget(self.volume_slider)

        playbar_layout.addWidget(volume_widget)

        main_layout.addWidget(self.playbar)

    @staticmethod
    def _sort_key(station):
        # Favorites first (False sorts before True), then alphabetical by name
        return (not station.get('favorite', False), station.get('name', '').lower())

    def sorted_stations(self):
        return sorted(self.stations, key=self._sort_key)

    def populate_grid(self, stations):
        # Clear existing layout items
        for i in reversed(range(self.grid_layout.count())):
            self.grid_layout.itemAt(i).widget().setParent(None)

        columns = 3
        for idx, station in enumerate(self.sorted_stations()):
            row = idx // columns
            col = idx % columns

            card = StationCard(station)
            card.clicked.connect(self.select_station)
            card.double_clicked.connect(self.play_station)
            card.favorite_toggled.connect(self.on_favorite_toggled)
            self.grid_layout.addWidget(card, row, col)
            self.card_widgets[station['id']] = card

            # Start background async download of logo if URL exists
            if station.get('logo'):
                downloader = LogoDownloader(station['id'], station['logo'])
                downloader.logo_downloaded.connect(self.on_logo_downloaded)
                downloader.start()
                self.downloaders.append(downloader)

        # Trailing spacer column absorbs leftover width so fixed-width cards
        # stay left-aligned instead of stretching across the row.
        self.grid_layout.setColumnStretch(columns, 1)

    def reflow_grid(self):
        """Re-positions existing cards in sorted order without recreating them."""
        # Detach all cards from the layout (widgets are kept alive in card_widgets)
        while self.grid_layout.count():
            self.grid_layout.takeAt(0)

        columns = 3
        for idx, station in enumerate(self.sorted_stations()):
            card = self.card_widgets.get(station['id'])
            if card is not None:
                self.grid_layout.addWidget(card, idx // columns, idx % columns)

        # Keep trailing spacer column so cards remain left-aligned, fixed width.
        self.grid_layout.setColumnStretch(columns, 1)

    def on_logo_downloaded(self, station_id, image_data):
        pixmap = QPixmap()
        if pixmap.loadFromData(image_data):
            # Scale logo
            scaled_pixmap = pixmap.scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            # Update grid card logo
            if station_id in self.card_widgets:
                self.card_widgets[station_id].set_logo_pixmap(scaled_pixmap)
            # Update playbar logo if currently selected
            if self.selected_station and self.selected_station['id'] == station_id:
                self.pb_logo.setPixmap(scaled_pixmap.scaled(56, 56, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def setup_connections(self):
        # Search filter
        self.search_input.textChanged.connect(self.apply_filters)
        self.fav_filter_btn.toggled.connect(self.apply_filters)

        # Station manager (CRUD)
        self.manage_btn.clicked.connect(self.open_station_manager)

        # Scan and connect
        self.scan_btn.clicked.connect(self.scan_chromecasts)
        self.device_list.currentRowChanged.connect(self.device_selection_changed)

        # Theme toggle
        self.theme_btn.clicked.connect(self.toggle_theme)

        # Language toggle
        self.lang_btn.clicked.connect(self.toggle_language)

        # About dialog
        self.about_btn.clicked.connect(self.open_about)

        # Proxy port apply
        self.apply_port_btn.clicked.connect(self.apply_proxy_port)
        
        # Chromecast Controller signals
        self.cast_controller.devices_updated.connect(self.on_devices_updated)
        self.cast_controller.connection_status.connect(self.on_connection_status_changed)
        self.cast_controller.playback_state_changed.connect(self.on_playback_state_changed)
        self.cast_controller.volume_changed.connect(self.on_volume_changed_remotely)
        
        # Playbar buttons
        self.play_btn.clicked.connect(self.toggle_playback)
        self.mute_btn.clicked.connect(self.toggle_mute)
        self.volume_slider.valueChanged.connect(self.volume_slider_changed)

    def set_led_state(self, color):
        if color == "green":
            self.status_led.setStyleSheet("background-color: #10b981; border-radius: 5px;")
        elif color == "yellow":
            self.status_led.setStyleSheet("background-color: #f59e0b; border-radius: 5px;")
        else: # grey
            self.status_led.setStyleSheet("background-color: #6b7280; border-radius: 5px;")

    def set_play_icon(self, is_playing):
        # Use painter to draw custom vector shapes for play/stop to avoid needing external image assets
        pixmap = QPixmap(40, 40)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        painter.setBrush(QColor('#0f0f11'))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, 40, 40)
        
        painter.setBrush(QColor('#ffffff'))
        if is_playing:
            # Draw STOP square
            painter.drawRect(13, 13, 14, 14)
        else:
            # Draw PLAY triangle
            from PyQt6.QtGui import QPolygonF
            from PyQt6.QtCore import QPointF
            polygon = QPolygonF([QPointF(15, 11), QPointF(15, 29), QPointF(30, 20)])
            painter.drawPolygon(polygon)
            
        painter.end()
        self.play_btn.setIcon(QIcon(pixmap))
        self.play_btn.setIconSize(QSize(40, 40))

    def set_mute_icon(self, is_muted):
        # Draw dynamic vector volume icon
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        icon_color = QColor(self.palette_colors['text'])
        painter.setPen(icon_color)

        # Speaker base
        painter.setBrush(icon_color)
        from PyQt6.QtGui import QPolygonF
        from PyQt6.QtCore import QPointF
        speaker_polygon = QPolygonF([
            QPointF(8, 12), QPointF(12, 12), QPointF(16, 8),
            QPointF(16, 24), QPointF(12, 20), QPointF(8, 20)
        ])
        painter.drawPolygon(speaker_polygon)
        
        if is_muted:
            # Muted X lines
            painter.setPen(QColor('#ef4444'))
            painter.drawLine(20, 12, 26, 20)
            painter.drawLine(26, 12, 20, 20)
        else:
            # Sound waves
            painter.setBrush(Qt.GlobalColor.transparent)
            painter.drawArc(12, 10, 10, 12, -60 * 16, 120 * 16)
            painter.drawArc(10, 7, 16, 18, -60 * 16, 120 * 16)
            
        painter.end()
        self.mute_btn.setIcon(QIcon(pixmap))
        self.mute_btn.setIconSize(QSize(32, 32))

    # --- Chromecast integration slots ---
    
    def scan_chromecasts(self):
        self.scan_btn.setEnabled(False)
        self.scan_btn.setText(t("sidebar.scan_running"))
        self.device_list.setEnabled(False)
        self.cast_controller.start_discovery()

    def on_devices_updated(self, devices):
        self.device_list.blockSignals(True)
        self.device_list.clear()
        self.device_list.addItem(t("sidebar.disconnected_item"))

        # Populate list of discovered Chromecasts
        for d in devices:
            self.device_list.addItem(d.name)

        # Decide which row to preselect (no signal fired while blocked)
        selected_row = 0
        auto_connect_name = None
        if self.cast_controller.active_cast:
            # Keep the currently connected device selected
            active_name = self.cast_controller.active_cast.name
            matches = self.device_list.findItems(active_name, Qt.MatchFlag.MatchExactly)
            if matches:
                selected_row = self.device_list.row(matches[0])
        elif self._auto_connect_pending:
            # First discovery after launch: reconnect to the last used device if present
            last_name = self.config.get('last_device')
            matches = self.device_list.findItems(last_name, Qt.MatchFlag.MatchExactly) if last_name else []
            if matches:
                selected_row = self.device_list.row(matches[0])
                auto_connect_name = last_name
        self.device_list.setCurrentRow(selected_row)

        self.device_list.blockSignals(False)
        self.device_list.setEnabled(True)
        self.scan_btn.setEnabled(True)
        self.scan_btn.setText(t("sidebar.scan"))

        # Auto-reconnect happens only once (don't reconnect on every manual rescan)
        self._auto_connect_pending = False
        if auto_connect_name:
            self.status_label.setText(t("status.reconnecting", name=auto_connect_name))
            self.cast_controller.connect_device(auto_connect_name)

    def device_selection_changed(self, index):
        if index <= 0:
            self.cast_controller.disconnect_active()
        else:
            item = self.device_list.item(index)
            if item:
                self.cast_controller.connect_device(item.text())

    def on_connection_status_changed(self, message, is_connected, kind="info"):
        self._is_connected = is_connected
        self.status_label.setText(message)
        if is_connected:
            self.set_led_state("green")
            self.volume_slider.setEnabled(True)
            self.play_btn.setEnabled(self.selected_station is not None)
            self.state_label.setText(t("state.connected"))

            # Remember the connected device for next launch
            if self.cast_controller.active_cast:
                name = self.cast_controller.active_cast.name
                if self.config.get('last_device') != name:
                    self.config['last_device'] = name
                    self.save_config()

            # Resume the last station once, right after the startup connection
            if self._auto_play_pending and self.selected_station:
                self._auto_play_pending = False
                self.play_station(self.selected_station)
        else:
            # Yellow while a connection/scan is in progress, grey otherwise.
            # Driven by the locale-independent kind so it works in any language.
            if kind in ("connecting", "searching"):
                self.set_led_state("yellow")
            else:
                self.set_led_state("grey")
            self.volume_slider.setEnabled(False)
            self.play_btn.setEnabled(False)
            self.state_label.setText(t("state.disconnected"))

    def on_playback_state_changed(self, player_state):
        log.info("playback_state=%s active_station=%s", player_state,
                 self.active_station['id'] if self.active_station else None)
        self.state_label.setText(player_state)
        if player_state in ["PLAYING", "BUFFERING"]:
            self.is_playing = True
            self.set_play_icon(True)
            # Ensure "now playing" polling is running. On startup the device replays
            # a stale IDLE status right after we start it, which stops the fetcher;
            # restart it here once real playback begins so the track title appears.
            if self.active_station and self.metadata_fetcher is None:
                self.start_metadata(self.active_station['url'])
        else:
            self.is_playing = False
            self.set_play_icon(False)
            self.stop_metadata()

    def on_volume_changed_remotely(self, volume_level, volume_muted):
        self.current_volume = volume_level
        self.is_muted = volume_muted
        
        # Update slider without triggering loop signals
        self.volume_slider.blockSignals(True)
        self.volume_slider.setValue(int(volume_level * 100))
        self.volume_slider.blockSignals(False)
        
        self.set_mute_icon(volume_muted)

    # --- Playback controls ---

    def select_station(self, station_data):
        # Deselect old card
        if self.selected_station and self.selected_station['id'] in self.card_widgets:
            self.card_widgets[self.selected_station['id']].set_selected(False)
            
        self.selected_station = station_data
        
        # Select new card
        if station_data['id'] in self.card_widgets:
            self.card_widgets[station_data['id']].set_selected(True)
            
        # Update details on the playbar
        self.pb_title.setText(station_data['name'])
        self.pb_desc.setText(station_data.get('description') or t("playbar.no_description"))

        # The track label belongs to the currently playing station; hide it when
        # the user merely selects a different station.
        if not self.active_station or station_data['id'] != self.active_station['id']:
            self.pb_track.hide()
            self.pb_track.clear()
        
        # Update logo on playbar
        if station_data['id'] in self.card_widgets:
            card_logo = self.card_widgets[station_data['id']].logo_label.pixmap()
            if card_logo:
                self.pb_logo.setPixmap(card_logo.scaled(56, 56, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                
        # Enable play button if Chromecast is connected
        if self.cast_controller.active_cast:
            self.play_btn.setEnabled(True)

    def play_station(self, station_data):
        self.select_station(station_data)
        if self.cast_controller.active_cast:
            # Construct Stream URL: route through proxy if proxy flag is true
            if station_data.get('proxy', False):
                stream_url = self.proxy_server.get_proxy_url(
                    station_data['id'], cast_host=self.cast_controller.active_cast_host())
            else:
                stream_url = station_data['url']

            log.info("play_station id=%s proxy=%s url=%s", station_data['id'],
                     station_data.get('proxy', False), stream_url)
            self.active_station = station_data
            self.cast_controller.play_stream(
                stream_url,
                content_type=station_data.get('content_type', 'audio/mpeg'),
                title=station_data['name']
            )

            # NOTE: we deliberately do NOT open the metadata connection here.
            # For proxied stations the proxy is already opening a connection to the
            # same source; opening a second one *before* the proxy connects races it
            # and small Icecast/Shoutcast servers (e.g. Guerrilla, Vanilla) end up
            # never delivering audio to the proxy. Metadata polling is started from
            # on_playback_state_changed once real playback (PLAYING/BUFFERING) begins,
            # so the proxy gets its upstream connection first.
            # Stop any fetcher left over from a previously playing station; the new
            # one is (re)started from on_playback_state_changed.
            self.stop_metadata()

            # Remember the last played station for next launch
            if self.config.get('last_station') != station_data['id']:
                self.config['last_station'] = station_data['id']
                self.save_config()

    def toggle_playback(self):
        if self.is_playing:
            self.cast_controller.stop_stream()
        else:
            if self.selected_station:
                self.play_station(self.selected_station)

    def toggle_mute(self):
        self.is_muted = not self.is_muted
        self.cast_controller.set_mute(self.is_muted)
        self.set_mute_icon(self.is_muted)

    def volume_slider_changed(self, value):
        self.current_volume = value / 100.0
        self.cast_controller.set_volume(self.current_volume)

    # --- Stream metadata ("now playing") ---

    def start_metadata(self, url):
        """Starts polling the given stream URL for ICY track metadata."""
        self.stop_metadata()
        self.pb_track.hide()
        self.pb_track.clear()
        self.metadata_fetcher = MetadataFetcher(url)
        self.metadata_fetcher.title_changed.connect(self.on_track_title_changed)
        self.metadata_fetcher.start()

    def stop_metadata(self):
        """Stops the active metadata fetcher thread, if any."""
        if self.metadata_fetcher is not None:
            self.metadata_fetcher.stop()
            self.metadata_fetcher.wait()
            self.metadata_fetcher = None
        self.pb_track.hide()
        self.pb_track.clear()

    def on_track_title_changed(self, title):
        if title:
            self.pb_track.setText(f"♪ {title}")
            self.pb_track.show()
            self.notify_track(title)
        else:
            self.pb_track.hide()
            self.pb_track.clear()

    def notify_track(self, title):
        """Records the track in the in-app history and, when the app is in the
        background, raises a native Windows notification so the user is alerted
        to the song change without having the window in focus."""
        station_name = self.active_station['name'] if self.active_station else "RadioChromecast"
        self.add_recent_track(station_name, title)

        # Only notify when the window isn't the active foreground window (i.e. it's
        # minimized, hidden to tray, or behind another app) — a toast on top of the
        # window you're already looking at is just noise.
        in_background = self.isMinimized() or not self.isVisible() or not self.isActiveWindow()
        if in_background and self.tray and QSystemTrayIcon.supportsMessages():
            self.tray.showMessage(station_name, f"♪ {title}", self.app_icon, 5000)

    def add_recent_track(self, station_name, title):
        """Prepends a track to the 'recently played' history, capped at MAX_RECENT."""
        self.recent_entries.insert(0, {
            'title': title,
            'station': station_name,
            'time': datetime.now(),
        })
        del self.recent_entries[self.MAX_RECENT:]
        self.render_recent()

    def format_relative_time(self, when):
        """Returns a localized 'x min ago' style string for a past datetime."""
        seconds = int((datetime.now() - when).total_seconds())
        if seconds < 60:
            return t("recent.just_now")
        minutes = seconds // 60
        if minutes < 60:
            return t("recent.minute_ago") if minutes == 1 else t("recent.minutes_ago", n=minutes)
        hours = minutes // 60
        if hours < 24:
            return t("recent.hour_ago") if hours == 1 else t("recent.hours_ago", n=hours)
        days = hours // 24
        return t("recent.day_ago") if days == 1 else t("recent.days_ago", n=days)

    def render_recent(self):
        """Rebuilds the recently-played list, refreshing each relative timestamp.
        Called when a track is added, on a timer, and on language switch."""
        self.recent_list.clear()
        if not self.recent_entries:
            self.recent_list.addItem(QListWidgetItem(t("sidebar.recent_empty")))
            return
        for entry in self.recent_entries:
            rel = self.format_relative_time(entry['time'])
            item = QListWidgetItem(f"♪ {entry['title']}\n{entry['station']} · {rel}")
            self.recent_list.addItem(item)

    # --- Filtering and utility slots ---

    def apply_filters(self, *args):
        search_text = self.search_input.text().lower()
        only_favorites = self.fav_filter_btn.isChecked()

        # Go through each card and check visibility criteria
        for station_id, card in self.card_widgets.items():
            name = card.station_data['name'].lower()
            genre = card.station_data.get('genre', '').lower()
            desc = card.station_data.get('description', '').lower()

            matches_text = (search_text in name or
                            search_text in genre or
                            search_text in desc)
            matches_fav = (not only_favorites) or card.is_favorite
            card.setVisible(matches_text and matches_fav)

    # --- Favorites ---

    def get_favorites_path(self):
        base_dir = os.path.dirname(self.stations_path) if self.stations_path else os.getcwd()
        return os.path.join(base_dir, 'favorites.json')

    def load_favorites(self):
        """Marks stations as favorite based on the 'favorites' id list in config.json.

        Falls back to the legacy favorites.json once, to migrate older installs."""
        favorite_ids = self.config.get('favorites')
        if favorite_ids is None:
            # Migration: pull from legacy favorites.json if present.
            path = self.get_favorites_path()
            if os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        favorite_ids = json.load(f)
                except Exception as e:
                    print(f"[RadioCast] Eroare la citirea favoritelor: {e}")
                    favorite_ids = []
            else:
                favorite_ids = []
        favorite_ids = set(favorite_ids)
        for station in self.stations:
            station['favorite'] = station.get('id') in favorite_ids

    def save_favorites(self):
        """Persists the list of favorite station ids inside config.json."""
        self.config['favorites'] = [s['id'] for s in self.stations if s.get('favorite')]
        self.save_config()

    def on_favorite_toggled(self, station_data, is_favorite):
        # station_data is the same dict held in self.stations, so the flag is already updated
        self.save_favorites()
        # Reorder the grid (favorites first) and re-apply the current filter
        self.reflow_grid()
        self.apply_filters()

    # --- Station CRUD ---

    def open_station_manager(self):
        """Opens the dialog for adding, editing and deleting radio stations."""
        StationManagerDialog(self).exec()

    def open_about(self):
        """Opens the About dialog with app info and credits."""
        AboutDialog(self, app_icon=self.app_icon).exec()

    def save_stations(self):
        """Persists the current station list back to stations.json (without the
        runtime-only 'favorite' flag, which lives in favorites.json)."""
        if not self.stations_path:
            return
        payload = {
            "stations": [
                {k: v for k, v in station.items() if k != 'favorite'}
                for station in self.stations
            ]
        }
        try:
            with open(self.stations_path, 'w', encoding='utf-8') as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[RadioCast] Eroare la salvarea stations.json: {e}")
            QMessageBox.warning(self, t("common.error"), t("error.save_stations_failed", error=e))

    def add_station(self, data):
        """Adds a new station (mutating the shared list in place so the proxy sees it)."""
        data.setdefault('favorite', False)
        self.stations.append(data)
        self.save_stations()
        self.rebuild_stations_grid()

    def update_station(self, station_id, data):
        """Updates an existing station in place, preserving its favorite flag."""
        station = next((s for s in self.stations if s.get('id') == station_id), None)
        if station is None:
            return
        favorite = station.get('favorite', False)
        station.clear()
        station.update(data)
        station['favorite'] = favorite
        self.save_stations()
        self.rebuild_stations_grid()

    def delete_station(self, station_id):
        """Removes a station and updates playback/selection state if it was in use."""
        station = next((s for s in self.stations if s.get('id') == station_id), None)
        if station is None:
            return

        # If the station is currently playing, stop it before removing.
        if self.active_station and self.active_station.get('id') == station_id:
            if self.is_playing and self.cast_controller.active_cast:
                self.cast_controller.stop_stream()
            self.stop_metadata()
            self.active_station = None

        # Reset the playbar if the deleted station was selected.
        if self.selected_station and self.selected_station.get('id') == station_id:
            self.selected_station = None
            self.pb_title.setText(t("playbar.select_station"))
            self.pb_desc.setText(t("playbar.no_station"))
            self.pb_track.hide()
            self.pb_track.clear()
            self.pb_logo.setPixmap(create_fallback_logo("").scaled(
                56, 56, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            self.play_btn.setEnabled(False)

        self.stations.remove(station)
        # Drop the deleted id from favorites.json too.
        self.save_favorites()
        self.save_stations()
        self.rebuild_stations_grid()

    def rebuild_stations_grid(self):
        """Fully rebuilds the station grid from the current list, replacing all cards."""
        # Stop any in-flight logo downloads tied to the old cards.
        for downloader in self.downloaders:
            if downloader.isRunning():
                downloader.terminate()
                downloader.wait()
        self.downloaders = []

        # Remove every existing card from the layout and forget them.
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
        self.card_widgets = {}

        # Rebuild from scratch, then restore selection highlight and active filter.
        self.populate_grid(self.stations)
        if self.selected_station and self.selected_station.get('id') in self.card_widgets:
            self.card_widgets[self.selected_station['id']].set_selected(True)
        self.apply_filters()

    # --- Theme ---

    def update_theme_button(self):
        # The button shows the theme you will switch TO
        if self.theme == 'dark':
            self.theme_btn.setText("☀")
            self.theme_btn.setToolTip(t("theme.to_light"))
        else:
            self.theme_btn.setText("☾")
            self.theme_btn.setToolTip(t("theme.to_dark"))

    def toggle_theme(self):
        self.theme = 'light' if self.theme == 'dark' else 'dark'
        self.palette_colors = PALETTES[self.theme]
        self.setStyleSheet(build_stylesheet(self.theme))
        # Redraw painter-based icons whose colors depend on the theme
        self.set_mute_icon(self.is_muted)
        self.update_theme_button()
        # Persist the choice
        self.config['theme'] = self.theme
        self.save_config()

    # --- Language ---

    def update_lang_button(self):
        # The button shows the language you will switch TO.
        other = "en" if i18n.current_language() == "ro" else "ro"
        self.lang_btn.setText(other.upper())
        self.lang_btn.setToolTip(t("lang.toggle_tooltip"))

    def toggle_language(self):
        new_lang = "en" if i18n.current_language() == "ro" else "ro"
        i18n.set_language(new_lang)
        self.config['language'] = new_lang
        self.save_config()
        self.retranslate_ui()

    def retranslate_ui(self):
        """Re-applies every static UI string in the active language. Called when
        the user switches language at runtime, so no restart is needed."""
        # Window / sidebar
        self.update_lang_button()
        self.update_theme_button()
        self.about_btn.setToolTip(t("about.tooltip"))
        self.cast_section_label.setText(t("sidebar.devices"))
        self.scan_btn.setText(t("sidebar.scan"))
        self.status_title.setText(t("sidebar.connection_status"))
        self.recent_title.setText(t("sidebar.recent"))
        self.render_recent()
        self.settings_label.setText(t("sidebar.settings"))
        self.port_label.setText(t("sidebar.proxy_port"))
        self.apply_port_btn.setText(t("sidebar.apply"))
        self.help_note.setText(t("sidebar.help_note"))

        # The "Disconnected" placeholder is the first device-list row when idle.
        if self.device_list.count() and self.device_list.item(0):
            self.device_list.item(0).setText(t("sidebar.disconnected_item"))

        # Content header
        self.search_input.setPlaceholderText(t("content.search_ph"))
        self.fav_filter_btn.setText(t("content.fav_filter"))
        self.manage_btn.setText(t("content.manage"))
        self.manage_btn.setToolTip(t("content.manage_tooltip"))

        # Connection status text + playback state, only when not actively connected
        # (a live message from the controller stays as-is until the next event).
        if not self._is_connected:
            self.status_label.setText(t("sidebar.not_connected"))
            self.state_label.setText(t("state.disconnected"))
        else:
            self.state_label.setText(t("state.connected"))

        # Playbar details: refresh from the selected station, or the placeholder.
        if self.selected_station:
            self.pb_title.setText(self.selected_station['name'])
            self.pb_desc.setText(self.selected_station.get('description') or t("playbar.no_description"))
        else:
            self.pb_title.setText(t("playbar.select_station"))
            self.pb_desc.setText(t("playbar.no_station"))

        # Station cards: re-localize each card's favorite tooltip and genre fallback.
        for card in self.card_widgets.values():
            card.update_fav_icon()
            if not card.station_data.get('genre'):
                card.genre_label.setText(t("common.general"))

        # Tray menu actions
        if self.tray and self.tray.contextMenu():
            actions = self.tray.contextMenu().actions()
            for action in actions:
                role = action.data()
                if role == "show":
                    action.setText(t("tray.show"))
                elif role == "quit":
                    action.setText(t("tray.quit"))

    def save_config(self):
        """Persists the in-memory config (including theme) to config.json."""
        if not self.stations_path:
            return
        config_path = os.path.join(os.path.dirname(self.stations_path), 'config.json')
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[RadioCast] Eroare la salvarea config.json: {e}")

    # --- Proxy port ---

    def apply_proxy_port(self):
        """Restarts the proxy server on the port chosen in the UI and persists it."""
        new_port = self.port_spin.value()
        if new_port == self.proxy_server.port:
            self.status_label.setText(t("proxy.already_using", port=new_port))
            return

        # Remember current playback so we can resume it on the new port
        was_playing = self.is_playing
        station = self.active_station

        try:
            self.proxy_server.stop()
            self.proxy_server.port = new_port
            self.proxy_server.start()
        except Exception as e:
            self.status_label.setText(t("proxy.change_failed", error=e))
            return

        # The proxy may auto-increment if the chosen port was busy; reflect the real one
        actual_port = self.proxy_server.port
        self.port_spin.setValue(actual_port)
        self.config['proxy_port'] = actual_port
        self.save_config()

        if actual_port != new_port:
            self.status_label.setText(t("proxy.port_busy", port=new_port, actual=actual_port))
        else:
            self.status_label.setText(t("proxy.now_using", port=actual_port))

        # Re-stream the active station so the Chromecast picks up the new proxy URL
        if was_playing and station and station.get('proxy') and self.cast_controller.active_cast:
            self.play_station(station)

    # --- Window geometry persistence ---

    def restore_window_geometry(self):
        """Restores the last saved window position and size, if it fits on a screen."""
        geo = self.config.get('window_geometry')
        if not isinstance(geo, dict):
            return
        try:
            x, y = int(geo['x']), int(geo['y'])
            w, h = int(geo['width']), int(geo['height'])
        except (KeyError, TypeError, ValueError):
            return

        # Never restore smaller than the enforced minimum size.
        w = max(w, self.minimumWidth())
        h = max(h, self.minimumHeight())
        rect = QRect(x, y, w, h)

        # Only restore if the window would land on a currently connected screen,
        # so a window saved on a now-disconnected monitor doesn't vanish off-screen.
        if any(screen.availableGeometry().intersects(rect) for screen in QGuiApplication.screens()):
            self.setGeometry(rect)

    def save_window_geometry(self):
        """Stores the current (non-maximized) window position and size to config."""
        geo = self.normalGeometry()
        self.config['window_geometry'] = {
            'x': geo.x(), 'y': geo.y(),
            'width': geo.width(), 'height': geo.height()
        }
        self.save_config()

    # --- System tray / minimize-to-tray ---

    def setup_tray(self):
        """Creates the system tray icon so the app can keep running while hidden."""
        self.tray = None
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return

        self.tray = QSystemTrayIcon(self.app_icon, self)
        self.tray.setToolTip("RadioChromecast")

        menu = QMenu()
        show_action = menu.addAction(t("tray.show"))
        show_action.setData("show")  # role tag so retranslate_ui can find it
        show_action.triggered.connect(self.show_from_tray)
        menu.addSeparator()
        quit_action = menu.addAction(t("tray.quit"))
        quit_action.setData("quit")
        quit_action.triggered.connect(self.quit_app)
        self.tray.setContextMenu(menu)

        self.tray.activated.connect(self.on_tray_activated)
        self.tray.show()

    def on_tray_activated(self, reason):
        # Restore the window on a left click / double click on the tray icon.
        if reason in (QSystemTrayIcon.ActivationReason.Trigger,
                      QSystemTrayIcon.ActivationReason.DoubleClick):
            self.show_from_tray()

    def show_from_tray(self):
        """Restores and focuses the window from the tray."""
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def quit_app(self):
        """Fully exits the application from the tray menu."""
        self._really_quit = True
        self.close()

    def changeEvent(self, event):
        # Hide to the tray when the window is minimized.
        if event.type() == QEvent.Type.WindowStateChange and self.isMinimized() and self.tray:
            event.ignore()
            self.save_window_geometry()
            # Defer hide() so the minimize animation doesn't leave a ghost window.
            QTimer.singleShot(0, self.hide)
            return
        super().changeEvent(event)

    def closeEvent(self, event):
        # Persist the current position/size before hiding or quitting.
        self.save_window_geometry()

        # Closing the window hides to the tray instead of quitting, unless the user
        # explicitly chose "Ieșire" from the tray menu.
        if self.tray and not self._really_quit:
            event.ignore()
            self.hide()
            self.tray.showMessage(
                "RadioChromecast",
                t("tray.running_background"),
                self.app_icon, 3000
            )
            return

        # Stop the metadata polling thread before exiting
        self.stop_metadata()
        # Gracefully stop download threads to prevent segmentation faults on exit
        for downloader in self.downloaders:
            if downloader.isRunning():
                downloader.terminate()
                downloader.wait()
        if self.tray:
            self.tray.hide()
        event.accept()
