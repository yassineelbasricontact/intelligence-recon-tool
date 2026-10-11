# Shodan Project Setup

Autonomy: accept mode, multi-agent, verify always, open browser.

## CRITICAL: Hierarchy Threshold is 100 IPs at EACH Level (NOT 1000)

**The hierarchy drills down only when a location has >100 IPs. Below 100, scrape directly.**

Hierarchy logic:
1. **Countries** (if applicable): fetch_cities() returns list with counts
   - If country total ≤ 100 IPs: add to variable, scrape directly later
   - If country total > 100 IPs: proceed to cities

2. **Cities**: for each city in city_list
   - If city total ≤ 100 IPs: scrape directly (no ASN check)
   - If city total > 100 IPs: proceed to ASNs

3. **ASNs**: for each ASN in city
   - If ASN total ≤ 100 IPs: scrape directly (no org check)
   - If ASN total > 100 IPs: proceed to orgs

4. **Orgs**: for each org in ASN
   - Scrape IPs directly

**Result:** Small cities like Shenzhen (≤100), Beijing (≤100) skip ASN checks entirely and grab IPs directly. Only big cities (>100) drill into ASNs. Only big ASNs (>100) drill into orgs.

Rate limiting: 15-second sleep BETWEEN EACH CITY.

## Auto-Verify Without User Interaction (mandatory)
- Before and after any change: run verification alone — do not wait for user.
- Run test query: `python3 shodan.py --query="ics" --thread=4`
- Check: small cities grabbed directly (no ASN output), big cities drilled, threshold 100 enforced.
- If test fails: fix code, re-run, verify again — never ask user to confirm.
- Always check output shows: "[+] Big cities (>100 IPs, drill to ASN): N" and "[+] Small cities (≤100 IPs, scrape directly): M"
- Verification is NOT optional; it runs alone every time.

## Pre-task rule
- Before every task: read this file, understand threshold is 100 IPs at EACH level
- Run program with actual Shodan query: `python3 shodan.py --query="ics" --thread=4`
- Verify results: small cities grabbed directly, big cities drilled to ASNs/orgs
- Confirm ≥40% scrape rate (actual IPs vs. reported count)
- After any change: re-run, check results, never stop without verification
- **DO NOT add pagination, DO NOT stop at one level, DO NOT change threshold from 100**
