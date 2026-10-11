#!/usr/bin/env python3
"""
Shodan Facet Scraper & Recon - Modern Edition
Hierarchical IP collection with Mullvad VPN + Auto Recon Mode
"""
import argparse
import subprocess
import sys
import os
import time
import json
import re
import threading
import warnings
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from datetime import datetime
from io import StringIO

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from tqdm import tqdm
import random
from urllib.parse import quote_plus

# Suppress Selenium warnings and non-critical errors
warnings.filterwarnings("ignore", category=DeprecationWarning)
os.environ["PYTHONWARNINGS"] = "ignore::DeprecationWarning"

# ============================================================================
# CONSTANTS & CONFIG
# ============================================================================
MIN_ASN_COUNT = 100
CITY_IP_DEEP_THRESHOLD = 100
RATE_LIMIT_BETWEEN_CITIES = 15

# Global error tracking (silent)
error_counts = {"asn": 0, "org": 0, "ip_city": 0, "ip_asn": 0, "ip_org": 0, "recon": 0}

# ANSI Colors for modern terminal output
class Color:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RESET = '\033[0m'

    @staticmethod
    def success(msg: str) -> str:
        return f"{Color.GREEN}✓{Color.RESET} {msg}"

    @staticmethod
    def error(msg: str) -> str:
        return f"{Color.RED}✗{Color.RESET} {msg}"

    @staticmethod
    def warning(msg: str) -> str:
        return f"{Color.YELLOW}⚠{Color.RESET} {msg}"

    @staticmethod
    def info(msg: str) -> str:
        return f"{Color.BLUE}ℹ{Color.RESET} {msg}"

    @staticmethod
    def debug(msg: str) -> str:
        return f"{Color.CYAN}»{Color.RESET} {msg}"

    @staticmethod
    def highlight(msg: str) -> str:
        return f"{Color.BOLD}{Color.CYAN}{msg}{Color.RESET}"


@dataclass
class HostData:
    """Modern dataclass for host reconnaissance data"""
    ip: str
    tags: List[str]
    general_info: Dict[str, str]
    web_technologies: List[str]
    open_ports: List[int]
    open_ports_scan: List[Dict]
    vulnerabilities: List[Dict]
    error: Optional[str] = None

    def to_json(self) -> Dict:
        return asdict(self)


# ============================================================================
# MULLVAD VPN MANAGEMENT
# ============================================================================
class MullvadVPN:
    """Modern Mullvad VPN CLI wrapper"""

    @staticmethod
    def is_connected() -> bool:
        """Check if Mullvad is connected"""
        try:
            result = subprocess.run(["mullvad", "status"], capture_output=True, text=True, timeout=5)
            return "Connected" in result.stdout
        except Exception as e:
            print(Color.warning(f"Could not check Mullvad status: {e}"))
            return False

    @staticmethod
    def connect(country: Optional[str] = None) -> bool:
        """Connect to Mullvad VPN, optionally to a specific country"""
        try:
            if country:
                print(Color.info(f"Setting Mullvad relay to {country}..."))
                subprocess.run(["mullvad", "relay", "set", "location", country], check=True, timeout=10)

            print(Color.info("Connecting to Mullvad VPN..."))
            subprocess.run(["mullvad", "connect"], check=True, timeout=30)

            time.sleep(2)  # Wait for connection to stabilize
            if MullvadVPN.is_connected():
                print(Color.success(f"Connected to Mullvad{' (' + country + ')' if country else ''}"))
                return True
        except subprocess.CalledProcessError as e:
            print(Color.error(f"Mullvad connection failed: {e}"))
        except Exception as e:
            print(Color.error(f"Mullvad error: {e}"))
        return False

    @staticmethod
    def disconnect() -> bool:
        """Disconnect Mullvad VPN"""
        try:
            print(Color.info("Disconnecting from Mullvad..."))
            subprocess.run(["mullvad", "disconnect"], check=True, timeout=10)
            print(Color.success("Disconnected from Mullvad"))
            return True
        except Exception as e:
            print(Color.error(f"Mullvad disconnect error: {e}"))
            return False

    @staticmethod
    def get_status() -> str:
        """Get current Mullvad status"""
        try:
            result = subprocess.run(["mullvad", "status"], capture_output=True, text=True, timeout=5)
            return result.stdout.strip()
        except Exception:
            return "Unknown"


