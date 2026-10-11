import sys
import json
import re
import os
import requests
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFileDialog, QListWidget, QListWidgetItem, QTextEdit,
    QLabel, QSplitter, QCheckBox, QComboBox
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
        if url.scheme() == "selecthost":
            ip_address = url.host()
            self.parent_app.select_host_by_ip(ip_address)
            return False
        return super().acceptNavigationRequest(url, _type, isMainFrame)


class ReconApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Intelligence Lightweight Recon Engine")
        self.resize(1200, 800)
        self.setStyleSheet("background-color: #0d1117; color: #c9d1d9;")

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
        sidebar_widget.setFixedWidth(280)
        sidebar_widget.setLayout(sidebar)
        sidebar_widget.setStyleSheet("background-color: #161b22; padding: 10px; border-radius: 6px;")

        self.btn_load = QPushButton("📁 Upload Recon File")
        self.btn_load.setStyleSheet("background-color: #238636; color: white; padding: 8px; font-weight: bold;")
        self.btn_load.clicked.connect(self.load_json)
        sidebar.addWidget(self.btn_load)

        # --- Multiline Grep Filter ---
        sidebar.addWidget(QLabel("Grep Search (One string per line):"))
        self.search_input = QTextEdit()
        self.search_input.setPlaceholderText("IP, Banner, Org, CVE...\n(One match per line)")
        self.search_input.setMaximumHeight(70)
        self.search_input.setStyleSheet("background-color: #0d1117; color: #c9d1d9; border: 1px solid #30363d;")
        self.search_input.textChanged.connect(self.apply_filters)
        sidebar.addWidget(self.search_input)

        # --- Port Filter ---
        sidebar.addWidget(QLabel("Filter by Port:"))
        self.port_combo = QComboBox()
        self.port_combo.addItem("All")
        self.port_combo.currentIndexChanged.connect(self.apply_filters)
        sidebar.addWidget(self.port_combo)

        # --- Hostnames Filter ---
        sidebar.addWidget(QLabel("Filter by Hostname:"))
        self.hostname_combo = QComboBox()
        self.hostname_combo.addItem("All")
        self.hostname_combo.currentIndexChanged.connect(self.apply_filters)
        sidebar.addWidget(self.hostname_combo)

        # --- Web Tech Filter ---
        sidebar.addWidget(QLabel("Filter by Web Tech:"))
        self.web_tech_combo = QComboBox()
        self.web_tech_combo.addItem("All")
        self.web_tech_combo.currentIndexChanged.connect(self.apply_filters)
        sidebar.addWidget(self.web_tech_combo)

        # --- ASN Filter ---
        sidebar.addWidget(QLabel("Filter by ASN:"))
        self.asn_combo = QComboBox()
        self.asn_combo.addItem("All")
        self.asn_combo.currentIndexChanged.connect(self.apply_filters)
        sidebar.addWidget(self.asn_combo)

        # --- Country Filter ---
        sidebar.addWidget(QLabel("Filter by Country:"))
        self.country_combo = QComboBox()
        self.country_combo.addItem("All")
        self.country_combo.currentIndexChanged.connect(self.on_country_changed)
        sidebar.addWidget(self.country_combo)

        # --- City Filter ---
        sidebar.addWidget(QLabel("Filter by City:"))
        self.city_combo = QComboBox()
        self.city_combo.addItem("All")
        self.city_combo.currentIndexChanged.connect(self.apply_filters)
        sidebar.addWidget(self.city_combo)

        # --- Checkboxes ---
        self.chk_vulns_only = QCheckBox("Vulnerable Only")
        self.chk_vulns_only.stateChanged.connect(self.apply_filters)
        sidebar.addWidget(self.chk_vulns_only)

        self.chk_show_scans = QCheckBox("Show Port Scans / Banners")
        self.chk_show_scans.setChecked(True)
        self.chk_show_scans.stateChanged.connect(self.refresh_details_display)
        sidebar.addWidget(self.chk_show_scans)

        self.lbl_stats = QLabel("Hosts Loaded: 0")
        sidebar.addWidget(self.lbl_stats)

        sidebar.addSpacing(10)
        
        self.btn_map = QPushButton("🗺️ Render Map")
        self.btn_map.setStyleSheet("background-color: #1f6beb; color: white; padding: 8px; font-weight: bold;")
        self.btn_map.clicked.connect(self.render_embedded_map)
        sidebar.addWidget(self.btn_map)

        sidebar.addStretch()
        main_layout.addWidget(sidebar_widget)

        # ==========================================
        # RIGHT AREA: MAP (TOP) & DETAILS (BOTTOM)
        # ==========================================
        main_vertical_splitter = QSplitter(Qt.Orientation.Vertical)

        # TOP PANEL: Embedded Map
        self.web_view = QWebEngineView()
        self.web_page = CustomWebEnginePage(self, self.web_view)
        self.web_view.setPage(self.web_page)
        self.web_view.setStyleSheet("border: none; background: #0d1117;")
        main_vertical_splitter.addWidget(self.web_view)

        # BOTTOM PANEL: Host List (Left) & Host Details (Right)
        bottom_horizontal_splitter = QSplitter(Qt.Orientation.Horizontal)

        self.host_list = QListWidget()
        self.host_list.setStyleSheet("background-color: #161b22; border: 1px solid #30363d; font-size: 13px;")
        self.host_list.itemClicked.connect(self.display_host_details)
        bottom_horizontal_splitter.addWidget(self.host_list)

        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setStyleSheet("background-color: #0d1117; border: 1px solid #30363d; font-family: monospace; font-size: 12px;")
        bottom_horizontal_splitter.addWidget(self.details_text)

        bottom_horizontal_splitter.setSizes([300, 500])
        main_vertical_splitter.addWidget(bottom_horizontal_splitter)

        main_vertical_splitter.setSizes([300, 450])
        main_layout.addWidget(main_vertical_splitter)

    def load_json(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Recon File", "", "JSON Files (*.json)")
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                if isinstance(data, list):
                    self.raw_hosts = data
                elif isinstance(data, dict):
                    self.raw_hosts = data.get("hosts") or data.get("results") or [data]
                else:
                    self.raw_hosts = []
                
                ports = set()
                hostnames = set()
                web_techs = set()
                asns = set()
                countries = set()

                for h in self.raw_hosts:
                    for p in h.get("open_ports", []):
                        ports.add(str(p))

                    gen_info = h.get("general_info") or h.get("general_information") or {}
                    
                    hn = gen_info.get("Hostnames") or h.get("hostnames")
                    if hn:
                        if isinstance(hn, list):
                            hostnames.update(hn)
                        else:
                            hostnames.add(str(hn))

                    wt = h.get("web_technologies") or h.get("web_tech") or []
                    web_techs.update(wt)

                    asn = gen_info.get("ASN")
                    if asn:
                        asns.add(str(asn))

                    country = gen_info.get("Country") or gen_info.get("country") or h.get("country")
                    if country:
                        countries.add(str(country))

                self._populate_combo(self.port_combo, sorted(list(ports), key=lambda x: int(x) if x.isdigit() else 0))
                self._populate_combo(self.hostname_combo, sorted(list(hostnames)))
                self._populate_combo(self.web_tech_combo, sorted(list(web_techs)))
                self._populate_combo(self.asn_combo, sorted(list(asns)))
                self._populate_combo(self.country_combo, sorted(list(countries)))

                # Dynamically update available cities based on country selection
                self.update_city_options()
                self.apply_filters()
            except Exception as e:
                self.details_text.setText(f"Error loading file: {e}")

    def _populate_combo(self, combo, items):
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("All")
        for item in items:
            if item and item != "N/A":
                combo.addItem(item)
        combo.blockSignals(False)

    def on_country_changed(self):
        """When country dropdown changes, dynamically update the city dropdown."""
        self.update_city_options()
        self.apply_filters()

    def update_city_options(self):
        """Populates the city dropdown with cities that belong ONLY to the selected country."""
        selected_country = self.country_combo.currentText()
        cities = set()

        for h in self.raw_hosts:
            gen_info = h.get("general_info") or h.get("general_information") or {}
            host_country = str(gen_info.get("Country") or gen_info.get("country") or h.get("country", ""))
            city = gen_info.get("City") or gen_info.get("city") or h.get("city")

            # Filter cities by selected country (or include all if "All" is selected)
            if selected_country == "All" or selected_country == host_country:
                if city:
                    cities.add(str(city))

        current_city = self.city_combo.currentText()
        self._populate_combo(self.city_combo, sorted(list(cities)))

        # Preserve selected city if it's still available in the new list
        index = self.city_combo.findText(current_city)
        if index >= 0:
            self.city_combo.blockSignals(True)
            self.city_combo.setCurrentIndex(index)
            self.city_combo.blockSignals(False)

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
        raw_grep = self.search_input.toPlainText().strip()
        grep_terms = [t.lower() for t in raw_grep.splitlines() if t.strip()]

        selected_port = self.port_combo.currentText()
        selected_hostname = self.hostname_combo.currentText()
        selected_web_tech = self.web_tech_combo.currentText()
        selected_asn = self.asn_combo.currentText()
        selected_country = self.country_combo.currentText()
        selected_city = self.city_combo.currentText()
        vulns_only = self.chk_vulns_only.isChecked()

        self.filtered_hosts = []
        self.host_list.clear()

        for host in self.raw_hosts:
            gen_info = host.get("general_info") or host.get("general_information") or {}
            vulns = host.get("vulnerabilities", [])
            ports = [str(p) for p in host.get("open_ports", [])]
            web_techs = host.get("web_technologies") or host.get("web_tech") or []
            
            hn = gen_info.get("Hostnames") or host.get("hostnames") or ""
            hn_str = ", ".join(hn) if isinstance(hn, list) else str(hn)

            host_country = str(gen_info.get("Country") or gen_info.get("country") or host.get("country", ""))
            host_city = str(gen_info.get("City") or gen_info.get("city") or host.get("city", ""))

            if vulns_only and not vulns:
                continue

            if selected_port != "All" and selected_port not in ports:
                continue

            if selected_hostname != "All" and selected_hostname not in hn_str:
                continue

            if selected_web_tech != "All" and selected_web_tech not in web_techs:
                continue

            if selected_asn != "All" and selected_asn != str(gen_info.get("ASN", "")):
                continue

            if selected_country != "All" and selected_country != host_country:
                continue

            if selected_city != "All" and selected_city != host_city:
                continue

            # Grep logic: matches host JSON against all specified lines
            if grep_terms:
                host_dump = json.dumps(host).lower()
                if not all(term in host_dump for term in grep_terms):
                    continue

            self.filtered_hosts.append(host)
            ip = host.get("ip", "Unknown")
            item = QListWidgetItem(f"🎯 {ip} [{len(ports)} Ports | {len(vulns)} CVEs]")
            item.setData(Qt.ItemDataRole.UserRole, ip)
            self.host_list.addItem(item)

        self.lbl_stats.setText(f"Hosts Loaded: {len(self.filtered_hosts)}")

    def geolocate_ip(self, ip_address):
        """API fallback executed ONLY when render map is clicked and JSON lacks coordinates."""
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

        self.details_text.setText("Parsing coordinates and rendering map... please wait.")
        QApplication.processEvents()

        m = folium.Map(
            location=[20, 0], 
            zoom_start=2, 
            tiles="CartoDB dark_matter",
            no_wrap=True
        )
        
        for host in self.filtered_hosts[:25]:
            ip = host.get("ip")
            if not ip:
                continue

            gen_info = host.get("general_info") or host.get("general_information") or {}
            
            # --- 1. READ DIRECTLY FROM JSON FILE FIRST ---
            lat = host.get("latitude") or host.get("lat") or gen_info.get("latitude") or gen_info.get("lat")
            lon = host.get("longitude") or host.get("lon") or gen_info.get("longitude") or gen_info.get("lon")
            city = gen_info.get("City") or gen_info.get("city") or host.get("city", "Unknown")

            # --- 2. FALLBACK TO IPSTACK API ONLY ON CLICK IF LAT/LON MISSING ---
            if lat is None or lon is None:
                geo = self.geolocate_ip(ip)
                lat = geo.get("latitude") or geo.get("lat")
                lon = geo.get("longitude") or geo.get("lon")
                city = geo.get("city", city)

            if lat is not None and lon is not None:
                try:
                    lat, lon = float(lat), float(lon)
                    marker = folium.CircleMarker(
                        location=[lat, lon],
                        radius=7,
                        popup=f"IP: {ip}<br>City: {city}<br>CVEs: {len(host.get('vulnerabilities', []))}<br><i>(Click marker to inspect host)</i>",
                        color="#ff4b4b",
                        fill=True,
                        fill_color="#ff4b4b"
                    )
                    
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
                except ValueError:
                    continue

        custom_css = """
        <style>
            html, body {
                width: 100% !important;
                height: 100% !important;
                margin: 0 !important;
                padding: 0 !important;
                background-color: #0d1117 !important;
                overflow: hidden !important;
            }
            .folium-map {
                width: 100% !important;
                height: 100% !important;
                margin: 0 !important;
                padding: 0 !important;
            }
        </style>
        """
        map_html = m._repr_html_() + custom_css
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

    def refresh_details_display(self):
        """Re-render current host details when check-box toggles."""
        current_item = self.host_list.currentItem()
        if current_item:
            self.display_host_details(current_item)

    def display_host_details(self, item):
        index = self.host_list.row(item)
        if index < 0 or index >= len(self.filtered_hosts):
            return

        host = self.filtered_hosts[index]
        ip = host.get("ip", "N/A")
        gen_info = host.get("general_info") or host.get("general_information") or {}
        ports = host.get("open_ports", [])
        vulns_raw = host.get("vulnerabilities", [])
        scans = host.get("open_ports_scan", [])
        web_tech = host.get("web_technologies") or host.get("web_tech") or []

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

        if self.chk_show_scans.isChecked() and scans:
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
            parsed_vulns = []
            for v in vulns_raw:
                cve_id, score, desc = self.parse_cve_entry(v)
                try:
                    num_score = float(score)
                except (ValueError, TypeError):
                    num_score = -1.0
                parsed_vulns.append({
                    "cve_id": cve_id,
                    "score": score,
                    "num_score": num_score,
                    "desc": desc
                })

            parsed_vulns.sort(key=lambda x: x["num_score"], reverse=True)

            for idx, v in enumerate(parsed_vulns, 1):
                output.append(f"[{idx}] {v['cve_id']}  |  CVSS Score: {v['score']}")
                if v['desc']:
                    output.append(f"    Description: {v['desc']}")
                output.append("-" * 45)
        else:
            output.append("No vulnerabilities flagged.")

        self.details_text.setText("\n".join(output))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ReconApp()
    window.show()
    sys.exit(app.exec())
