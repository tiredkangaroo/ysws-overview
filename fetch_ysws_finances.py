#!/usr/bin/env python3
"""
fetch_ysws_finances.py

Reads Approved Projects.json, finds each unique YSWS name, searches for its
HCB organization via hcbscan, then fetches balance data from the HCB API.

Output: ysws_finances.json
  {
    "<ysws_name>": {
      "total_raised": 747.49,
      "total_spent": 691.83
    },
    ...
  }

Usage:
  python fetch_ysws_finances.py
  python fetch_ysws_finances.py --input path/to/Approved\ Projects.json --output out.json
"""

import json
import time
import argparse
import sys
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.parse import quote
from urllib.error import URLError, HTTPError

HCBSCAN_SEARCH = "https://hcbscan.3kh0.net/api/search?q={query}&scope=orgs&limit=10"
HCB_ORG_API    = "https://hcb.hackclub.com/api/v3/organizations/{org_id}.json"
TARGET_CATEGORY = "hack_club_hq"
DELAY_SECONDS   = 0.5   # polite delay between requests


def fetch_json(url: str) -> dict | list | None:
    req = Request(url, headers={"User-Agent": "ysws-finance-fetcher/1.0"})
    try:
        with urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except HTTPError as e:
        print(f"  HTTP {e.code} for {url}", file=sys.stderr)
        return None
    except URLError as e:
        print(f"  URL error for {url}: {e.reason}", file=sys.stderr)
        return None


def find_org_id(ysws_name: str) -> str | None:
    """Search hcbscan for the YSWS and return the first hack_club_hq org id."""
    url = HCBSCAN_SEARCH.format(query=quote(ysws_name))
    data = fetch_json(url)
    if not data or "orgs" not in data:
        return None
    for org in data["orgs"]:
        if org.get("Category") == TARGET_CATEGORY:
            return org.get("Organization ID")
    return None


def fetch_org_finances(org_id: str) -> dict | None:
    """Return (total_raised_dollars, total_spent_dollars) or None."""
    url = HCB_ORG_API.format(org_id=org_id)
    data = fetch_json(url)
    if not data or "balances" not in data:
        return None
    b = data["balances"]
    total_raised_cents  = b.get("total_raised", 0)
    balance_cents       = b.get("balance_cents", 0)
    total_spent_cents   = total_raised_cents - balance_cents
    return {
        "total_raised": round(total_raised_cents / 100, 2),
        "total_spent":  round(total_spent_cents  / 100, 2),
    }


def main():
    parser = argparse.ArgumentParser(description="Fetch HCB finances for each YSWS.")
    parser.add_argument("--input",  default="Approved Projects.json",
                        help="Path to Approved Projects.json")
    parser.add_argument("--output", default="ysws_finances.json",
                        help="Output JSON file path")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    with open(input_path, encoding="utf-8") as f:
        projects = json.load(f)

    # Collect unique YSWS names
    ysws_names: list[str] = []
    seen: set[str] = set()
    for p in projects:
        names = p.get("fields", {}).get("YSWS–Name") or ["Unknown"]
        name = names[0]
        if name not in seen:
            seen.add(name)
            ysws_names.append(name)

    print(f"Found {len(ysws_names)} unique YSWS names.")

    results: dict = {}

    for i, name in enumerate(ysws_names, 1):
        print(f"[{i}/{len(ysws_names)}] {name}")

        org_id = find_org_id(name)
        if not org_id:
            print(f"  No hack_club_hq org found — skipping.")
            results[name] = {"total_raised": None, "total_spent": None}
            time.sleep(DELAY_SECONDS)
            continue

        print(f"  Found org: {org_id}")
        time.sleep(DELAY_SECONDS)

        finances = fetch_org_finances(org_id)
        if not finances:
            print(f"  Failed to fetch finances for {org_id} — skipping.")
            results[name] = {"total_raised": None, "total_spent": None}
        else:
            print(f"  raised=${finances['total_raised']:.2f}  spent=${finances['total_spent']:.2f}")
            results[name] = finances

        time.sleep(DELAY_SECONDS)

    output_path = Path(args.output)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\nDone. Results written to {output_path}")


if __name__ == "__main__":
    main()
