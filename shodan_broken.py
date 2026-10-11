import argparse
import sys
import os
import time
import json
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from tqdm import tqdm
import random
from urllib.parse import quote_plus

file_lock = threading.Lock()


# Configurable thresholds


def fetch_cities(query):
    city_list = []
    number_of_ips = []
    try:
        driver = get_driver()
        facet_url = f"https://www.shodan.io/search/facet?query={quote_plus(query)}&facet=city"
        driver.get(facet_url)
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".facets-card")))
        rows = driver.execute_script("return Array.from(document.querySelectorAll('.facets-card .name a')).map(a=>a.innerText.trim()).filter(x=>x);")
        city_list = rows
        vals = driver.execute_script("return Array.from(document.querySelectorAll('.facets-card .value')).map(v=>v.innerText.trim()).filter(x=>x);")
        number_of_ips = vals
        print(f"[+] fetch_cities: {len(city_list)} cities, values={vals[:5]}...")
    except Exception as e:
        print(f"[-] fetch_cities error: {e}")
    finally:
        try: driver.quit()
        except: pass
    return city_list, number_of_ips

def check_asn(query, cities):
    driver = None
    big_asn = {}
    small_asn = {}
    print("[*] Grabbing ASNs (hierarchical)...")
    for city in cities:
        big_asn.setdefault(city, [])
        small_asn.setdefault(city, [])
        try:
            driver = get_driver()
            check_asn_url = f"https://www.shodan.io/search/facet?query={quote_plus(query + f' city:"{city}"')}&facet=asn"
            driver.get(check_asn_url)
            time.sleep(random.uniform(0.5, 1.5))
            WebDriverWait(driver, 15).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".card.card-padding.u-full-width.facets-card"))
            )
            if _check_cloudflare(driver):
                raise Exception("Cloudflare detected during ASN check for " + city)
            # Retry/refresh if no rows loaded (Shodan may truncate for headless)
            if not driver.find_elements(By.CSS_SELECTOR, ".card.card-padding.u-full-width.facets-card"):
                driver.get(check_asn_url)
                time.sleep(random.uniform(1.0, 2.5))
            rows = driver.find_elements(By.CSS_SELECTOR, ".card.card-padding.u-full-width.facets-card")
            asn_found = 0
            for row in rows:
                try:
                    # Try new layout selectors first, fallback to old
                    try:
                        asn = row.find_element(By.CSS_SELECTOR, ".facet-name, .name, h4, .facet-label").text.strip()
                    except:
                        asn = row.find_element(By.CLASS_NAME, "name").text.strip()
                    try:
                        noi_raw = row.find_element(By.CSS_SELECTOR, ".facet-value, .value, span.count, .facet-count").text.strip()
                    except:
                        noi_raw = row.find_element(By.CLASS_NAME, "value").text.strip()
                    noi = _safe_int(noi_raw)
                    if noi >= 100 or noi >= MIN_ASN_COUNT:
                        asn_found += 1
                        big_asn[city].append(asn)
                        # Always continue deeper when big (user directive: country->city->asn->org->scrape)
                        # Small ASNs kept for direct grab when count is lower
                        if noi < CITY_IP_DEEP_THRESHOLD:
                            small_asn[city].append(asn)


def fetch_cities(query):
    city_list = []
    number_of_ips = []
    try:
        driver = get_driver()
        facet_url = f"https://www.shodan.io/search/facet?query={quote_plus(query)}&facet=city"
        driver.get(facet_url)
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".facets-card")))
        rows = driver.execute_script("return Array.from(document.querySelectorAll('.facets-card .name a')).map(a=>a.innerText.trim()).filter(x=>x);")
        city_list = rows
        vals = driver.execute_script("return Array.from(document.querySelectorAll('.facets-card .value')).map(v=>v.innerText.trim()).filter(x=>x);")
        number_of_ips = vals
        print(f"[+] fetch_cities: {len(city_list)} cities, values={vals[:5]}...")
    except Exception as e:
        print(f"[-] fetch_cities error: {e}")
    finally:
        try: driver.quit()
        except: pass
    return city_list, number_of_ips



