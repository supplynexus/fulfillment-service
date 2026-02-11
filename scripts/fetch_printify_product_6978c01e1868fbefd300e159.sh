#!/usr/bin/env bash
# 拉取商品 6978c01e1868fbefd300e159 的完整 JSON 到当前目录
# 用法：PRINTIFY_API_KEY=你的key ./scripts/fetch_printify_product_6978c01e1868fbefd300e159.sh
# 或：export PRINTIFY_API_KEY=你的key && ./scripts/fetch_printify_product_6978c01e1868fbefd300e159.sh

set -e
KEY="${PRINTIFY_API_KEY:?请设置 PRINTIFY_API_KEY}"
OUT="$(cd "$(dirname "$0")" && pwd)/printify_product_6978c01e1868fbefd300e159.json"
curl -s -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  "https://api.printify.com/v1/shops/24981565/products/6978c01e1868fbefd300e159.json" \
  -o "$OUT"
echo "已写入: $OUT"
