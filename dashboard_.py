import streamlit as st
import pandas as pd
import requests
import json
import re
import plotly.express as px

# Page Setup
st.set_page_config(
    page_title="Intelligence Platform",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Hardcoded IPstack API Key
IPSTACK_API_KEY = "abc25956a2f21bda82e27b5f08a319f2"

# Custom Dark Styling
st.markdown("""
<style>
    .stApp {
        background-color: #0d1117;
        color: #c9d1d9;
    }
    .metric-card {
        background-color: #161b22;
        border: 1px solid #30363d;
        padding: 15px;
        border-radius: 8px;
    }
    .cve-badge-critical {
        background-color: #da3633;
        color: white;
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: bold;
    }
    .cve-badge-high {
        background-color: #d29922;
        color: black;
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: bold;
    }
    .cve-badge-info {
        background-color: #238636;
        color: white;
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: bold;
    }
    .scan-box {
        background-color: #161b22;
        border: 1px solid #30363d;
        padding: 10px;
        border-radius: 6px;
        font-family: monospace;
        white-space: pre-wrap;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

st.title("📡 Intelligence Recon & Target Tracking Engine")

# --- Helper Functions ---

@st.cache_data(ttl=3600)
def geolocate_ip(ip_address: str) -> dict:
    """Fetch latitude, longitude, and country from IPstack."""
    try:
        url = f"http://api.ipstack.com/{ip_address}?access_key={IPSTACK_API_KEY}"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            return res.json()
    except Exception:
        pass
    return {}

def parse_cve_entry(v):
    """
    Parses CVE items with formats like:
    'CVE-2026-60001: CVE-2026-60001 6.5sshd in OpenSSH before 10.4 does not always honor...'
    Extracts CVE ID, Score (float), and clean description.
    """
    if isinstance(v, dict):
        cve_id = v.get("cve", "")
        desc = v.get("description", "")
        raw_text = f"{cve_id}: {desc}"
    else:
        raw_text = str(v)

    # 1. Extract CVE ID
    cve_match = re.search(r"(CVE-\d{4}-\d+)", raw_text)
    cve_id = cve_match.group(1) if cve_match else "CVE-Unknown"

    # 2. Extract CVSS Score
    score = None
    score_match = re.search(r"(\d{1,2}\.\d)", raw_text)
    if score_match:
        try:
            score = float(score_match.group(1))
        except ValueError:
            score = None

    # 3. Clean up description text
    clean_desc = raw_text
    clean_desc = re.sub(r"^(?:CVE-\d{4}-\d+[:\s]*)+", "", clean_desc)
    if score_match:
        clean_desc = re.sub(r"^\d{1,2}\.\d\s*", "", clean_desc.strip())

    return {
        "cve_id": cve_id,
        "score": score,
        "description": clean_desc.strip()
    }

# --- Sidebar Controls ---
st.sidebar.header("⚙️ Data Source")
uploaded_file = st.sidebar.file_uploader("Upload Recon JSON", type=["json"])

raw_hosts = []
if uploaded_file is not None:
    try:
        raw_hosts = json.load(uploaded_file)
    except Exception as e:
        st.error(f"Error reading JSON: {e}")

if not raw_hosts:
    st.info("👆 Upload your recon JSON file in the sidebar to populate the map and filters.")
else:
    # --- Dynamic Dropdown Collection ---
    st.sidebar.header("🔍 Filters")
    
    ports = set()
    tags = set()
    hostnames = set()
    web_techs = set()
    asns = set()
    locations = set()

    for h in raw_hosts:
        # Collect Ports
        for p in h.get("open_ports", []):
            ports.add(str(p))

        # Collect Tags
        for t in h.get("tags", []):
            if not str(t).replace(".", "", 1).isdigit():
                tags.add(str(t))

        # Schema fallback checks
        gen_info = h.get("general_info") or h.get("general_information") or {}

        # Hostnames
        hn = gen_info.get("Hostnames") or h.get("hostnames")
        if hn:
            if isinstance(hn, list):
                hostnames.update(hn)
            else:
                hostnames.add(str(hn))

        # Web Tech
        wt = h.get("web_technologies") or h.get("web_tech") or []
        web_techs.update(wt)

        # ASN
        asn = gen_info.get("ASN")
        if asn:
            asns.add(str(asn))

        # Location
        city = gen_info.get("City", "")
        country = gen_info.get("Country", "")
        if city or country:
            locations.add(f"{city}, {country}".strip(", "))

    # Helper for sorted options
    sorted_ports = ["All"] + sorted(list(ports), key=lambda x: int(x) if x.isdigit() else 0)
    sorted_tags = ["All"] + sorted(list(tags))
    sorted_hostnames = ["All"] + sorted(list(hostnames))
    sorted_web_techs = ["All"] + sorted(list(web_techs))
    sorted_asns = ["All"] + sorted(list(asns))
    sorted_locations = ["All"] + sorted(list(locations))

    # --- Sidebar Inputs ---
    search_query = st.sidebar.text_input("Search IP, Banner, Org...")
    selected_port = st.sidebar.selectbox("Filter by Port", sorted_ports)
    selected_tag = st.sidebar.selectbox("Filter by Tag", sorted_tags)
    selected_hostname = st.sidebar.selectbox("Filter by Hostname", sorted_hostnames)
    selected_web_tech = st.sidebar.selectbox("Filter by Web Tech", sorted_web_techs)
    selected_asn = st.sidebar.selectbox("Filter by ASN", sorted_asns)
    selected_location = st.sidebar.selectbox("Filter by Location", sorted_locations)

    vulns_only = st.sidebar.checkbox("Vulnerable Only")
    show_scans = st.sidebar.checkbox("Show Port Scans / Banners", value=True)
    min_cvss = st.sidebar.slider("Min CVSS Severity", 0.0, 10.0, 0.0, step=0.5)

    # Process and filter host records
    filtered_hosts = []
    map_data = []

    with st.spinner("Processing intelligence data and geolocating hosts..."):
        for host in raw_hosts:
            vulns_raw = host.get("vulnerabilities", [])
            parsed_vulns = [parse_cve_entry(v) for v in vulns_raw]

            if vulns_only and not parsed_vulns:
                continue

            max_cvss = max([v["score"] for v in parsed_vulns if v["score"] is not None], default=0.0)
            if min_cvss > 0 and max_cvss < min_cvss:
                continue

            # Check Filters
            gen_info = host.get("general_info") or host.get("general_information") or {}
            host_ports = [str(p) for p in host.get("open_ports", [])]
            host_tags = [str(t) for t in host.get("tags", [])]
            host_web_techs = host.get("web_technologies") or host.get("web_tech") or []

            hn = gen_info.get("Hostnames") or host.get("hostnames") or ""
            hn_str = ", ".join(hn) if isinstance(hn, list) else str(hn)
            loc_str = f"{gen_info.get('City', '')}, {gen_info.get('Country', '')}".strip(", ")

            if selected_port != "All" and selected_port not in host_ports:
                continue

            if selected_tag != "All" and selected_tag not in host_tags:
                continue

            if selected_hostname != "All" and selected_hostname not in hn_str:
                continue

            if selected_web_tech != "All" and selected_web_tech not in host_web_techs:
                continue

            if selected_asn != "All" and selected_asn != str(gen_info.get("ASN", "")):
                continue

            if selected_location != "All" and selected_location != loc_str:
                continue

            if search_query:
                query = search_query.lower()
                if query not in json.dumps(host).lower():
                    continue

            # Attach parsed vulns back to host dict
            host["parsed_vulns"] = parsed_vulns
            filtered_hosts.append(host)

            # Geolocation Lookup
            ip = host.get("ip")
            if ip:
                geo_info = geolocate_ip(ip)
                lat = geo_info.get("latitude")
                lon = geo_info.get("longitude")
                if lat and lon:
                    map_data.append({
                        "ip": ip,
                        "lat": lat,
                        "lon": lon,
                        "city": geo_info.get("city", "Unknown"),
                        "country": geo_info.get("country_name", "Unknown"),
                        "vulns_count": len(parsed_vulns),
                        "max_cvss": max_cvss
                    })

    # --- Metrics Bar ---
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Hosts", len(filtered_hosts))
    total_cves = sum(len(h["parsed_vulns"]) for h in filtered_hosts)
    c2.metric("Total CVEs Detected", total_cves)
    c3.metric("Geolocated IPs", len(map_data))
    c4.metric("Active Port Filter", selected_port)

    st.markdown("---")

    # --- Interactive Global Map with Click Detection ---
    st.subheader("🌐 Interactive Map (Click any host marker to inspect)")

    selected_ip_from_map = None

    if map_data:
        df_map = pd.DataFrame(map_data)

        fig = px.scatter_mapbox(
            df_map,
            lat="lat",
            lon="lon",
            hover_name="ip",
            hover_data={"city": True, "country": True, "vulns_count": True, "max_cvss": True, "lat": False, "lon": False},
            color="vulns_count",
            size="vulns_count",
            size_max=20,
            color_continuous_scale="Reds",
            zoom=1,
            height=500
        )
        fig.update_layout(
            mapbox_style="carto-darkmatter",
            margin={"r": 0, "t": 0, "l": 0, "b": 0}
        )

        map_event = st.plotly_chart(fig, use_container_width=True, on_select="rerun")

        if map_event and "selection" in map_event and map_event["selection"].get("points"):
            point_index = map_event["selection"]["points"][0]["point_index"]
            selected_ip_from_map = df_map.iloc[point_index]["ip"]
            st.success(f"🎯 Target Selected from Map: **{selected_ip_from_map}**")
    else:
        st.warning("No geographic points available for the selected filters.")

    st.markdown("---")

    # --- Display Detailed Host Results ---
    st.subheader("🎯 Host Findings")

    display_hosts = filtered_hosts
    if selected_ip_from_map:
        display_hosts = [h for h in filtered_hosts if h.get("ip") == selected_ip_from_map]
        if st.button("❌ Clear Map Selection"):
            st.rerun()

    for host in display_hosts:
        ip = host.get("ip", "Unknown IP")
        gen_info = host.get("general_info") or host.get("general_information") or {}
        vulns = host.get("parsed_vulns", [])
        ports = host.get("open_ports", [])
        scans = host.get("open_ports_scan", [])
        web_tech = host.get("web_technologies") or host.get("web_tech") or []

        with st.expander(f"🖥️ {ip} — Open Ports: {len(ports)} | Total CVEs: {len(vulns)}", expanded=True if selected_ip_from_map else False):
            col1, col2 = st.columns([1, 2])

            with col1:
                st.markdown("### Host Information")
                st.write(f"**IP Address:** `{ip}`")
                st.write(f"**ASN:** {gen_info.get('ASN', 'N/A')}")
                st.write(f"**Organization / ISP:** {gen_info.get('Organization', gen_info.get('ISP', 'N/A'))}")
                st.write(f"**Location:** {gen_info.get('City', 'N/A')}, {gen_info.get('Country', 'N/A')}")
                st.write(f"**Hostnames:** {gen_info.get('Hostnames', 'None')}")
                
                if host.get("tags"):
                    st.write(f"**Tags:** {', '.join(map(str, host.get('tags')))}")
                
                if web_tech:
                    st.write(f"**Web Tech:** {', '.join(web_tech)}")
                
                st.markdown("#### Open Ports")
                st.write(", ".join([f"`{p}`" for p in ports]))

                # Port Scans and Raw Banner Output (Dynamic Toggle)
                if show_scans and scans:
                    st.markdown("#### Port Scans & Banners")
                    for scan in scans:
                        header = scan.get("header", "Port Banner")
                        banner = scan.get("banner", "").strip()
                        st.caption(f"**Header:** `{header}`")
                        st.markdown(f"<div class='scan-box'>{banner}</div>", unsafe_allow_html=True)

            with col2:
                st.markdown(f"### All Vulnerabilities ({len(vulns)})")
                if vulns:
                    for idx, v in enumerate(vulns, 1):
                        score = v["score"]
                        score_display = f"Score: {score}" if score is not None else "Score: N/A"

                        if score and score >= 7.0:
                            badge = f"<span class='cve-badge-critical'>{score_display}</span>"
                        elif score and score >= 4.0:
                            badge = f"<span class='cve-badge-high'>{score_display}</span>"
                        else:
                            badge = f"<span class='cve-badge-info'>{score_display}</span>"

                        st.markdown(
                            f"**{idx}. {v['cve_id']}** {badge}<br/>"
                            f"_{v['description']}_",
                            unsafe_allow_html=True
                        )
                        st.markdown("<hr style='margin: 8px 0; border-color: #30363d;'/>", unsafe_allow_html=True)
                else:
                    st.success("No vulnerabilities flagged for this host.")