# ============================================================================
# SELENIUM WEBDRIVER MANAGEMENT
# ============================================================================
def get_driver(use_vpn: bool = False) -> webdriver.Chrome:
    """Create and return a headless Chrome WebDriver"""
    opts = webdriver.ChromeOptions()
    opts.add_argument("--headless")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)

    service = Service("/usr/bin/chromedriver")
    return webdriver.Chrome(service=service, options=opts)


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================
def _safe_int(s: str) -> int:
    """Safely convert string to int"""
    try:
        return int(re.sub(r'\D', '', str(s)))
    except:
        return 0


def _check_cloudflare(driver: webdriver.Chrome) -> bool:
    """Check if page is blocked by Cloudflare"""
    try:
        return bool(driver.find_elements(By.ID, "challenge-body"))
    except:
        return False


# ============================================================================
# FACET SCRAPING FUNCTIONS
# ============================================================================
def fetch_cities(query: str) -> Tuple[List[str], List[str]]:
    """Fetch cities for a given query"""
    city_list = []
    number_of_ips = []
    print(Color.info(f"Fetching cities for query: {Color.highlight(query)}"))

    try:
        driver = get_driver()
        facet_url = f"https://www.shodan.io/search/facet?query={quote_plus(query)}&facet=city"
        driver.get(facet_url)

        # WebDriverWait verification: verify page loaded (max 15s timeout)
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".facets-card")))

        rows = driver.execute_script("return Array.from(document.querySelectorAll('.facets-card .name a')).map(a=>a.innerText.trim()).filter(x=>x);")
        city_list = rows
        vals = driver.execute_script("return Array.from(document.querySelectorAll('.facets-card .value')).map(v=>v.innerText.trim()).filter(x=>x);")
        number_of_ips = vals

        print(Color.success(f"Fetched {len(city_list)} cities"))
    except Exception as e:
        print(Color.error(f"fetch_cities error: {e}"))
    finally:
        try:
            driver.quit()
        except:
            pass

    return city_list, number_of_ips


def check_asn(query: str, cities: List[str]) -> Tuple[Dict, Dict]:
    """Check ASNs for each city (hierarchical)"""
    driver = None
    big_asn = {}
    small_asn = {}
    print(Color.info("Grabbing ASNs (hierarchical)..."))

    for city in cities:
        big_asn.setdefault(city, [])
        small_asn.setdefault(city, [])
        try:
            driver = get_driver()
            check_asn_url = f"https://www.shodan.io/search/facet?query={quote_plus(query + f' city:\"{city}\"')}&facet=asn"
            driver.get(check_asn_url)

            # WebDriverWait verification
            WebDriverWait(driver, 15).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".card.card-padding.u-full-width.facets-card"))
            )
            print(Color.debug(f"Page verified for {city}"))

            if _check_cloudflare(driver):
                raise Exception("Cloudflare detected")

            rows = driver.find_elements(By.CSS_SELECTOR, ".card.card-padding.u-full-width.facets-card")
            asn_found = 0

            for row in rows:
                try:
                    try:
                        asn = row.find_element(By.CSS_SELECTOR, ".facet-name, .name, h4, .facet-label").text.strip()
                    except:
                        asn = row.find_element(By.CLASS_NAME, "name").text.strip()

                    try:
                        noi_raw = row.find_element(By.CSS_SELECTOR, ".facet-value, .value, span.count, .facet-count").text.strip()
                    except:
                        noi_raw = row.find_element(By.CLASS_NAME, "value").text.strip()

                    noi = _safe_int(noi_raw)
                    if noi >= MIN_ASN_COUNT:
                        asn_found += 1
                        big_asn[city].append(asn)
                except Exception:
                    continue

            print(Color.success(f"[{city}] Found {asn_found} ASNs"))
        except Exception:
            error_counts["asn"] += 1
        finally:
            if driver:
                driver.quit()
            time.sleep(RATE_LIMIT_BETWEEN_CITIES)

    return big_asn, small_asn


def check_org(query: str, big_asn: Dict) -> Dict:
    """Check organizations for big ASNs"""
    driver = None
    big_orgs = {}
    print(Color.info("Checking organizations for big ASNs..."))

    for city, asn_list in big_asn.items():
        big_orgs.setdefault(city, {})
        for asn in asn_list:
            big_orgs[city].setdefault(asn, [])
            try:
                driver = get_driver()
                org_query = f'{query} city:"{city}" asn:"{asn}"'
                org_facet_url = f"https://www.shodan.io/search/facet?query={quote_plus(org_query)}&facet=org"
                driver.get(org_facet_url)

                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".card.card-padding.u-full-width.facets-card"))
                )

                rows = driver.find_elements(By.CSS_SELECTOR, ".card.card-padding.u-full-width.facets-card")
                orgs_found = 0

                for row in rows:
                    try:
                        org = row.find_element(By.CLASS_NAME, "name").text.strip()
                        noi_raw = row.find_element(By.CLASS_NAME, "value").text.strip()
                        noi = _safe_int(noi_raw)
                        if noi > 10:
                            big_orgs[city][asn].append(org)
                            orgs_found += 1
                    except Exception:
                        continue

                if orgs_found > 0:
                    print(Color.success(f"[{city}/{asn}] Found {orgs_found} orgs"))
            except Exception:
                error_counts["org"] += 1
            finally:
                if driver:
                    driver.quit()

    return big_orgs


