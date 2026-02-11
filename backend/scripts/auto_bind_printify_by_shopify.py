#!/usr/bin/env python3
"""
按 Printify raw_data.external.id 与 Shopify 映射，自动绑定「有 Shopify、无 Printify」的核心商品。
与 API 及「自动化管理」中的「Printify–Shopify 商品自动绑定」步骤同源，可直接跑脚本无需 token。

用法（在 backend 目录下）:
  python scripts/auto_bind_printify_by_shopify.py           # 先预览
  python scripts/auto_bind_printify_by_shopify.py --execute # 执行写入
"""

import argparse
import asyncio
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.database import AsyncSessionLocal
from app.services.printify_shopify_binding_service import auto_bind_printify_by_shopify as run_auto_bind


async def run(tenant_id: int, dry_run: bool) -> dict:
    async with AsyncSessionLocal() as db:
        result = await run_auto_bind(db, tenant_id, dry_run=dry_run)
        # 兼容脚本原有输出字段名
        result.setdefault("created", result.get("created_count", 0))
        result.setdefault("skipped", result.get("skipped_already_mapped", 0))
        return result


def main():
    parser = argparse.ArgumentParser(description="Auto-bind Printify by Shopify external.id")
    parser.add_argument("--tenant", type=int, default=1, help="Tenant ID (default: 1 = impeach)")
    parser.add_argument("--execute", action="store_true", help="Execute write; default is dry-run (preview only)")
    args = parser.parse_args()
    dry_run = not args.execute

    print(f"Tenant ID: {args.tenant}, dry_run: {dry_run}")
    result = asyncio.run(run(args.tenant, dry_run))

    if result.get("error"):
        print("Error:", result["error"])
        sys.exit(1)
    print(f"Candidates: {len(result.get('candidates', []))}")
    if result.get("candidates"):
        for i, c in enumerate(result["candidates"][:10], 1):
            print(f"  {i}. core={c['core_product_id']} {c['core_title'][:50]}... -> printify={c['printify_product_id']}")
        if len(result["candidates"]) > 10:
            print(f"  ... and {len(result['candidates']) - 10} more")
    print(f"Created: {result.get('created', 0)}, Skipped: {result.get('skipped', 0)}")
    if not dry_run and result.get("created", 0) > 0:
        print("Done. Product-level mappings added; variant fallback will use SKU/options.")
    sys.exit(0)


if __name__ == "__main__":
    main()