def check_asn(query, cities):
    driver = None
    big_asn = {}
    small_asn = {}
    print("[*] Grabbing ASNs (hierarchical)...")
    for city in cities:
        big_asn.setdefault(city, [])
        small_asn.setdefault(city, [])
        try:
            driver = get_driver()
            check_asn_url = f"https://www.shodan.io/search/facet?query={quote_plus(query + f' city:"{city}"')}&facet=asn"
            driver.get(check_asn_url)
            time.sleep(random.uniform(0.5, 1.5))
            WebDriverWait(driver, 15).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".card.card-padding.u-full-width.facets-card"))
            )
            if _check_cloudflare(driver):
                raise Exception("Cloudflare detected during ASN check for " + city)
            # Retry/refresh if no rows loaded (Shodan may truncate for headless)
            if not driver.find_elements(By.CSS_SELECTOR, ".card.card-padding.u-full-width.facets-card"):
                driver.get(check_asn_url)
                time.sleep(random.uniform(1.0, 2.5))
            rows = driver.find_elements(By.CSS_SELECTOR, ".card.card-padding.u-full-width.facets-card")
            asn_found = 0
            for row in rows:
                try:
                    # Try new layout selectors first, fallback to old
                    try:
                        asn = row.find_element(By.CSS_SELECTOR, ".facet-name, .name, h4, .facet-label").text.strip()
                    except:
                        asn = row.find_element(By.CLASS_NAME, "name").text.strip()
                    try:
                        noi_raw = row.find_element(By.CSS_SELECTOR, ".facet-value, .value, span.count, .facet-count").text.strip()
                    except:
                        noi_raw = row.find_element(By.CLASS_NAME, "value").text.strip()
                    noi = _safe_int(noi_raw)
                    if noi >= 100 or noi >= MIN_ASN_COUNT:
                        asn_found += 1
                        big_asn[city].append(asn)
                        # Always continue deeper when big (user directive: country->city->asn->org->scrape)
                        # Small ASNs kept for direct grab when count is lower
                        if noi < CITY_IP_DEEP_THRESHOLD:
                            small_asn[city].append(asn)

    opts = webdriver.ChromeOptions()
    opts.add_argument("--headless")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    return webdriver.Chrome(options=opts)

CITY_IP_DEEP_THRESHOLD:
                            small_asn[city].append(asn)
                except Exception:
                    continue
            print(f"    [{city}] ASNs found: {asn_found}, big={len(big_asn[city])}, small={len(small_asn[city])}")
        except Exception as e:
            print(f"[-] ASN check failed for {city}: {e}", file=sys.stderr)
        finally:
            if driver:
                driver.quit()
            time.sleep(15)  # rate limit / wait 15s max between cities
    total_big = sum(len(v) for v in big_asn.values())
    total_small = sum(len(v) for v in small_asn.values())
    print(f"[+] check_asn: big ASNs per city = { {k: len(v) for k,v in big_asn.items()} }, small ASNs per city = { {k: len(v) for k,v in small_asn.items()} }")
    print(f"[+] Total ASNs found: {total_big + total_small} (big={total_big}, small={total_small})")
    if total_big + total_small == 0 and len(cities) > 0:
        print("[-] WARNING: No ASNs found despite cities existing!")
    return big_asn, small_asn



