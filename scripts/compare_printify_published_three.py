#!/usr/bin/env python3
"""
拉取店铺 24981565 下三个商品的完整 JSON，并比较「发布」相关字段。
- 6978c01e1868fbefd300e159 已发布
- 698254feac45c6e86a0b90b0 未发布
- 69825421562ab484c806a82c 未发布

用法: PRINTIFY_API_KEY=key python scripts/compare_printify_published_three.py
  或 key 放在 ~/.cursor/mcp.json 的 PRINTIFY_API_KEY
"""
import asyncio
import json
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
scripts_dir = project_root / "scripts"
shop_id = "24981565"
ids = [
    "6978c01e1868fbefd300e159",  # 已发布
    "698254feac45c6e86a0b90b0",  # 未发布
    "69825421562ab484c806a82c",  # 未发布
]


def get_api_key() -> str:
    import os
    key = os.environ.get("PRINTIFY_API_KEY", "").strip()
    if key:
        return key
    mcp_path = Path.home() / ".cursor" / "mcp.json"
    if mcp_path.exists():
        try:
            data = json.loads(mcp_path.read_text(encoding="utf-8"))
            key = (data.get("PRINTIFY_API_KEY") or (data.get("printify") or {}).get("api_key") or "").strip()
            if key:
                return key
        except Exception:
            pass
    raise SystemExit("需要 PRINTIFY_API_KEY 或 ~/.cursor/mcp.json 中的 PRINTIFY_API_KEY")


async def fetch_one(api_key: str, product_id: str) -> dict:
    import httpx
    url = f"https://api.printify.com/v1/shops/{shop_id}/products/{product_id}.json"
    async with httpx.AsyncClient() as client:
        r = await client.get(
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "SupplyNexus/1.0",
            },
            timeout=30.0,
        )
        r.raise_for_status()
        return r.json()


async def main():
    api_key = get_api_key()
    products = {}
    for pid in ids:
        print(f"Fetching {pid} ...", flush=True)
        data = await fetch_one(api_key, pid)
        products[pid] = data
        out = scripts_dir / f"printify_product_{pid}.json"
        out.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  -> {out}")

    # 比较与「发布」相关的字段（只取可能相关的 top-level 键）
    publish_related = ["id", "title", "visible", "is_visible", "sales_channel_properties", "created_at", "updated_at"]
    print("\n" + "=" * 80)
    print("比较（仅 24981565 店铺）与发布相关的字段")
    print("=" * 80)

    for pid in ids:
        p = products[pid]
        print(f"\n--- {pid} ---")
        for k in publish_related:
            if k not in p:
                print(f"  {k}: (不存在)")
                continue
            v = p[k]
            if k == "sales_channel_properties":
                if isinstance(v, list):
                    print(f"  {k}: list, len={len(v)}")
                    for i, item in enumerate(v[:3]):
                        print(f"    [{i}]: {item}")
                    if len(v) > 3:
                        print(f"    ... 共 {len(v)} 项")
                elif isinstance(v, dict):
                    print(f"  {k}: dict, keys={list(v.keys())[:10]}")
                else:
                    print(f"  {k}: {type(v).__name__} = {v}")
            else:
                print(f"  {k}: {v}")

    # 结论：用 sales_channel_properties 是否非空判断
    print("\n" + "=" * 80)
    print("结论（用 sales_channel_properties 判断是否已发布）")
    print("=" * 80)
    for pid in ids:
        scp = products[pid].get("sales_channel_properties")
        if isinstance(scp, list):
            is_pub = len(scp) > 0
        elif isinstance(scp, dict):
            is_pub = bool(scp)
        else:
            is_pub = False
        print(f"  {pid}: sales_channel_properties 非空 = {is_pub} -> {'已发布' if is_pub else '未发布'}")


if __name__ == "__main__":
    asyncio.run(main())
