import sys
import json
import re
import os
import requests
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFileDialog, QListWidget, QListWidgetItem, QTextEdit,
    QLabel, QSplitter, QLineEdit, QCheckBox, QComboBox
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage
import folium

IPSTACK_API_KEY = os.environ.get("IPSTACK_API_KEY", "abc25956a2f21bda82e27b5f08a319f2")


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
        self.setWindowTitle("ShadowNet Covert Recon Terminal")
        self.resize(1150, 750)
        self.setStyleSheet("background-color: #000000; color: #00ff00;")

        self.raw_hosts = []
        self.filtered_hosts = []

        self.init_ui()

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)

        # ==========================================
        # LEFT SIDEBAR CONTROLS
        # ==========================================
        sidebar = QVBoxLayout()
        sidebar_widget = QWidget()
        sidebar_widget.setFixedWidth(260)
        sidebar_widget.setLayout(sidebar)
        sidebar_widget.setStyleSheet("""
            QWidget { background-color: #000000; color: #00ff00; }
            QLabel { color: #00ff00; }
            QLineEdit { background-color: #001100; color: #00ff00; border: 1px solid #00ff00; padding: 5px; border-radius: 3px; }
            QComboBox { background-color: #001100; color: #00ff00; border: 1px solid #00ff00; padding: 5px; border-radius: 3px; }
            QCheckBox { color: #00ff00; spacing: 5px; }
            QCheckBox::indicator { width: 13px; height: 13px; border: 1px solid #00ff00; border-radius: 2px; background-color: #000000; }
            QCheckBox::indicator:checked { background-color: #00ff00; border: 1px solid #00ff00; }
        """)

        self.btn_load = QPushButton("📁 Load Recon JSON")
        self.btn_load.setStyleSheet("background-color: #000000; color: #00ff00; padding: 8px; font-weight: bold; border: 1px solid #00ff00;")
        self.btn_load.clicked.connect(self.load_json)
        sidebar.addWidget(self.btn_load)

        sidebar.addWidget(QLabel("Search Query:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("IP, Banner, Org, CVE...")
        self.search_input.textChanged.connect(self.apply_filters)
        sidebar.addWidget(self.search_input)

        sidebar.addWidget(QLabel("Filter by Port:"))
        self.port_combo = QComboBox()
        self.port_combo.addItem("All")
        self.port_combo.currentIndexChanged.connect(self.apply_filters)
        sidebar.addWidget(self.port_combo)

        self.chk_vulns_only = QCheckBox("Vulnerable Only")
        self.chk_vulns_only.stateChanged.connect(self.apply_filters)
        sidebar.addWidget(self.chk_vulns_only)

        self.lbl_stats = QLabel("Hosts Loaded: 0")
        sidebar.addWidget(self.lbl_stats)

        sidebar.addSpacing(15)
        
        self.btn_map = QPushButton("🗺️ Render Map")
        self.btn_map.setStyleSheet("background-color: #000000; color: #00ff00; padding: 8px; font-weight: bold; border: 1px solid #00ff00;")
        self.btn_map.clicked.connect(self.render_embedded_map)
        sidebar.addWidget(self.btn_map)

        sidebar.addStretch()
        main_layout.addWidget(sidebar_widget)

        # ==========================================
        # RIGHT AREA: TOP (MAP) & BOTTOM (HOSTS / SCANS)
        # ==========================================
        main_vertical_splitter = QSplitter(Qt.Orientation.Vertical)

        # TOP PANEL: Embedded Map with Custom Interceptor Page
        self.web_view = QWebEngineView()
        self.web_page = CustomWebEnginePage(self, self.web_view)
        self.web_view.setPage(self.web_page)
        self.web_view.setStyleSheet("border: 1px solid #00ff00; background: #000000;")
        main_vertical_splitter.addWidget(self.web_view)

        # BOTTOM PANEL: Horizontal Splitter for Hosts (Left) and Scans (Right)
        bottom_horizontal_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Bottom Left: Hosts List
        self.host_list = QListWidget()
        self.host_list.setStyleSheet("background-color: #000000; color: #00ff00; border: 1px solid #00ff00; font-size: 13px;")
        self.host_list.itemClicked.connect(self.display_host_details)
        bottom_horizontal_splitter.addWidget(self.host_list)

        # Bottom Right: Scans and Details Display
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setStyleSheet("background-color: #000000; color: #00ff00; border: 1px solid #00ff00; font-family: monospace; font-size: 12px;")
        bottom_horizontal_splitter.addWidget(self.details_text)

        bottom_horizontal_splitter.setSizes([300, 500])
        main_vertical_splitter.addWidget(bottom_horizontal_splitter)

        main_vertical_splitter.setSizes([300, 450])
        main_layout.addWidget(main_vertical_splitter)

    def load_json(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Recon JSON File", "", "JSON Files (*.json)")
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    self.raw_hosts = json.load(f)
                
                ports = set()
                for h in self.raw_hosts:
                    for p in h.get("open_ports", []):
                        ports.add(str(p))
                
                self.port_combo.clear()
                self.port_combo.addItem("All")
                for p in sorted(list(ports), key=lambda x: int(x) if str(x).isdigit() else 0):
                    self.port_combo.addItem(p)

                self.apply_filters()
            except Exception as e:
                self.details_text.setText(f"Error loading JSON file: {e}")

    def parse_cve_entry(self, v):
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
            item = QListWidgetItem(f"🎯 {ip} [{len(ports)} Ports | {len(vulns)} CVEs]")
            # Attach IP to the item for quick lookup
            item.setData(Qt.ItemDataRole.UserRole, ip)
            self.host_list.addItem(item)

        self.lbl_stats.setText(f"Hosts Loaded: {len(self.filtered_hosts)}")

    def geolocate_ip(self, ip_address):
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
            self.details_text.setText("Load hosts first before generating a map.")
            return

        self.details_text.setText("Geolocating hosts for embedded map generation... please wait.")
        QApplication.processEvents()

        m = folium.Map(location=[20, 0], zoom_start=2, tiles="CartoDB dark_matter")
        
        for host in self.filtered_hosts[:25]:
            ip = host.get("ip")
            if ip:
                geo = self.geolocate_ip(ip)
                lat, lon = geo.get("latitude"), geo.get("longitude")
                if lat and lon:
                    marker = folium.CircleMarker(
                        location=[lat, lon],
                        radius=7,
                        popup=f"IP: {ip}<br>City: {geo.get('city', 'Unknown')}<br>CVEs: {len(host.get('vulnerabilities', []))}<br><i>(Click marker to inspect host)</i>",
                        color="#ff4b4b",
                        fill=True,
                        fill_color="#ff4b4b"
                    )
                    
                    # Attach click listener to marker redirecting to custom scheme
                    click_js = f"function(e) {{ window.location.href = 'selecthost://{ip}'; }}"
                    marker.add_child(folium.Element(f"""
                        <script>
                            setTimeout(function() {{
                                var marker = {marker.get_name()};
                                marker.on('click', {click_js});
                            }}, 500);
                        </script>
                    """))
                    
                    marker.add_to(m)

        map_html = m._repr_html_()
        self.web_view.setHtml(map_html)
        self.details_text.setText("Map successfully updated! Click any marker on the map to inspect its details.")

    def select_host_by_ip(self, ip):
        """Finds host by IP from map click and selects it in the list."""
        for i in range(self.host_list.count()):
            item = self.host_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == ip:
                self.host_list.setCurrentItem(item)
                self.display_host_details(item)
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

        output = []
        output.append("=" * 65)
        output.append(f" TARGET HOST INTEL: {ip}")
        output.append("=" * 65)
        output.append(f"ISP / Provider: {gen_info.get('ISP', gen_info.get('Organization', 'N/A'))}")
        output.append(f"Location:       {gen_info.get('City', 'N/A')}, {gen_info.get('Country', 'N/A')}")
        output.append(f"ASN:            {gen_info.get('ASN', 'N/A')}")
        output.append(f"Hostnames:      {gen_info.get('Hostnames', 'None')}")
        output.append(f"Open Ports:     {', '.join(map(str, ports))}")
        if web_tech:
            output.append(f"Web Tech:       {', '.join(web_tech)}")
        if "tags" in host and host["tags"]:
            output.append(f"Tags:           {', '.join(host.get('tags', []))}")

        if scans:
            output.append("\n" + "-" * 65)
            output.append(" OPEN PORTS SCANS & BANNERS")
            output.append("-" * 65)
            for scan in scans:
                header = scan.get("header", "Port Banner")
                banner = scan.get("banner", "").strip()
                output.append(f"[ Header: {header} ]")
                output.append(banner)
                output.append("")

        output.append("-" * 65)
        output.append(f" IDENTIFIED VULNERABILITIES ({len(vulns_raw)} DETECTED)")
        output.append("-" * 65)

        if vulns_raw:
            for idx, v in enumerate(vulns_raw, 1):
                cve_id, score, desc = self.parse_cve_entry(v)
                output.append(f"[{idx}] {cve_id}  |  CVSS Score: {score}")
                if desc:
                    output.append(f"    Description: {desc}")
                output.append("-" * 45)
        else:
            output.append("No vulnerabilities flagged.")

        self.details_text.setText("\n".join(output))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ReconApp()
    window.show()
    sys.exit(app.exec())