def check_org(query, big_asn):
    driver = None
    big_orgs = {}
    print("[*] Checking big ASNs for organizations (deep drill)...")
    total_expanded = 0
    for city, asn_list in big_asn.items():
        big_orgs.setdefault(city, {})
        for asn in asn_list:
            big_orgs[city].setdefault(asn, [])
            try:
                driver = get_driver()
                org_query = f'{query} city:"{city}" asn:"{asn}"'
                org_facet_url = f"https://www.shodan.io/search/facet?query={quote_plus(org_query)}&facet=org"
                driver.get(org_facet_url)
                time.sleep(random.uniform(0.5, 1.5))
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".card.card-padding.u-full-width.facets-card"))
                )
                if _check_cloudflare(driver):
                    raise Exception("Cloudflare during org check for " + city + "/" + asn)
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
                    total_expanded += 1
                print(f"    [{city}/asn={asn}] orgs expanded={orgs_found}")
            except Exception as e:
                print(f"[-] Org check failed for {city}/{asn}: {e}", file=sys.stderr)
            finally:
                if driver:
                    driver.quit()
    total_orgs = sum(len(v) for city in big_orgs.values() for v in city.values())
    print(f"[+] check_org: {total_orgs} organizations found, expanded ASNs={total_expanded}")
    if total_orgs == 0 and len(big_asn) > 0:
        print("[-] WARNING: Big ASNs exist but no organizations found!")
    return big_orgs



def ip_grab_worker(query, city):
    driver = None
    ips = []
    try:
        driver = get_driver()
        ip_url = f"https://www.shodan.io/search/facet?query={quote_plus(query + f' city:"{city}"')}&facet=ip"
        driver.get(ip_url)
        time.sleep(random.uniform(0.5, 1.5))
        WebDriverWait(driver, 25).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".card.card-padding.u-full-width.facets-card"))
        )
        ips = driver.execute_script("""
            return Array.from(document.querySelectorAll('.card.card-padding.u-full-width.facets-card .name a strong'))
                        .map(el => el.innerText.trim())
                        .filter(ip => ip.length > 0);
        """)
    except Exception as e:
        print(f"[-] IP grab failed for {city}: {e}", file=sys.stderr)
    finally:
        if driver:
            driver.quit()
    return ips




def ip_grab_worker_by_asn(query, city, asn):
    driver = None
    ips = []
    try:
        driver = get_driver()
        ip_facet = f"https://www.shodan.io/search/facet?query={quote_plus(query + f' city:"{city}" asn:"{asn}"')}&facet=ip"
        driver.get(ip_facet)
        time.sleep(random.uniform(0.5, 1.5))
        WebDriverWait(driver, 25).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".card.card-padding.u-full-width.facets-card"))
        )
        ips = driver.execute_script("""
            return Array.from(document.querySelectorAll('.card.card-padding.u-full-width.facets-card .name a strong'))
                        .map(el => el.innerText.trim())
                        .filter(ip => ip.length > 0);
        """)
    except Exception as e:
        print(f"[-] IP grab failed for {city}/asn={asn}: {e}", file=sys.stderr)
    finally:
        if driver:
            driver.quit()
    return ips




def ip_grab_worker_by_org(query, city, asn, org):
    driver = None
    ips = []
    try:
        driver = get_driver()
        ip_facet = f"https://www.shodan.io/search/facet?query={quote_plus(query + f' city:"{city}" asn:"{asn}" org:"{org}"')}&facet=ip"
        driver.get(ip_facet)
        time.sleep(random.uniform(0.5, 1.5))
        WebDriverWait(driver, 25).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".card.card-padding.u-full-width.facets-card"))
        )
        ips = driver.execute_script("""
            return Array.from(document.querySelectorAll('.card.card-padding.u-full-width.facets-card .name a strong'))
                        .map(el => el.innerText.trim())
                        .filter(ip => ip.length > 0);
        """)
    except Exception as e:
        print(f"[-] IP grab failed for {city}/asn={asn}/org={org}: {e}", file=sys.stderr)
    finally:
        if driver:
            driver.quit()
    return ips




