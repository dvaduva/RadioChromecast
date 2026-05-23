import os
import sys
import json
import math
from string import Template
import requests
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QPointF
from PyQt6.QtGui import QPainter, QColor, QFont, QPixmap, QIcon, QAction, QPolygonF, QPen
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QSlider, QScrollArea, QListWidget,
    QSpinBox, QFrame, QSizePolicy, QSpacerItem, QGraphicsDropShadowEffect
)

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
QLabel#pbLogo { border-radius: 6px; background-color: $logo_bg; }
QLabel#pbTitle { font-size: 14px; font-weight: bold; color: $text_strong; }
QLabel#pbDesc { font-size: 11px; color: $text_muted; }
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
    margin-top: -4px;
    border-radius: 6px;
}
QSlider::handle:horizontal:hover {
    background: #c084fc;
    width: 14px;
    height: 14px;
    margin-top: -5px;
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
        self.fav_btn.setToolTip("Adaugă la favorite")
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
        self.genre_label = QLabel(self.station_data.get('genre', 'General'), self)
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
        self.fav_btn.setToolTip("Elimină de la favorite" if self.is_favorite else "Adaugă la favorite")

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

        # Auto-reconnect to the last used device / resume the last station, once
        self._auto_connect_pending = bool(self.config.get('last_device'))
        self._auto_play_pending = bool(self.config.get('last_station'))

        self.card_widgets = {}
        self.downloaders = []

        self.setWindowTitle("RadioChromecast")
        self.setMinimumSize(1000, 700)
        self.setStyleSheet(build_stylesheet(self.theme))

        # Set window icon
        icon_path = get_resource_path("icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))


        self.init_ui()
        self.setup_connections()

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

        # App Logo & Name
        logo_container = QHBoxLayout()
        logo_container.setSpacing(10)
        
        self.app_title = QLabel("RadioCast", self)
        self.app_title.setObjectName("appTitle")
        logo_container.addWidget(self.app_title)
        logo_container.addStretch()

        # Theme toggle button
        self.theme_btn = QPushButton(self)
        self.theme_btn.setObjectName("themeBtn")
        self.theme_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_theme_button()
        logo_container.addWidget(self.theme_btn)
        sidebar_layout.addLayout(logo_container)

        # Separator line
        sep = QFrame()
        sep.setObjectName("sep")
        sep.setFrameShape(QFrame.Shape.HLine)
        sidebar_layout.addWidget(sep)

        # Chromecast Title Section
        cast_section_label = QLabel("DISPOZITIVE CHROMECAST", self)
        cast_section_label.setObjectName("sectionLabel")
        sidebar_layout.addWidget(cast_section_label)

        # Chromecast Device List
        self.device_list = QListWidget(self)
        self.device_list.setObjectName("deviceList")
        self.device_list.setMaximumHeight(180)
        self.device_list.addItem("Deconectat")
        self.device_list.setCurrentRow(0)
        sidebar_layout.addWidget(self.device_list)

        # Scan Button
        self.scan_btn = QPushButton("Scanează Rețea", self)
        self.scan_btn.setObjectName("scanBtn")
        sidebar_layout.addWidget(self.scan_btn)

        # Chromecast connection status display
        self.status_title = QLabel("STARE CONEXIUNE", self)
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

        self.status_label = QLabel("Nu este conectat niciun Chromecast.", self)
        self.status_label.setObjectName("statusLabel")
        self.status_label.setWordWrap(True)
        status_frame_layout.addWidget(self.status_label)
        sidebar_layout.addWidget(self.status_frame)

        # Settings section: proxy port
        settings_label = QLabel("SETĂRI", self)
        settings_label.setObjectName("sectionLabelMt")
        sidebar_layout.addWidget(settings_label)

        port_row = QHBoxLayout()
        port_row.setSpacing(8)
        port_label = QLabel("Port proxy:", self)
        port_label.setObjectName("statusLabel")
        port_row.addWidget(port_label)

        self.port_spin = QSpinBox(self)
        self.port_spin.setObjectName("portSpin")
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(self.proxy_server.port)
        port_row.addWidget(self.port_spin)

        self.apply_port_btn = QPushButton("Aplică", self)
        self.apply_port_btn.setObjectName("applyPortBtn")
        port_row.addWidget(self.apply_port_btn)
        sidebar_layout.addLayout(port_row)

        # Spacer to push everything to the top
        sidebar_layout.addStretch()

        # Instructions / Help note
        self.help_note = QLabel(
            "Asigură-te că dispozitivul tău Chromecast se află în aceeași rețea Wi-Fi cu calculatorul.",
            self
        )
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
        self.search_input.setPlaceholderText("Caută un post de radio sau gen muzical...")
        search_layout.addWidget(self.search_input)

        # Favorites-only filter toggle
        self.fav_filter_btn = QPushButton("★ Favorite", self)
        self.fav_filter_btn.setObjectName("favFilterBtn")
        self.fav_filter_btn.setCheckable(True)
        self.fav_filter_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        search_layout.addWidget(self.fav_filter_btn)

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
        self.pb_title = QLabel("Selectează un post", self)
        self.pb_title.setObjectName("pbTitle")
        text_layout.addWidget(self.pb_title)

        self.pb_desc = QLabel("Niciun post selectat", self)
        self.pb_desc.setObjectName("pbDesc")
        text_layout.addWidget(self.pb_desc)
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
        self.state_label = QLabel("DECONECTAT", self)
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

        # Scan and connect
        self.scan_btn.clicked.connect(self.scan_chromecasts)
        self.device_list.currentRowChanged.connect(self.device_selection_changed)

        # Theme toggle
        self.theme_btn.clicked.connect(self.toggle_theme)

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
        self.scan_btn.setText("Scanare...")
        self.device_list.setEnabled(False)
        self.cast_controller.start_discovery()

    def on_devices_updated(self, devices):
        self.device_list.blockSignals(True)
        self.device_list.clear()
        self.device_list.addItem("Deconectat")

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
        self.scan_btn.setText("Scanează Rețea")

        # Auto-reconnect happens only once (don't reconnect on every manual rescan)
        self._auto_connect_pending = False
        if auto_connect_name:
            self.status_label.setText(f"Se reconectează la ultimul dispozitiv: {auto_connect_name}...")
            self.cast_controller.connect_device(auto_connect_name)

    def device_selection_changed(self, index):
        if index <= 0:
            self.cast_controller.disconnect_active()
        else:
            item = self.device_list.item(index)
            if item:
                self.cast_controller.connect_device(item.text())

    def on_connection_status_changed(self, message, is_connected):
        self.status_label.setText(message)
        if is_connected:
            self.set_led_state("green")
            self.volume_slider.setEnabled(True)
            self.play_btn.setEnabled(self.selected_station is not None)
            self.state_label.setText("CONECTAT")

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
            if "conectează" in message:
                self.set_led_state("yellow")
            else:
                self.set_led_state("grey")
            self.volume_slider.setEnabled(False)
            self.play_btn.setEnabled(False)
            self.state_label.setText("DECONECTAT")

    def on_playback_state_changed(self, player_state):
        self.state_label.setText(player_state)
        if player_state in ["PLAYING", "BUFFERING"]:
            self.is_playing = True
            self.set_play_icon(True)
        else:
            self.is_playing = False
            self.set_play_icon(False)

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
        self.pb_desc.setText(station_data.get('description', 'Fără descriere'))
        
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
                stream_url = self.proxy_server.get_proxy_url(station_data['id'])
            else:
                stream_url = station_data['url']
                
            self.active_station = station_data
            self.cast_controller.play_stream(
                stream_url,
                content_type=station_data.get('content_type', 'audio/mpeg'),
                title=station_data['name']
            )

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
        """Marks stations as favorite based on the saved favorites.json id list."""
        path = self.get_favorites_path()
        if not os.path.exists(path):
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                favorite_ids = set(json.load(f))
            for station in self.stations:
                station['favorite'] = station.get('id') in favorite_ids
        except Exception as e:
            print(f"[RadioCast] Eroare la citirea favoritelor: {e}")

    def save_favorites(self):
        """Persists the list of favorite station ids to favorites.json."""
        favorite_ids = [s['id'] for s in self.stations if s.get('favorite')]
        try:
            with open(self.get_favorites_path(), 'w', encoding='utf-8') as f:
                json.dump(favorite_ids, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[RadioCast] Eroare la salvarea favoritelor: {e}")

    def on_favorite_toggled(self, station_data, is_favorite):
        # station_data is the same dict held in self.stations, so the flag is already updated
        self.save_favorites()
        # Reorder the grid (favorites first) and re-apply the current filter
        self.reflow_grid()
        self.apply_filters()

    # --- Theme ---

    def update_theme_button(self):
        # The button shows the theme you will switch TO
        if self.theme == 'dark':
            self.theme_btn.setText("☀")
            self.theme_btn.setToolTip("Comută pe tema deschisă (light)")
        else:
            self.theme_btn.setText("☾")
            self.theme_btn.setToolTip("Comută pe tema închisă (dark)")

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
            self.status_label.setText(f"Proxy-ul foloseste deja portul {new_port}.")
            return

        # Remember current playback so we can resume it on the new port
        was_playing = self.is_playing
        station = self.active_station

        try:
            self.proxy_server.stop()
            self.proxy_server.port = new_port
            self.proxy_server.start()
        except Exception as e:
            self.status_label.setText(f"Nu s-a putut schimba portul: {e}")
            return

        # The proxy may auto-increment if the chosen port was busy; reflect the real one
        actual_port = self.proxy_server.port
        self.port_spin.setValue(actual_port)
        self.config['proxy_port'] = actual_port
        self.save_config()

        if actual_port != new_port:
            self.status_label.setText(f"Portul {new_port} era ocupat. Proxy-ul foloseste {actual_port}.")
        else:
            self.status_label.setText(f"Proxy-ul ruleaza acum pe portul {actual_port}.")

        # Re-stream the active station so the Chromecast picks up the new proxy URL
        if was_playing and station and station.get('proxy') and self.cast_controller.active_cast:
            self.play_station(station)

    def closeEvent(self, event):
        # Gracefully stop download threads to prevent segmentation faults on exit
        for downloader in self.downloaders:
            if downloader.isRunning():
                downloader.terminate()
                downloader.wait()
        event.accept()