# ============================================================================
# IP GRABBING WORKERS (Parallel)
# ============================================================================
def ip_grab_worker(query: str, city: str) -> List[str]:
    """Grab IPs by city"""
    driver = None
    ips = []
    try:
        driver = get_driver()
        ip_url = f"https://www.shodan.io/search/facet?query={quote_plus(query + f' city:\"{city}\"')}&facet=ip"
        driver.get(ip_url)

        WebDriverWait(driver, 25).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".card.card-padding.u-full-width.facets-card"))
        )

        ips = driver.execute_script("""
            return Array.from(document.querySelectorAll('.card.card-padding.u-full-width.facets-card .name a strong'))
                        .map(el => el.innerText.trim())
                        .filter(ip => ip.length > 0);
        """)
    except Exception:
        error_counts["ip_city"] += 1
    finally:
        if driver:
            driver.quit()
    return ips


def ip_grab_worker_by_asn(query: str, city: str, asn: str) -> List[str]:
    """Grab IPs by city + ASN"""
    driver = None
    ips = []
    try:
        driver = get_driver()
        ip_facet = f"https://www.shodan.io/search/facet?query={quote_plus(query + f' city:\"{city}\" asn:\"{asn}\"')}&facet=ip"
        driver.get(ip_facet)

        WebDriverWait(driver, 25).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".card.card-padding.u-full-width.facets-card"))
        )

        ips = driver.execute_script("""
            return Array.from(document.querySelectorAll('.card.card-padding.u-full-width.facets-card .name a strong'))
                        .map(el => el.innerText.trim())
                        .filter(ip => ip.length > 0);
        """)
    except Exception:
        error_counts["ip_asn"] += 1
    finally:
        if driver:
            driver.quit()
    return ips


def ip_grab_worker_by_org(query: str, city: str, asn: str, org: str) -> List[str]:
    """Grab IPs by city + ASN + org"""
    driver = None
    ips = []
    try:
        driver = get_driver()
        ip_facet = f"https://www.shodan.io/search/facet?query={quote_plus(query + f' city:\"{city}\" asn:\"{asn}\" org:\"{org}\"')}&facet=ip"
        driver.get(ip_facet)

        WebDriverWait(driver, 25).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".card.card-padding.u-full-width.facets-card"))
        )

        ips = driver.execute_script("""
            return Array.from(document.querySelectorAll('.card.card-padding.u-full-width.facets-card .name a strong'))
                        .map(el => el.innerText.trim())
                        .filter(ip => ip.length > 0);
        """)
    except Exception:
        error_counts["ip_org"] += 1
    finally:
        if driver:
            driver.quit()
    return ips


