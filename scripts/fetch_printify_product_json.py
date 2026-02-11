#!/usr/bin/env python3
"""
Fetch a single Printify product as full JSON (for debugging published/visible fields).

Usage:
  python scripts/fetch_printify_product_json.py --product-id 6978c01e1868fbefd300e159 --shop-id 24981565
  python scripts/fetch_printify_product_json.py --product-id 6978c01e1868fbefd300e159 --tenant impeach

API key: --api-key KEY | env PRINTIFY_API_KEY | --token-file path
"""
import asyncio
import argparse
import json
import os
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "backend"))

import httpx


def get_api_key(args) -> str:
    if args.api_key:
        return args.api_key.strip()
    if args.token_file:
        p = Path(args.token_file).expanduser()
        if not p.exists():
            raise FileNotFoundError(f"Token file not found: {p}")
        return p.read_text(encoding="utf-8").strip()
    key = os.environ.get("PRINTIFY_API_KEY", "").strip()
    if key:
        return key
    mcp_path = Path.home() / ".cursor" / "mcp.json"
    if mcp_path.exists():
        try:
            data = json.loads(mcp_path.read_text(encoding="utf-8"))
            key = (data.get("PRINTIFY_API_KEY") or data.get("printify", {}).get("api_key") or "").strip()
            if key:
                return key
        except Exception:
            pass
    raise ValueError("Need --api-key, --token-file, env PRINTIFY_API_KEY, or ~/.cursor/mcp.json with PRINTIFY_API_KEY")


async def get_product(api_key: str, shop_id: str, product_id: str) -> dict | None:
    url = f"https://api.printify.com/v1/shops/{shop_id}/products/{product_id}.json"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "SupplyNexus/1.0",
    }
    async with httpx.AsyncClient() as client:
        r = await client.get(url, headers=headers, timeout=30.0)
        r.raise_for_status()
        return r.json()


async def main():
    parser = argparse.ArgumentParser(description="Fetch one Printify product as JSON")
    parser.add_argument("--product-id", required=True, help="Printify product ID (e.g. 6978c01e1868fbefd300e159)")
    parser.add_argument("--shop-id", default="24981565", help="Printify shop ID (default: 24981565)")
    parser.add_argument("--api-key", help="Printify API key")
    parser.add_argument("--token-file", help="Path to file containing API key")
    parser.add_argument("--tenant", help="Tenant name (not implemented here; use --shop-id)")
    parser.add_argument("--out", help="Output JSON file path (default: printify_product_<id>.json in scripts/)")
    args = parser.parse_args()

    api_key = get_api_key(args)
    if args.tenant and not args.shop_id:
        args.shop_id = "24981565"  # impeach

    data = await get_product(api_key, args.shop_id, args.product_id)
    if not data:
        print("Failed to fetch product")
        return

    out_path = args.out or str(project_root / "scripts" / f"printify_product_{args.product_id}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Full JSON written to: {out_path}")

    # Summary of fields that indicate published state (per Printify API / our usage)
    print("\n--- Published/visibility-related fields ---")
    for key in ("id", "title", "visible", "is_visible", "sales_channel_properties"):
        if key in data:
            val = data[key]
            if key == "sales_channel_properties" and isinstance(val, (list, dict)):
                print(f"  {key}: {type(val).__name__} len={len(val)}  value={val}")
            else:
                print(f"  {key}: {val}")


if __name__ == "__main__":
    asyncio.run(main())