def scrape_host_details(ip):
    driver = None
    host_data = {
        "ip": ip,
        "tags": [],
        "general_information": {},
        "web_technologies": [],
        "open_ports": [],
        "open_ports_scan": [],
        "vulnerabilities": []
    }
    try:
        driver = get_driver()
        url = f"https://www.shodan.io/host/{ip}"
        driver.get(url)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(2)
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
                    if (val && key.length < 50) {
                        data.general_info[key] = val;
                    }
                }
            });
            document.querySelectorAll('.technology-name').forEach(el => {
                let tech = el.innerText.trim();
                if (tech && !data.web_technologies.includes(tech)) {
                    data.web_technologies.push(tech);
                }
            });
            document.querySelectorAll('#ports a').forEach(el => {
                let match = el.innerText.match(/\\d+/);
                if (match) {
                    let portNum = parseInt(match[0]);
                    if (!data.open_ports.includes(portNum)) {
                        data.open_ports.push(portNum);
                    }
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
                    data.vulnerabilities.push({
                        cve: cveId,
                        description: text
                    });
                }
            });
            return data;
        """)
        if scraped:
            host_data.update(scraped)
    except Exception as e:
        host_data["error"] = str(e)
    finally:
        if driver:
            driver.quit()
    return host_data




def main():
    parser = argparse.ArgumentParser(description="Shodan Facet Scraper & Recon")
    parser.add_argument("--query", required=False, help="Base search query")
    parser.add_argument("--ip-grab", action="store_true", help="Enable IP extraction and file saving")
    parser.add_argument("--output", default=None, help="Output file name for IP grab")
    parser.add_argument("--thread", type=int, default=5, help="How many threads (default=5)")
    parser.add_argument("--recon-mode", action="store_true", help="Scrape detailed host information for each IP")
    parser.add_argument("--target", default=None, help="File containing a list of IPs (one per line) to run recon-mode on directly, skipping the query/city flow")
    args = parser.parse_args()

    if not args.target and not args.query:
        parser.error("either --query or --target is required")

    if args.target:
        if not os.path.isfile(args.target):
            print(f"[-] Target file not found: {args.target}")
            return
        with open(args.target, "r", encoding="utf-8") as f:
            all_ips = {line.strip() for line in f if line.strip()}
        if not all_ips:
            print(f"[-] No IPs found in target file: {args.target}")
            return
        print(f"[+] Loaded {len(all_ips)} unique IPs from {args.target}")
        print(f"[*] Starting host scan on {len(all_ips)} IPs...")
        recon_results = []
        base_name = os.path.splitext(os.path.basename(args.target))[0]
        json_output_path = f"{base_name}.json"
        with ThreadPoolExecutor(max_workers=args.thread) as pool:
            futures = [pool.submit(scrape_host_details, ip) for ip in all_ips]
            with tqdm(total=len(futures), desc="Scraping Host Recon Pages") as pbar:
                for future in as_completed(futures):
                    data = future.result()
                    recon_results.append(data)
                    pbar.update(1)
        with open(json_output_path, "w", encoding="utf-8") as f:
            json.dump(recon_results, f, indent=4)
        print(f"\n[+] Recon Complete! Results saved to: {json_output_path}")
        return

    dir_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', args.query)
    # Handle --output=. or directory-like output
    if args.output == "." or args.output == "./" or args.output == ".\\":
        args.output = os.path.join(dir_name, "ips.txt")
    elif args.output and os.path.basename(args.output) == "" and args.output.endswith(os.sep):
        args.output = os.path.join(args.output, "ips.txt")
    elif args.output and not args.output.endswith((".txt", ".json")) and not os.path.dirname(args.output) and not os.path.isfile(args.output):
        # User passed something like --output=myfolder; treat as folder + ips.txt
        if not args.output.endswith("/") and not args.output.endswith("\\"):
            args.output = os.path.join(args.output, "ips.txt")
    elif not args.output:
        args.output = os.path.join(dir_name, "ips.txt")

    print(f"[*] Fetching target cities for query: '{args.query}'...")
    city_list, number_of_ips = fetch_cities(args.query)
    if not city_list:
        print("[-] No cities found or failed to load initial facet page.")
        return
    print(f"[+] Found {len(city_list)} cities.")

    # Prefer pagination over facet when query given (bypasses 2-city facet limit)
    if args.query and not args.target:
        paginated = fetch_paginated_ips(args.query, max_pages=3)
        all_ips = set(paginated)
        print(f"[+] SKIPPEDed {len(all_ips)} IPs from 3 pages")
        if args.output and not args.output.endswith(".txt"):
            args.output = os.path.join(dir_name, "ips.txt") if not os.path.dirname(args.output) else args.output
        if args.output:
            with open(args.output, "w") as f:
                for ip in sorted(all_ips): f.write(ip+"\n")
            print(f"[+] Saved paginated IPs to {os.path.abspath(args.output)}")
        if args.recon_mode and all_ips:
            # recon on paginated IPs... (handled below if needed)
            pass
        # Skip facet flow; return after pagination results
        if not args.recon_mode:
            print("[*] Pagination complete. Use --recon-mode to scan these IPs.")
            return


    all_ips = set()
    collect_now = args.ip_grab or args.recon_mode
    if not collect_now and args.query and not args.target:
        print("[*] Note: --ip-grab not set, but a query is given. Collecting IPs by default (add --ip-grab if you want to suppress).")
        collect_now = True
    if collect_now:
        # User explicitly requested IP collection (or recon implies it)
        os.makedirs(dir_name, exist_ok=True)
        print(f"[*] Starting IP collection with {args.thread} threads...")
        number_of_ips = [_safe_int(n) for n in number_of_ips]
        total_reported = sum(number_of_ips)
        print(f"[+] After fetch_cities: total reported results = {total_reported}")
        split = len(number_of_ips)
        for idx, n in enumerate(number_of_ips):
            if n > 1000:
                split = idx
                break

        big_cities = city_list[:split]
        normal_cities = city_list[split:]

        big_asn, small_asn = check_asn(args.query, big_cities)
        organizations = check_org(args.query, big_asn)

        all_ips = set()
        # Hierarchical collection: always start with cities, then ASN, then org if needed
        with ThreadPoolExecutor(max_workers=args.thread) as pool:
            future_to_info = {}

            # 1. Normal / small cities: direct city-level IP grab
            for city in normal_cities:
                future_to_info[pool.submit(ip_grab_worker, args.query, city)] = ("city", city)

            # 2. Small ASNs: grab IPs by ASN directly (no org drill needed if count low)
            for city, asns in small_asn.items():
                for asn in asns:
                    future_to_info[pool.submit(ip_grab_worker_by_asn, args.query, city, asn)] = ("asn", city, asn)

            # 3. Deep drill for big ASNs: try ASN directly first; if it still has too many, drill to org
            for city in big_cities:
                asns = big_asn.get(city, [])
                for asn in asns:
                    # First try direct ASN grab for this big-city ASN
                    future_to_info[pool.submit(ip_grab_worker_by_asn, args.query, city, asn)] = ("asn-deep", city, asn)
                    # If we have orgs for this ASN, also submit org-level grabs
                    orgs = organizations.get(city, {}).get(asn, [])
                    if orgs:
                        for org in orgs:
                            future_to_info[pool.submit(ip_grab_worker_by_org, args.query, city, asn, org)] = ("org", city, asn, org)
                # If this big city produced no ASNs, fall back to direct city grab
                if not asns:
                    future_to_info[pool.submit(ip_grab_worker, args.query, city)] = ("city-fallback", city)

            # 4. Also process any cities present in small_asn that aren't in big_cities / normal_cities
            for city, asns in small_asn.items():
                if city not in big_cities and city not in normal_cities:
                    for asn in asns:
                        future_to_info[pool.submit(ip_grab_worker_by_asn, args.query, city, asn)] = ("asn-small-fallback", city, asn)

            with tqdm(total=len(future_to_info), desc="Collecting IPs hierarchically") as pbar:
                for future in as_completed(future_to_info):
                    info = future_to_info[future]
                    try:
                        city_ips = future.result() or []
                        if len(city_ips) == 0:
                            label = info[1] if len(info) > 1 else str(info)
                            tqdm.write(f"[-] WARNING: Empty IP result from {label}")
                        all_ips.update(city_ips)
                        if isinstance(info, tuple):
                            if info[0] == "org":
                                label = f"{info[1]}/asn={info[2]}/org={info[3]}"
                            elif info[0] == "asn-deep":
                                label = f"{info[1]}/asn={info[2]} (deep)"
                            elif info[0] == "asn":
                                label = f"{info[1]}/asn={info[2]}"
                            elif info[0].startswith("city"):
                                label = f"{info[1]} (city)"
                            else:
                                label = str(info[1:])
                        else:
                            label = str(info)
                        tqdm.write(f"[+] query={args.query} {label} -> {len(city_ips)} IPs (total={len(all_ips)})")
                        pbar.set_postfix(IPs_Found=len(all_ips), target=str(info)[:30])
                    except Exception as e:
                        tqdm.write(f"[-] Worker failed for {info}: {e}")
                    pbar.update(1)

        print(f"\n[+] Total unique IPs collected: {len(all_ips)}")
        if total_reported > 0 and len(all_ips) < 0.3 * total_reported:
            print(f"[-] WARNING: Collected {len(all_ips)} unique IPs, which is much lower than reported total ({total_reported}) — <30%. Possible blocking, partial scraping, or missing deep drills.")
        elif total_reported > 0 and len(all_ips) < 0.4 * total_reported:
            print(f"[-] WARNING: Collected IPs ({len(all_ips)}) are below ~40% of reported total ({total_reported}). Verify no workers failed.")
        if len(all_ips) == 0 and total_reported > 0:
            print("[-] WARNING: Zero IPs collected despite positive reported counts!")
        with open(args.output, "w", encoding="utf-8") as f:
            for ip in sorted(all_ips):
                f.write(f"{ip}\n")
        print(f"[+] Saved IP list to: {os.path.abspath(args.output)}")
    else:
        print("[-] IP collection skipped (--ip-grab / --recon-mode not set). No IP file written.")
        print("[*] To collect IPs, run with --ip-grab (now default when --query is given) or --recon-mode.")

    # Always report where results went
    if collect_now and args.output:
        abs_output = os.path.abspath(args.output)
        print(f"[*] Output file: {abs_output}")
    if args.recon_mode and all_ips:
        recon_json = os.path.join(dir_name, "recon_results.json")
        if os.path.isfile(recon_json):
            print(f"[*] Recon results saved to: {os.path.abspath(recon_json)}")

    # Clear end-of-run summary
    if collect_now:
        if len(all_ips) > 0:
            print(f"\n[+] Completed. Collected {len(all_ips)} unique IPs. File: {os.path.abspath(args.output)}")
        else:
            print(f"\n[-] Completed but collected 0 IPs. File would be: {os.path.abspath(args.output)}")
            print("[-] Possible causes: Cloudflare block, empty facets, or query returned no results.")
    else:
        print("\n[*] City list only (no IP collection). Add --ip-grab / --recon-mode to collect IPs.")

    if args.recon_mode:
        print(f"\n[*] Recon Mode Enabled: Directory '{dir_name}' created.")
        print(f"[*] Starting host scan on {len(all_ips)} IPs...")
        recon_results = []
        json_output_path = os.path.join(dir_name, "recon_results.json")
        with ThreadPoolExecutor(max_workers=args.thread) as pool:
            futures = [pool.submit(scrape_host_details, ip) for ip in all_ips]
            with tqdm(total=len(futures), desc="Gathering hosts infos ") as pbar:
                for future in as_completed(futures):
                    data = future.result()
                    recon_results.append(data)
                    pbar.update(1)
        with open(json_output_path, "w", encoding="utf-8") as f:
            json.dump(recon_results, f, indent=4)
        print(f"\n[+] Recon Complete! Results saved to: {json_output_path}")