# ============================================================================
# HOST RECONNAISSANCE (Recon Mode)
# ============================================================================
def scrape_host_details(ip: str) -> HostData:
    """Scrape detailed host information from Shodan"""
    driver = None
    host_data = HostData(
        ip=ip,
        tags=[],
        general_info={},
        web_technologies=[],
        open_ports=[],
        open_ports_scan=[],
        vulnerabilities=[]
    )

    try:
        driver = get_driver()
        url = f"https://www.shodan.io/host/{ip}"
        driver.get(url)

        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(1)

        scraped = driver.execute_script("""
            let data = {
                tags: [],
                general_info: {},
                web_technologies: [],
                open_ports: [],
                open_ports_scan: [],
                vulnerabilities: []
            };

            document.querySelectorAll('.tag, .tags a, .host-tags .tag').forEach(el => {
                let txt = el.innerText ? el.innerText.trim() : "";
                if (txt && !data.tags.includes(txt)) data.tags.push(txt);
            });

            document.querySelectorAll('.grid-table label').forEach(label => {
                let key = label.innerText.trim();
                let valueDiv = label.nextElementSibling;
                if (key && valueDiv) {
                    let val = valueDiv.innerText.trim().replace(/\\s+/g, ' ');
                    if (val && key.length < 50) data.general_info[key] = val;
                }
            });

            document.querySelectorAll('.technology-name').forEach(el => {
                let tech = el.innerText.trim();
                if (tech && !data.web_technologies.includes(tech)) data.web_technologies.push(tech);
            });

            document.querySelectorAll('#ports a').forEach(el => {
                let match = el.innerText.match(/\\d+/);
                if (match) {
                    let portNum = parseInt(match[0]);
                    if (!data.open_ports.includes(portNum)) data.open_ports.push(portNum);
                }
            });

            document.querySelectorAll('h6.grid-heading').forEach(header => {
                if (!header.querySelector('strong')) return;
                let bannerDiv = header.nextElementSibling;
                if (bannerDiv && bannerDiv.classList.contains('banner')) {
                    let pre = bannerDiv.querySelector('pre');
                    data.open_ports_scan.push({
                        header: header.innerText.trim().replace(/\\s+/g, ' '),
                        banner: pre ? pre.innerText.trim() : ""
                    });
                }
            });

            let seen = new Set();
            document.querySelectorAll('a[href*="CVE-"], [id*="CVE-"]').forEach(el => {
                let text = el.innerText ? el.innerText.trim() : "";
                if (!text) return;
                let idMatch = text.match(/CVE-\\d{4}-\\d+/i);
                if (!idMatch) return;
                let cveId = idMatch[0].toUpperCase();
                if (!seen.has(cveId)) {
                    seen.add(cveId);
                    data.vulnerabilities.push({ cve: cveId, description: text });
                }
            });

            return data;
        """)

        if scraped:
            host_data.tags = scraped.get('tags', [])
            host_data.general_info = scraped.get('general_info', {})
            host_data.web_technologies = scraped.get('web_technologies', [])
            host_data.open_ports = scraped.get('open_ports', [])
            host_data.open_ports_scan = scraped.get('open_ports_scan', [])
            host_data.vulnerabilities = scraped.get('vulnerabilities', [])

    except Exception as e:
        host_data.error = str(e)
        error_counts["recon"] += 1
    finally:
        if driver:
            driver.quit()

    return host_data


def run_recon_mode(ip_file: str, output_file: str, threads: int = 4):
    """Automatic recon mode: load IPs from file and scrape host data"""
    print(Color.highlight(f"\n🔍 AUTO RECON MODE"))

    # Load IPs from file
    if not os.path.isfile(ip_file):
        print(Color.error(f"IP file not found: {ip_file}"))
        return

    with open(ip_file, 'r') as f:
        all_ips = {line.strip() for line in f if line.strip()}

    if not all_ips:
        print(Color.error(f"No IPs found in {ip_file}"))
        return

    print(Color.success(f"Loaded {len(all_ips)} IPs from {ip_file}"))
    print(Color.info(f"Starting host reconnaissance on {len(all_ips)} IPs with {threads} threads..."))

    recon_results = []

    with ThreadPoolExecutor(max_workers=threads) as pool:
        futures = [pool.submit(scrape_host_details, ip) for ip in all_ips]

        with tqdm(total=len(futures), desc="Recon Progress", unit="host") as pbar:
            for future in as_completed(futures):
                try:
                    host_data = future.result()
                    recon_results.append(host_data.to_json())

                    # Show quick summary
                    if host_data.vulnerabilities:
                        tqdm.write(Color.warning(f"{host_data.ip}: {len(host_data.vulnerabilities)} CVEs"))
                    if host_data.open_ports:
                        tqdm.write(Color.info(f"{host_data.ip}: {len(host_data.open_ports)} ports"))
                except Exception:
                    error_counts["recon"] += 1

                pbar.update(1)

    # Save results
    with open(output_file, 'w') as f:
        json.dump(recon_results, f, indent=2)

    print(f"\n{Color.success('Recon Complete!')} Results saved to: {Color.highlight(output_file)}")

    # Summary stats
    vulnerable = sum(1 for r in recon_results if r.get('vulnerabilities'))
    print(Color.info(f"Summary: {vulnerable}/{len(recon_results)} hosts with vulnerabilities"))


