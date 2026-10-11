from urllib.parse import quote
import argparse
import random
import requests
from lxml import html
from concurrent.futures import ThreadPoolExecutor, as_completed

# Expanded pool of modern desktop User-Agents
USER_AGENTS = [
    # Chrome
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    # Firefox
    "Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:124.0) Gecko/20100101 Firefox/124.0",
    # Safari
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3.1 Safari/605.1.15",
    # Edge
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
]


def get_random_headers():
    """Generates realistic HTTP headers with a randomly selected User-Agent."""
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }


def load_proxies(proxy_input):
    """Loads a single proxy string or a list of proxies from a .txt file."""
    if not proxy_input:
        return None

    if proxy_input.endswith(".txt"):
        try:
            with open(proxy_input, "r") as f:
                proxies = [line.strip() for line in f if line.strip()]
            print(f"[*] Loaded {len(proxies)} proxies from {proxy_input}")
            return proxies
        except Exception as e:
            print(f"[-] Error reading proxy file: {e}")
            return None

    return [proxy_input]


def get_proxy_dict(proxy_list):
    """Selects a random proxy from the list and formats it for requests."""
    if not proxy_list:
        return None

    proxy_str = random.choice(proxy_list)
    if not proxy_str.startswith(("http://", "https://", "socks5://", "socks4://")):
        proxy_str = f"http://{proxy_str}"

    return {"http": proxy_str, "https": proxy_str}


def ip_grab(query, city, proxies=None):
    ips = []
    encoded_query = quote(f'{query} city:"{city}"')
    url = f"https://www.shodan.io/search/facet?query={encoded_query}&facet=ip"

    proxy_dict = get_proxy_dict(proxies)
    headers = get_random_headers()  # Random UA per request

    try:
        ips_get = requests.get(
            url, headers=headers, proxies=proxy_dict, timeout=10
        )
        if ips_get.status_code != 200:
            return ips

        ips_tree = html.fromstring(ips_get.text)
        ips_city = ips_tree.xpath('//div[contains(@class, "facet-row")]')

        for ip in ips_city:
            names = ip.xpath(
                './/*[contains(@class, "name")]//text() | .//a/text() | .//strong/text()'
            )
            text = "".join(t.strip() for t in names if t.strip())
            if text:
                ips.append(text)
    except Exception:
        pass

    return ips


def main():
    parser = argparse.ArgumentParser(description="Shodan Facet Scraper")
    parser.add_argument("--query", required=True, help="Base search query")
    parser.add_argument(
        "--ip-grab",
        action="store_true",
        help="Enable IP extraction and file saving",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output file name (default: <query>.txt)",
    )
    parser.add_argument(
        "--thread", default=5, type=int, help="How many threads (default=5)"
    )
    parser.add_argument(
        "--proxy",
        default=None,
        help="Proxy address OR path to proxies.txt",
    )
    parser.add_argument(
        "--recon-mode",
        help="check every ip alone and output the results to json file",
    )
    args = parser.parse_args()

    output_file = args.output if args.output else f"{args.query}.txt"
    proxies = load_proxies(args.proxy)

    city_list = []
    ips_final = set()

    # Step 1: Fetch cities for query
    encoded_base = quote(args.query)
    base_proxy = get_proxy_dict(proxies)

    try:
        city_request = requests.get(
            f"https://www.shodan.io/search/facet?query={encoded_base}&facet=city",
            headers=get_random_headers(),
            proxies=base_proxy,
            timeout=10,
        )
        tree = html.fromstring(city_request.text)

        rows = tree.xpath('//div[contains(@class, "facet-row")]')
        for row in rows:
            names = row.xpath(
                './/*[contains(@class, "name")]//text() | .//strong/text()'
            )
            text = "".join(t.strip() for t in names if t.strip())
            if text:
                city_list.append(text)
    except Exception as e:
        print(f"[-] Failed to fetch city list: {e}")
        return

    print(f"[*] Found {len(city_list)} cities...")

    # Step 2: Grab IPs if --ip-grab flag is active
    if args.ip_grab:
        print(
            f"[*] Extracting IPs across {len(city_list)} cities using {args.thread} threads..."
        )
        with ThreadPoolExecutor(max_workers=args.thread) as executor:
            futures = [
                executor.submit(ip_grab, args.query, city, proxies)
                for city in city_list
            ]
            for future in as_completed(futures):
                ips_final.update(future.result())

        with open(output_file, "w") as f:
            for ip in ips_final:
                f.write(f"{ip}\n")

        print(f"[+] Total Unique IPs saved to '{output_file}': {len(ips_final)}")

    # Step 3: Recon mode placeholder
    if args.recon_mode:
        print(f"[*] Recon mode activated for target: {args.recon_mode}")


if __name__ == "__main__":
    main()
