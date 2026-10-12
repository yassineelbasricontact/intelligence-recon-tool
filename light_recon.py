#!/usr/bin/env python3
"""
Enhanced Light Recon - Futuristic Cyberpunk Interface for Shodan Data Visualization
Modern UI/UX with enhanced user experience and futuristic aesthetics
"""

import sys
import json
import re
import os
import requests
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFileDialog, QListWidget, QListWidgetItem, QTextEdit,
    QLabel, QSplitter, QLineEdit, QCheckBox, QComboBox, QProgressBar,
    QFrame, QGridLayout, QGroupBox, QTabWidget, QScrollArea
)
from PyQt6.QtCore import Qt, QUrl, QThread, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QColor, QPalette, QLinearGradient, QBrush, QPainter
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage
import folium
import threading
import time

IPSTACK_API_KEY = os.environ.get("IPSTACK_API_KEY", "abc25956a2f21bda82e27b5f08a319f2")


class FuturisticFrame(QFrame):
    """Custom frame with futuristic styling"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #0a0a0a, stop:0.5 #1a001a, stop:1 #0a0a0a);
                border: 1px solid #00ffff;
                border-radius: 8px;
                margin: 2px;
            }
        """)


class NeonButton(QPushButton):
    """Custom button with neon glow effect"""
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #001100, stop:0.5 #002200, stop:1 #001100);
                color: #00ffff;
                border: 2px solid #00ffff;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                font-family: 'Courier New', monospace;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #002200, stop:0.5 #004400, stop:1 #002200);
                border: 2px solid #00ff00;
                color: #00ff00;
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #000000, stop:0.5 #001100, stop:1 #000000);
                border: 2px solid #00ff00;
            }
        """)


class CyberpunkLabel(QLabel):
    """Custom label with cyberpunk styling"""
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet("""
            QLabel {
                color: #00ffff;
                font-family: 'Courier New', monospace;
                font-weight: bold;
                letter-spacing: 1px;
            }
        """)


class DataThread(QThread):
    """Thread for handling geolocation requests to prevent UI freezing"""
    geolocation_result = pyqtSignal(str, dict)
    progress_update = pyqtSignal(int, int)

    def __init__(self, ips, api_key):
        super().__init__()
        self.ips = ips
        self.api_key = api_key

    def run(self):
        for i, ip in enumerate(self.ips):
            try:
                url = f"http://api.ipstack.com/{ip}?access_key={self.api_key}"
                res = requests.get(url, timeout=3)
                if res.status_code == 200:
                    self.geolocation_result.emit(ip, res.json())
                else:
                    self.geolocation_result.emit(ip, {})
            except Exception:
                self.geolocation_result.emit(ip, {})
            self.progress_update.emit(i + 1, len(self.ips))
            time.sleep(0.1)  # Rate limiting


class CustomWebEnginePage(QWebEnginePage):
    """Custom WebEngine Page to intercept map marker clicks."""
    def __init__(self, parent_app, parent=None):
        super().__init__(parent)
        self.parent_app = parent_app

    def acceptNavigationRequest(self, url, _type, isMainFrame):
        # Intercept custom schema when a map marker is clicked
        if url.scheme() == "selecthost":
            ip_address = url.host()
            self.parent_app.select_host_by_ip(ip_address)
            return False  # Prevent browser from navigating away
        return super().acceptNavigationRequest(url, _type, isMainFrame)


class ReconApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("◢◤ NEXUS RECON TERMINAL ◥◣")
        self.setGeometry(100, 100, 1400, 900)

        # Set application icon and style
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #000000, stop:0.3 #000011, stop:0.7 #000011, stop:1 #000000);
            }
            QWidget {
                font-family: 'Courier New', monospace;
            }
        """)

        self.raw_hosts = []
        self.filtered_hosts = []
        self.geolocation_data = {}
        self.data_thread = None

        self.init_ui()
        self.apply_futuristic_theme()

    def apply_futuristic_theme(self):
        """Apply cyberpunk/futuristic theme to the application"""
        # Set custom palette
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(0, 0, 0))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(0, 255, 255))
        palette.setColor(QPalette.ColorRole.Base, QColor(0, 0, 0))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(0, 0, 0))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(0, 255, 255))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(0, 255, 255))
        palette.setColor(QPalette.ColorRole.Text, QColor(0, 255, 255))
        palette.setColor(QPalette.ColorRole.Button, QColor(0, 0, 0))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(0, 255, 255))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 255, 0))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 255, 255))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(0, 0, 0))
        self.setPalette(palette)

    def init_ui(self):
        # Central widget with tabbed interface
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Header
        header = self.create_header()
        main_layout.addWidget(header)

        # Main content area with tabs
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #00ffff;
                background: transparent;
            }
            QTabBar::tab {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #000000, stop:0.5 #001100, stop:1 #000000);
                color: #00ffff;
                border: 1px solid #00ffff;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #001100, stop:0.5 #002200, stop:1 #001100);
                border-bottom: 2px solid #00ff00;
                color: #00ff00;
            }
            QTabBar::tab:hover:!selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #000000, stop:0.5 #002200, stop:1 #000000);
                color: #00ff00;
            }
        """)

        # Tab 1: Main Recon Interface
        recon_tab = self.create_recon_tab()
        self.tab_widget.addTab(recon_tab, "◢◤ RECON ◥◣")

        # Tab 2: Analytics Dashboard
        analytics_tab = self.create_analytics_tab()
        self.tab_widget.addTab(analytics_tab, "◢◤ ANALYTICS ◥◣")

        # Tab 3: Threat Intelligence
        threat_tab = self.create_threat_tab()
        self.tab_widget.addTab(threat_tab, "◢◤ THREAT INTEL ◥◣")

        main_layout.addWidget(self.tab_widget)

        # Status bar
        self.status_bar = self.create_status_bar()
        main_layout.addWidget(self.status_bar)

    def create_header(self):
        """Create futuristic header with title and status indicators"""
        header_frame = FuturisticFrame()
        header_layout = QHBoxLayout(header_frame)

        # Title
        title_label = CyberpunkLabel("◢◤ NEXUS RECON TERMINAL ◥◣")
        title_label.setStyleSheet("""
            QLabel {
                color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00ffff, stop:0.5 #00ff00, stop:1 #ffff00);
                font-size: 24px;
                font-weight: bold;
                letter-spacing: 2px;
                text-shadow: 0 0 10px #00ffff, 0 0 20px #00ffff;
            }
        """)
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # Status indicators
        status_layout = QHBoxLayout()

        self.connection_status = CyberpunkLabel("● OFFLINE")
        self.connection_status.setStyleSheet("color: #ff0000;")
        status_layout.addWidget(QLabel("Connection:"))
        status_layout.addWidget(self.connection_status)

        self.hosts_status = CyberpunkLabel("Hosts: 0")
        status_layout.addWidget(QLabel(""))
        status_layout.addWidget(self.hosts_status)

        header_layout.addLayout(status_layout)

        return header_frame

    def create_recon_tab(self):
        """Create the main reconnaissance tab"""
        tab = QWidget()
        layout = QHBoxLayout(tab)

        # Left panel - Controls
        left_panel = self.create_control_panel()
        layout.addWidget(left_panel, 1)

        # Center panel - Map view
        center_panel = self.create_map_panel()
        layout.addWidget(center_panel, 2)

        # Right panel - Details view
        right_panel = self.create_details_panel()
        layout.addWidget(right_panel, 1)

        return tab

    def create_control_panel(self):
        """Create the left control panel"""
        panel = FuturisticFrame()
        layout = QVBoxLayout(panel)

        # Controls group
        controls_group = QGroupBox("◢◤ CONTROL MATRIX ◥◣")
        controls_group.setStyleSheet("""
            QGroupBox {
                color: #00ffff;
                font-weight: bold;
                border: 1px solid #00ffff;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
            }
        """)
        controls_layout = QVBoxLayout(controls_group)

        # Load button
        self.btn_load = NeonButton("◢◤ LOAD RECON DATA ◥◣")
        self.btn_load.clicked.connect(self.load_json)
        controls_layout.addWidget(self.btn_load)

        # Search section
        search_label = CyberpunkLabel("◢◤ SEARCH PROTOCOL ◥◣")
        controls_layout.addWidget(search_label)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("IP, Banner, Org, CVE, ASN...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #000000, stop:1 #001100);
                color: #00ffff;
                border: 1px solid #00ffff;
                border-radius: 4px;
                padding: 6px;
                font-family: 'Courier New', monospace;
            }
            QLineEdit:focus {
                border: 1px solid #00ff00;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #000000, stop:1 #002200);
            }
        """)
        self.search_input.textChanged.connect(self.apply_filters)
        controls_layout.addWidget(self.search_input)

        # Filter section
        filter_label = CyberpunkLabel("◢◤ FILTER MATRIX ◥◣")
        controls_layout.addWidget(filter_label)

        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("Port:"))
        self.port_combo = QComboBox()
        self.port_combo.setStyleSheet("""
            QComboBox {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #000000, stop:1 #001100);
                color: #00ffff;
                border: 1px solid #00ffff;
                border-radius: 4px;
                padding: 4px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid #00ffff;
                border-top: 4px solid transparent;
                border-bottom: 4px solid transparent;
                width: 0px;
                height: 0px;
            }
            QComboBox QAbstractItemView {
                background-color: #000000;
                color: #00ffff;
                selection-background-color: #002200;
            }
        """)
        self.port_combo.addItem("All")
        self.port_combo.currentIndexChanged.connect(self.apply_filters)
        port_layout.addWidget(self.port_combo)
        controls_layout.addLayout(port_layout)

        self.chk_vulns_only = QCheckBox("◢◤ VULNERABLE ONLY ◥◣")
        self.chk_vulns_only.setStyleSheet("""
            QCheckBox {
                color: #00ffff;
                spacing: 6px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border: 1px solid #00ffff;
                border-radius: 2px;
                background-color: #000000;
            }
            QCheckBox::indicator:checked {
                background-color: #00ff00;
                border: 1px solid #00ff00;
            }
        """)
        self.chk_vulns_only.stateChanged.connect(self.apply_filters)
        controls_layout.addWidget(self.chk_vulns_only)

        # Stats display
        stats_label = CyberpunkLabel("◢◤ STATISTICS MATRIX ◥◣")
        controls_layout.addWidget(stats_label)

        self.lbl_stats = CyberpunkLabel("Hosts Loaded: 0")
        self.lbl_stats.setStyleSheet("font-size: 13px;")
        controls_layout.addWidget(self.lbl_stats)

        # Progress bar for geolocation
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #00ffff;
                border-radius: 4px;
                text-align: center;
                background-color: #000000;
                color: #00ffff;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00ff00, stop:1 #00ffff);
                border-radius: 3px;
            }
        """)
        controls_layout.addWidget(self.progress_bar)

        controls_layout.addStretch()
        controls_group.setLayout(controls_layout)
        layout.addWidget(controls_group)

        # Quick actions
        actions_group = QGroupBox("◢◤ QUICK ACTIONS ◥◣")
        actions_group.setStyleSheet(controls_group.styleSheet())
        actions_layout = QVBoxLayout(actions_group)

        self.btn_map = NeonButton("◢◤ GENERATE THREAT MAP ◥◣")
        self.btn_map.clicked.connect(self.render_embedded_map)
        actions_layout.addWidget(self.btn_map)

        self.btn_export = NeonButton("◢◤ EXPORT INTEL ◥◣")
        self.btn_export.clicked.connect(self.export_data)
        actions_layout.addWidget(self.btn_export)

        actions_layout.addStretch()
        actions_group.setLayout(actions_layout)
        layout.addWidget(actions_group)

        return panel

    def create_map_panel(self):
        """Create the map visualization panel"""
        panel = FuturisticFrame()
        layout = QVBoxLayout(panel)

        # Map header
        map_header = CyberpunkLabel("◢◤ GEOSPATIAL THREAT MAP ◥◣")
        map_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(map_header)

        # Map view with futuristic styling
        self.web_view = QWebEngineView()
        self.web_page = CustomWebEnginePage(self, self.web_view)
        self.web_view.setPage(self.web_page)
        self.web_view.setStyleSheet("""
            QWebEngineView {
                border: 2px solid #00ffff;
                border-radius: 6px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #000000, stop:1 #000011);
            }
        """)
        layout.addWidget(self.web_view)

        # Map status
        self.map_status = CyberpunkLabel("Ready to generate threat map...")
        self.map_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.map_status)

        return panel

    def create_details_panel(self):
        """Create the details view panel"""
        panel = FuturisticFrame()
        layout = QVBoxLayout(panel)

        # Details header with tabs
        details_header = QLabel("◢◤ TARGET INTELLIGENCE DISPLAY ◥◣")
        details_header.setStyleSheet("""
            QLabel {
                color: #00ffff;
                font-weight: bold;
                font-size: 16px;
                padding: 8px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #000000, stop:0.5 #001100, stop:1 #000000);
                border: 1px solid #00ffff;
                border-radius: 4px;
            }
        """)
        details_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(details_header)

        # Details text area with enhanced styling
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setStyleSheet("""
            QTextEdit {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #000000, stop:1 #000011);
                color: #00ff00;
                border: 1px solid #00ff00;
                border-radius: 4px;
                font-family: 'Courier New', monospace;
                font-size: 10px;
                line-height: 1.4;
                padding: 8px;
            }
        """)
        layout.addWidget(self.details_text)

        # Host list
        hosts_label = CyberpunkLabel("◢◤ DETECTED TARGETS ◥◣")
        layout.addWidget(hosts_label)

        self.host_list = QListWidget()
        self.host_list.setStyleSheet("""
            QListWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #000000, stop:1 #000011);
                color: #00ffff;
                border: 1px solid #00ffff;
                border-radius: 4px;
                font-family: 'Courier New', monospace;
                font-size: 9px;
            }
            QListWidget::item {
                padding: 4px;
                border-bottom: 1px solid #001100;
            }
            QListWidget::item:selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #001100, stop:0.5 #002200, stop:1 #001100);
                border: 1px solid #00ff00;
            }
            QListWidget::item:hover:!selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #000000, stop:0.5 #001100, stop:1 #000000);
            }
        """)
        self.host_list.itemClicked.connect(self.display_host_details)
        layout.addWidget(self.host_list)

        return panel

    def create_analytics_tab(self):
        """Create analytics dashboard tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Placeholder for analytics - would integrate with matplotlib or Qt Charts in full implementation
        analytics_label = CyberpunkLabel("◢◤ ANALYTICS ENGINE ◥◣")
        analytics_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        analytics_label.setStyleSheet("font-size: 24px; padding: 40px;")
        layout.addWidget(analytics_label)

        placeholder = CyberpunkLabel("Advanced analytics module\nComing in v2.0 update")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet("color: #888888; font-style: italic;")
        layout.addWidget(placeholder)

        layout.addStretch()
        return tab

    def create_threat_tab(self):
        """Create threat intelligence tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Placeholder for threat intelligence
        threat_label = CyberpunkLabel("◢◤ THREAT INTELLIGENCE ◥◣")
        threat_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        threat_label.setStyleSheet("font-size: 24px; padding: 40px;")
        layout.addWidget(threat_label)

        placeholder = CyberpunkLabel("Threat intelligence feed\nIntegration with threat feeds\nComing in v2.0 update")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet("color: #888888; font-style: italic;")
        layout.addWidget(placeholder)

        layout.addStretch()
        return tab

    def create_status_bar(self):
        """Create status bar"""
        status_frame = QFrame()
        status_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #000000, stop:0.5 #001100, stop:1 #000000);
                border-top: 1px solid #00ffff;
                max-height: 24px;
            }
        """)
        status_layout = QHBoxLayout(status_frame)

        self.status_label = CyberpunkLabel("● SYSTEM ONLINE")
        self.status_label.setStyleSheet("color: #00ff00;")
        status_layout.addWidget(self.status_label)

        status_layout.addStretch()

        self.time_label = CyberpunkLabel("00:00:00")
        status_layout.addWidget(self.time_label)

        return status_frame

    def load_json(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Recon Data", "", "JSON Files (*.json);;All Files (*)"
        )
        if file_path:
            try:
                self.status_label.setText("● LOADING DATA...")
                self.status_label.setStyleSheet("color: #ffff00;")

                with open(file_path, "r", encoding="utf-8") as f:
                    self.raw_hosts = json.load(f)

                # Extract unique ports for filter
                ports = set()
                for h in self.raw_hosts:
                    for p in h.get("open_ports", []):
                        ports.add(str(p))

                self.port_combo.clear()
                self.port_combo.addItem("All")
                for p in sorted(list(ports), key=lambda x: int(x) if str(x).isdigit() else 0):
                    self.port_combo.addItem(p)

                self.apply_filters()
                self.update_hosts_status()

                self.status_label.setText("● DATA LOADED SUCCESSFULLY")
                self.status_label.setStyleSheet("color: #00ff00;")

                # Show success message in details
                self.details_text.setHtml(f"""
                    <div style='color: #00ff00; font-family: "Courier New", monospace;'>
                        <p>✓ Successfully loaded {len(self.raw_hosts)} host records</p>
                        <p>✓ Extracted {len(ports)} unique port signatures</p>
                        <p>✓ Ready for threat analysis</p>
                    </div>
                """)

            except Exception as e:
                self.status_label.setText("● LOAD FAILED")
                self.status_label.setStyleSheet("color: #ff0000;")
                self.details_text.setText(f"Error loading JSON file: {str(e)}")

    def apply_filters(self):
        query = self.search_input.text().lower()
        selected_port = self.port_combo.currentText()
        vulns_only = self.chk_vulns_only.isChecked()

        self.filtered_hosts = []
        self.host_list.clear()

        for host in self.raw_hosts:
            vulns = host.get("vulnerabilities", [])
            if vulns_only and not vulns:
                continue

            ports = [str(p) for p in host.get("open_ports", [])]
            if selected_port != "All" and selected_port not in ports:
                continue

            if query and query not in json.dumps(host).lower():
                continue

            self.filtered_hosts.append(host)
            ip = host.get("ip", "Unknown")
            ports_count = len(host.get("open_ports", []))
            vulns_count = len(host.get("vulnerabilities", []))

            # Color-code based on threat level
            threat_level = "LOW"
            if vulns_count > 5:
                threat_level = "CRITICAL"
            elif vulns_count > 2:
                threat_level = "HIGH"
            elif vulns_count > 0:
                threat_level = "MEDIUM"

            threat_colors = {
                "CRITICAL": "#ff0000",
                "HIGH": "#ff6600",
                "MEDIUM": "#ffaa00",
                "LOW": "#00ff00"
            }

            color = threat_colors.get(threat_level, "#00ff00")

            item_text = f"◢◤ {ip} ◥◣ [{ports_count}P | {vulns_count}V]"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, ip)
            item.setForeground(QColor(color))

            # Add threat level indicator
            if threat_level != "LOW":
                item.setToolTip(f"Threat Level: {threat_level}")

            self.host_list.addItem(item)

        self.lbl_stats.setText(f"Hosts Loaded: {len(self.filtered_hosts)}")
        self.update_hosts_status()

    def update_hosts_status(self):
        self.hosts_status.setText(f"Hosts: {len(self.filtered_hosts)}")
        if len(self.filtered_hosts) > 0:
            self.hosts_status.setStyleSheet("color: #00ff00;")
        else:
            self.hosts_status.setStyleSheet("color: #ff0000;")

    def geolocate_ip(self, ip_address):
        """Synchronous version for backward compatibility"""
        try:
            url = f"http://api.ipstack.com/{ip_address}?access_key={IPSTACK_API_KEY}"
            res = requests.get(url, timeout=2)
            if res.status_code == 200:
                return res.json()
        except Exception:
            pass
        return {}

    def render_embedded_map(self):
        if not self.filtered_hosts:
            self.details_text.setText("Load hosts first before generating a threat map.")
            return

        # Check if we have any valid IPs to geolocate
        ips = [host.get("ip") for host in self.filtered_hosts if host.get("ip")]
        if not ips:
            self.details_text.setText("No valid IP addresses found in the loaded data.")
            return

        self.map_status.setText("● GEOLOCATING TARGETS...")
        self.map_status.setStyleSheet("color: #ffff00;")
        self.btn_map.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(len(ips))

        try:
            # Start geolocation thread
            self.data_thread = DataThread(ips, IPSTACK_API_KEY)
            self.data_thread.geolocation_result.connect(self.handle_geolocation_result)
            self.data_thread.progress_update.connect(self.update_geolocation_progress)
            self.data_thread.finished.connect(self.geolocation_finished)
            self.data_thread.start()
        except Exception as e:
            self.map_status.setText("● THREAD START FAILED")
            self.map_status.setStyleSheet("color: #ff0000;")
            self.details_text.setText(f"Failed to start geolocation thread: {str(e)}")
            self.btn_map.setEnabled(True)
            self.progress_bar.setVisible(False)

    def handle_geolocation_result(self, ip, geo_data):
        self.geolocation_data[ip] = geo_data

    def update_geolocation_progress(self, current, total):
        self.progress_bar.setValue(current)
        self.map_status.setText(f"● GEOLOCATING TARGETS... ({current}/{total})")

    def geolocation_finished(self):
        self.map_status.setText("● GENERATING THREAT MAP...")
        self.map_status.setStyleSheet("color: #ffff00;")
        try:
            self.generate_map_with_data()
            self.btn_map.setEnabled(True)
            self.progress_bar.setVisible(False)
            self.map_status.setText("● THREAT MAP GENERATED SUCCESSFULLY")
            self.map_status.setStyleSheet("color: #00ff00;")
        except Exception as e:
            self.map_status.setText("● MAP GENERATION FAILED")
            self.map_status.setStyleSheet("color: #ff0000;")
            self.details_text.setHtml(f"""
                <div style='color: #ff0000; font-family: "Courier New", monospace;'>
                    <p>✗ Failed to generate threat map</p>
                    <p>Error: {str(e)}</p>
                    <p>Please check your IPStack API key and internet connection.</p>
                </div>
            """)
            self.btn_map.setEnabled(True)
            self.progress_bar.setVisible(False)

    def generate_map_with_data(self):
        if not self.filtered_hosts:
            return

        try:
            # Create futuristic dark map
            m = folium.Map(
                location=[20, 0],
                zoom_start=2,
                tiles="CartoDB dark_matter",
                prefer_canvas=True
            )

            # Add custom CSS for futuristic markers
            m.get_root().html.add_child(folium.Element("""
            <style>
                .leaflet-popup-content {
                    font-family: 'Courier New', monospace;
                    color: #00ffff;
                    background: rgba(0, 0, 0, 0.9);
                    border: 1px solid #00ffff;
                    border-radius: 4px;
                }
                .leaflet-popup-content h4 {
                    margin: 0 0 5px 0;
                    color: #00ff00;
                    text-shadow: 0 0 5px #00ff00;
                }
                .leaflet-popup-content strong {
                    color: #ffff00;
                }
            </style>
            """))

            for host in self.filtered_hosts[:50]:  # Limit to prevent overload
                ip = host.get("ip")
                if ip and ip in self.geolocation_data:
                    geo = self.geolocation_data[ip]
                    lat, lon = geo.get("latitude"), geo.get("longitude")
                    if lat and lon:
                        # Determine marker color based on threat level
                        vulns_count = len(host.get("vulnerabilities", []))
                        if vulns_count > 5:
                            color = "#ff0000"  # Red - Critical
                            icon_color = "red"
                        elif vulns_count > 2:
                            color = "#ff6600"  # Orange - High
                            icon_color = "orange"
                        elif vulns_count > 0:
                            color = "#ffaa00"  # Yellow - Medium
                            icon_color = "yellow"
                        else:
                            color = "#00ff00"  # Green - Low
                            icon_color = "green"

                        # Create custom HTML popup with threat intelligence
                        popup_html = f"""
                        <div style='min-width: 200px;'>
                            <h4>◢◤ TARGET ACQUIRED ◥◣</h4>
                            <hr style='border: 1px solid #00ffff;'>
                            <p><strong>IP Address:</strong> {ip}</p>
                            <p><strong>Location:</strong> {geo.get('city', 'Unknown')}, {geo.get('country_name', 'Unknown')}</p>
                            <p><strong>ISP/Org:</strong> {geo.get('isp', 'Unknown')}</p>
                            <p><strong>Open Ports:</strong> {len(host.get('open_ports', []))}</p>
                            <p><strong>Vulnerabilities:</span style='color: {color};'>{vulns_count}</span></p>
                            <hr style='border: 1px solid #00ffff;'>
                            <p><small>Click for full intelligence report</small></p>
                        </div>
                        """

                        # Create marker with custom icon
                        folium.Marker(
                            location=[lat, lon],
                            popup=folium.Popup(popup_html, max_width=250),
                            icon=folium.Icon(color=icon_color, icon='info-sign'),
                            tooltip=f"Target: {ip} | Threat: {vulns_count} vulns"
                        ).add_to(m)

            # Add legend (using unicode circles instead of Font Awesome to avoid dependency issues)
            legend_html = """
            <div style="position: fixed;
                        bottom: 50px; left: 50px; width: 180px; height: 120px;
                        background-color: rgba(0,0,0,0.8);
                        border: 2px solid #00ffff; border-radius: 6px;
                        z-index:9999; font-size:14px;
                        ">
            &nbsp; <b>◢◤ THREAT LEVEL LEGEND ◥◣</b> <br>
            &nbsp; <span style="color:#ff0000;">●</span> Critical (5+ vulns)<br>
            &nbsp; <span style="color:#ff6600;">●</span> High (3-4 vulns)<br>
            &nbsp; <span style="color:#ffaa00;">●</span> Medium (1-2 vulns)<br>
            &nbsp; <span style="color:#00ff00;">●</span> Low (0 vulns)<br>
            </div>
            """
            m.get_root().html.add_child(folium.Element(legend_html))

            map_html = m._repr_html_()
            if map_html:
                self.web_view.setHtml(map_html)
                count = len([ip for ip in self.geolocation_data if self.geolocation_data.get(ip)])
                self.details_text.setHtml(f"""
                    <div style='color: #00ff00; font-family: "Courier New", monospace;'>
                        <p>✓ Threat map successfully generated</p>
                        <p>✓ {count} targets geolocated and mapped</p>
                        <p>✓ Ready for target selection</p>
                    </div>
                """)
            else:
                raise Exception("Failed to generate map HTML")

        except Exception as e:
            # Re-raise the exception to be caught by geolocation_finished
            raise Exception(f"Map generation error: {str(e)}")

    def select_host_by_ip(self, ip):
        """Finds host by IP from map click and selects it in the list."""
        for i in range(self.host_list.count()):
            item = self.host_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == ip:
                self.host_list.setCurrentItem(item)
                self.display_host_details(item)
                self.tab_widget.setCurrentIndex(0)  # Switch to recon tab
                break

    def display_host_details(self, item):
        index = self.host_list.row(item)
        if index < 0 or index >= len(self.filtered_hosts):
            return

        host = self.filtered_hosts[index]
        ip = host.get("ip", "N/A")
        gen_info = host.get("general_info", {})
        ports = host.get("open_ports", [])
        vulns_raw = host.get("vulnerabilities", [])
        scans = host.get("open_ports_scan", [])
        web_tech = host.get("web_technologies", host.get("web_tech", []))
        tags = host.get("tags", [])

        # Get geolocation data
        geo_data = self.geolocation_data.get(ip, {})

        # Build threat assessment
        vuln_count = len(vulns_raw)
        if vuln_count > 5:
            threat_level = "◢◤ CRITICAL ◥◣"
            threat_color = "#ff0000"
        elif vuln_count > 2:
            threat_level = "◢◤ HIGH ◥◣"
            threat_color = "#ff6600"
        elif vuln_count > 0:
            threat_level = "◢◤ MEDIUM ◥◣"
            threat_color = "#ffaa00"
        else:
            threat_level = "◢◤ LOW ◥◣"
            threat_color = "#00ff00"

        output = []
        output.append(f"<div style='font-family: \"Courier New\", monospace; color: #00ff00;'>")
        output.append("<hr style='border: 1px solid #00ffff;'>")
        output.append(f"<div style='text-align: center;'>")
        output.append(f"<h2 style='color: {threat_color}; text-shadow: 0 0 10px {threat_color};'>")
        output.append(f"{threat_level}<br><span style='font-size: 18px;'>{ip}</span>")
        output.append("</h2>")
        output.append("</div>")
        output.append("<hr style='border: 1px solid #00ffff;'>")

        # Geolocation info
        if geo_data:
            output.append("<h3 style='color: #00ffff;'>◢◤ GEOLOCATION INTELLIGENCE ◥◣</h3>")
            output.append(f"<p><strong>IP Address:</strong> {ip}</p>")
            output.append(f"<p><strong>Location:</strong> {geo_data.get('city', 'Unknown')}, {geo_data.get('region_name', 'Unknown')}, {geo_data.get('country_name', 'Unknown')}</p>")
            output.append(f"<p><strong>Coordinates:</strong> {geo_data.get('latitude', 'N/A')}, {geo_data.get('longitude', 'N/A')}</p>")
            output.append(f"<p><strong>ISP/Organization:</strong> {geo_data.get('isp', 'Unknown')}</p>")
            output.append(f"<p><strong>ASN:</strong> {geo_data.get('asn', 'N/A')}</p>")
            output.append(f"<p><strong>Timezone:</strong> {geo_data.get('time_zone', 'N/A')}</p>")
            output.append("<hr style='border: 1px solid #00ffff;'>")

        # Network info
        output.append("<h3 style='color: #00ffff;'>◢◤ NETWORK PROFILE ◥◣</h3>")
        output.append(f"<p><strong>ISP / Provider:</strong> {gen_info.get('ISP', gen_info.get('Organization', 'N/A'))}</p>")
        output.append(f"<p><strong>ASN:</strong> {gen_info.get('ASN', 'N/A')}</p>")
        output.append(f"<p><strong>Hostnames:</strong> {', '.join(gen_info.get('Hostnames', ['None']))}</p>")
        output.append(f"<p><strong>Domains:</strong> {', '.join(gen_info.get('Domains', ['None']))}</p>")
        output.append(f"<p><strong>Open Ports ({len(ports)}):</strong> {', '.join(map(str, ports)) if ports else 'None'}</p>")
        if web_tech:
            output.append(f"<p><strong>Web Technologies:</strong> {', '.join(web_tech)}</p>")
        if tags:
            output.append(f"<p><strong>Tags:</strong> {', '.join(tags)}</p>")
        output.append("<hr style='border: 1px solid #00ffff;'>")

        # Port scan details
        if scans:
            output.append("<h3 style='color: #00ffff;'>◢◤ PORT SCAN INTELLIGENCE ◥◣</h3>")
            for scan in scans[:10]:  # Limit display
                header = scan.get("header", "Port Banner")
                banner = scan.get("banner", "").strip()
                output.append(f"<p><strong>[ Port {scan.get('port', '?')} ]</strong> {header}</p>")
                if banner:
                    # Escape HTML but preserve line breaks
                    escaped_banner = banner.replace("&", "&amp").replace("<", "&lt").replace(">", "&gt")
                    output.append(f"<pre style='background: #000000; color: #00ff00; padding: 8px; border-radius: 4px;'>{escaped_banner}</pre>")
                output.append("<br>")
            output.append("<hr style='border: 1px solid #00ffff;'>")

        # Vulnerabilities
        output.append(f"<h3 style='color: {threat_color};'>◢◤ VULNERABILITY INTELLIGENCE ({vuln_count}) ◥◣</h3>")
        if vulns_raw:
            for idx, v in enumerate(vulns_raw[:15]):  # Limit display
                cve_id, score, desc = self.parse_cve_entry(v)
                # Color code by CVSS score
                try:
                    score_float = float(score) if score.replace('.', '', 1).isdigit() else 0
                    if score_float >= 9.0:
                        score_color = "#ff0000"
                    elif score_float >= 7.0:
                        score_color = "#ff6600"
                    elif score_float >= 4.0:
                        score_color = "#ffaa00"
                    else:
                        score_color = "#00ff00"
                except:
                    score_color = "#ffff00"

                output.append(f"<p><strong>[{idx+1}] {cve_id}</strong> <span style='color: {score_color};'>CVSS: {score}</span></p>")
                if desc:
                    # Truncate long descriptions
                    short_desc = desc[:200] + "..." if len(desc) > 200 else desc
                    escaped_desc = short_desc.replace("&", "&amp").replace("<", "&lt").replace(">", "&gt")
                    output.append(f"<p>&nbsp;&nbsp;&nbsp;&nbsp;{escaped_desc}</p>")
                output.append("<br>")
            if len(vulns_raw) > 15:
                output.append(f"<p><em>... and {len(vulns_raw) - 15} more vulnerabilities</em></p>")
        else:
            output.append("<p><em>No vulnerabilities detected in this target.</em></p>")
        output.append("<hr style='border: 1px solid #00ffff;'>")

        output.append("<p style='text-align: center; color: #888888; font-size: 10px;'>")
        output.append("◢◤ NEXUS RECON TERMINAL - CLASSIFIED INTELLIGENCE ◥◣")
        output.append("</p>")
        output.append("</div>")

        self.details_text.setHtml("".join(output))

    def export_data(self):
        if not self.filtered_hosts:
            self.details_text.setText("No data to export. Load recon data first.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Intelligence Report", "",
            "JSON Files (*.json);;Text Files (*.txt);;All Files (*)"
        )
        if file_path:
            try:
                if file_path.endswith('.json'):
                    export_data = {
                        'export_timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                        'total_hosts': len(self.raw_hosts),
                        'filtered_hosts': len(self.filtered_hosts),
                        'hosts': self.filtered_hosts,
                        'geolocation_data': self.geolocation_data
                    }
                    with open(file_path, 'w') as f:
                        json.dump(export_data, f, indent=2)
                else:
                    # Text export
                    with open(file_path, 'w') as f:
                        f.write("NEXUS RECON TERMINAL - INTELLIGENCE REPORT\n")
                        f.write("=" * 50 + "\n")
                        f.write(f"Export Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                        f.write(f"Total Hosts: {len(self.raw_hosts)}\n")
                        f.write(f"Filtered Hosts: {len(self.filtered_hosts)}\n\n")

                        for host in self.filtered_hosts:
                            f.write(f"Target: {host.get('ip', 'Unknown')}\n")
                            f.write(f"Ports: {len(host.get('open_ports', []))}\n")
                            f.write(f"Vulnerabilities: {len(host.get('vulnerabilities', []))}\n")
                            f.write("-" * 30 + "\n")

                self.details_text.setText(f"✓ Intelligence report exported successfully to:\n{file_path}")
                self.status_label.setText("● EXPORT COMPLETE")
                self.status_label.setStyleSheet("color: #00ff00;")

            except Exception as e:
                self.details_text.setText(f"Export failed: {str(e)}")
                self.status_label.setText("● EXPORT FAILED")
                self.status_label.setStyleSheet("color: #ff0000;")

    def parse_cve_entry(self, v):
        """Parse a CVE vulnerability entry to extract CVE ID, score, and description."""
        raw_text = v.get("description", "") if isinstance(v, dict) else str(v)
        cve_id = v.get("cve", "CVE-Unknown") if isinstance(v, dict) else "CVE-Unknown"

        cve_match = re.search(r"(CVE-\d{4}-\d+)", raw_text)
        if cve_match:
            cve_id = cve_match.group(1)

        score_match = re.search(r"(\d{1,2}\.\d)", raw_text)
        score = v.get("cvss", score_match.group(1) if score_match else "N/A") if isinstance(v, dict) else (score_match.group(1) if score_match else "N/A")

        clean_desc = re.sub(r"^(?:CVE-\d{4}-\d+[:\s]*)+", "", raw_text)
        if score_match and not isinstance(v, dict):
            clean_desc = re.sub(r"^\d{1,2}\.\d\s*", "", clean_desc.strip())

        return cve_id, score, clean_desc.strip()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ReconApp()
    window.show()
    sys.exit(app.exec())