# ============================================================================
# MAIN FUNCTION
# ============================================================================
def main():
    parser = argparse.ArgumentParser(
        description="Shodan Facet Scraper & Recon - Modern Edition",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 shodan.py --query="ics" --thread=4
  python3 shodan.py --query="ics" --thread=4 --vpn mullvad-us
  python3 shodan.py --query="ics" --thread=4 --auto-recon
        """
    )

    parser.add_argument("--query", required=False, help="Base search query")
    parser.add_argument("--output", default=None, help="Output file for IPs (default: query_dir/ips.txt)")
    parser.add_argument("--thread", type=int, default=4, help="Worker threads (default=4)")
    parser.add_argument("--recon-mode", action="store_true", help="Scrape host details for each IP")
    parser.add_argument("--auto-recon", action="store_true", help="Auto recon after IP collection")
    parser.add_argument("--vpn", choices=["mullvad", "mullvad-us", "mullvad-uk", "mullvad-de", "mullvad-nl"],
                        help="Use Mullvad VPN (mullvad=auto, mullvad-XX=specific country)")
    parser.add_argument("--target", default=None, help="File with IPs for recon-mode")

    args = parser.parse_args()

    # Handle VPN
    if args.vpn:
        country = args.vpn.replace("mullvad-", "") if args.vpn != "mullvad" else None
        if not MullvadVPN.connect(country):
            print(Color.warning("Continuing without VPN"))

    # Mode: IP Recon from file
    if args.target and args.recon_mode:
        run_recon_mode(args.target, args.target.replace('.txt', '_recon.json'), args.thread)
        return

    # Mode: IP Collection (Hierarchical)
    if not args.query:
        parser.error("Either --query or --target is required")

    dir_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', args.query)
    output_file = args.output or os.path.join(dir_name, "ips.txt")

    print(Color.highlight(f"\n🔍 SHODAN IP COLLECTOR"))
    print(Color.info(f"Query: {args.query} | Output: {output_file} | Threads: {args.thread}"))

    # Fetch cities
    city_list, number_of_ips = fetch_cities(args.query)
    if not city_list:
        print(Color.error("No cities found"))
        return

    # Split by threshold (100 IPs)
    big_cities = []
    small_cities = []
    number_of_ips = [_safe_int(n) for n in number_of_ips]

    for city, count in zip(city_list, number_of_ips):
        if count > 100:
            big_cities.append(city)
        else:
            small_cities.append(city)

    print(Color.success(f"Big cities (>100): {len(big_cities)} | Small cities (≤100): {len(small_cities)}"))

    # Hierarchy: ASNs and Orgs
    big_asn, _ = check_asn(args.query, big_cities) if big_cities else ({}, {})
    organizations = check_org(args.query, big_asn) if big_asn else {}

    # Parallel IP collection
    all_ips: Set[str] = set()
    os.makedirs(dir_name, exist_ok=True)

    with ThreadPoolExecutor(max_workers=args.thread) as pool:
        future_to_info = {}

        # Small cities: direct grab
        for city in small_cities:
            future_to_info[pool.submit(ip_grab_worker, args.query, city)] = ("city", city)

        # Big cities: drill to ASN/org
        for city in big_cities:
            asns = big_asn.get(city, [])
            if asns:
                for asn in asns:
                    future_to_info[pool.submit(ip_grab_worker_by_asn, args.query, city, asn)] = ("asn", city, asn)
                    orgs = organizations.get(city, {}).get(asn, [])
                    for org in orgs:
                        future_to_info[pool.submit(ip_grab_worker_by_org, args.query, city, asn, org)] = ("org", city, asn, org)
            else:
                future_to_info[pool.submit(ip_grab_worker, args.query, city)] = ("city-fallback", city)

        with tqdm(total=len(future_to_info), desc="IP Collection", unit="facet") as pbar:
            for future in as_completed(future_to_info):
                try:
                    ips = future.result() or []
                    all_ips.update(ips)
                except Exception:
                    error_counts["recon"] += 1
                pbar.update(1)

    # Save IPs
    with open(output_file, 'w') as f:
        for ip in sorted(all_ips):
            f.write(f"{ip}\n")

    print(f"\n{Color.success('Collection Complete!')} {len(all_ips)} unique IPs")
    print(Color.info(f"Saved to: {Color.highlight(output_file)}"))

    # Status bar: error counts (silent, no memory addresses, no random output)
    total_errors = sum(error_counts.values())
    if total_errors > 0:
        error_parts = ", ".join(f"{k}:{v}" for k, v in error_counts.items() if v > 0)
        print(Color.info(f"Status: {total_errors} errors ({error_parts})"))
    else:
        print(Color.success("Status: 0 errors"))

    # Auto recon mode
    if args.auto_recon:
        run_recon_mode(output_file, output_file.replace('.txt', '_recon.json'), args.thread)

    # Cleanup VPN
    if args.vpn:
        MullvadVPN.disconnect()


if __name__ == "__main__":
    main()
