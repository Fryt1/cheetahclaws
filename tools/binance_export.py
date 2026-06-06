"""
Export Binance trade history (交割单) to CSV.

Uses Binance signed API — requires API Key + Secret with read permission.
Set env vars: BINANCE_API_KEY, BINANCE_API_SECRET

Usage:
    python cheetahclaws/tools/binance_export.py                    # all symbols, last 90 days
    python cheetahclaws/tools/binance_export.py --symbol BTCUSDT   # single symbol
    python cheetahclaws/tools/binance_export.py --start 2026-01-01 --end 2026-06-04
    python cheetahclaws/tools/binance_export.py --output my_trades.csv
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import hmac
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import urlencode

import requests

BASE_URL = "https://api.binance.com"
MAX_LIMIT = 1000  # Binance max per request


def _now_ms() -> int:
    return int(time.time() * 1000)


def _build_signature(params: dict[str, Any], secret: str) -> str:
    query = urlencode(params, doseq=True)
    return hmac.new(secret.encode("utf-8"), query.encode("utf-8"), hashlib.sha256).hexdigest()


def _signed_get(path: str, params: dict[str, Any], api_key: str, api_secret: str) -> Any:
    signed = dict(params)
    signed["timestamp"] = _now_ms()
    signed["recvWindow"] = 10000
    signed["signature"] = _build_signature(signed, api_secret)

    resp = requests.get(
        f"{BASE_URL}{path}",
        params=signed,
        headers={"X-MBX-APIKEY": api_key},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def get_exchange_info(api_key: str, api_secret: str) -> list[dict]:
    """Fetch all available symbols (no auth needed, but we use it for filtering)."""
    resp = requests.get(f"{BASE_URL}/api/v3/exchangeInfo", timeout=15)
    resp.raise_for_status()
    data = resp.json()
    return [s for s in data.get("symbols", []) if s.get("status") == "TRADING"]


def fetch_my_trades(
    symbol: str,
    api_key: str,
    api_secret: str,
    start_ms: Optional[int] = None,
    end_ms: Optional[int] = None,
) -> list[dict]:
    """Fetch all trades for a symbol, handling pagination via fromId."""
    all_trades: list[dict] = []
    from_id: Optional[int] = None
    params: dict[str, Any] = {"symbol": symbol, "limit": MAX_LIMIT}
    if start_ms:
        params["startTime"] = start_ms
    if end_ms:
        params["endTime"] = end_ms

    while True:
        if from_id is not None:
            params["fromId"] = from_id

        trades = _signed_get("/api/v3/myTrades", params, api_key, api_secret)
        if not isinstance(trades, list):
            print(f"  Unexpected response for {symbol}: {type(trades)}", file=sys.stderr)
            break

        if not trades:
            break

        all_trades.extend(trades)

        if len(trades) < MAX_LIMIT:
            break

        # Use the last trade ID as the starting point for the next page
        from_id = int(trades[-1]["id"])

        # Rate limit guard
        time.sleep(0.15)

    return all_trades


def get_traded_symbols(api_key: str, api_secret: str) -> list[str]:
    """Discover symbols that have trade history by checking all orders."""
    try:
        orders = _signed_get(
            "/api/v3/allOrders",
            {"symbol": "BTCUSDT", "limit": 1},
            api_key,
            api_secret,
        )
        _ = orders  # just test connectivity
    except Exception:
        pass

    # Actually, myTrades is per-symbol. Better approach: try common quote assets.
    # First, let's fetch exchange info and filter for USDT pairs.
    try:
        info = get_exchange_info(api_key, api_secret)
        return sorted(
            [s["symbol"] for s in info if s.get("quoteAsset") == "USDT"],
        )
    except Exception:
        # Fallback: common trading pairs
        return [
            "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
            "ADAUSDT", "DOGEUSDT", "DOTUSDT", "AVAXUSDT", "LINKUSDT",
            "MATICUSDT", "UNIUSDT", "LTCUSDT", "ATOMUSDT", "NEARUSDT",
            "ARBUSDT", "OPUSDT", "APTUSDT", "SUIUSDT", "SEIUSDT",
        ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Export Binance trade history to CSV")
    parser.add_argument("--symbol", "-s", help="Single symbol (e.g. BTCUSDT). Omit for all symbols.")
    parser.add_argument("--start", help="Start date YYYY-MM-DD (default: 90 days ago)")
    parser.add_argument("--end", help="End date YYYY-MM-DD (default: today)")
    parser.add_argument("--output", "-o", default="binance_trades.csv", help="Output CSV file path")
    parser.add_argument("--all-symbols", action="store_true", help="Scan all USDT pairs for trades")
    args = parser.parse_args()

    api_key = os.getenv("BINANCE_API_KEY", "").strip()
    api_secret = os.getenv("BINANCE_API_SECRET", "").strip()

    if not api_key or not api_secret:
        print("错误: 缺少币安 API Key。请设置环境变量:", file=sys.stderr)
        print("  $env:BINANCE_API_KEY='your_api_key'    (PowerShell)", file=sys.stderr)
        print("  $env:BINANCE_API_SECRET='your_secret'  (PowerShell)", file=sys.stderr)
        print(file=sys.stderr)
        print("去币安网站创建只读 API Key: https://www.binance.com/zh-CN/my/settings/api-management", file=sys.stderr)
        sys.exit(1)

    # Date range
    now = datetime.now(timezone.utc)
    end_dt = datetime.fromisoformat(args.end) if args.end else now
    start_dt = (
        datetime.fromisoformat(args.start)
        if args.start
        else datetime.fromtimestamp(now.timestamp() - 90 * 86400)
    )
    start_ms = int(start_dt.timestamp() * 1000)
    end_ms = int(end_dt.timestamp() * 1000)

    print(f"币安交割单导出", file=sys.stderr)
    print(f"  时间范围: {start_dt.strftime('%Y-%m-%d')} ~ {end_dt.strftime('%Y-%m-%d')}", file=sys.stderr)
    print(f"  输出文件: {args.output}", file=sys.stderr)

    if args.symbol:
        symbols = [args.symbol.upper()]
    elif args.all_symbols:
        print("  正在获取交易对列表...", file=sys.stderr)
        symbols = get_traded_symbols(api_key, api_secret)
        print(f"  将扫描 {len(symbols)} 个 USDT 交易对", file=sys.stderr)
    else:
        # Quick mode: only scan common pairs
        symbols = get_traded_symbols(api_key, api_secret)
        print(f"  将扫描 {len(symbols)} 个 USDT 交易对", file=sys.stderr)
        print("  提示: 不需要全部的话可以用 --symbol BTCUSDT 指定单个", file=sys.stderr)

    all_trades: list[dict] = []
    for i, symbol in enumerate(symbols):
        if len(symbols) > 10 and (i + 1) % 50 == 0:
            print(f"  进度: {i + 1}/{len(symbols)}...", file=sys.stderr)
        try:
            trades = fetch_my_trades(symbol, api_key, api_secret, start_ms, end_ms)
            if trades:
                all_trades.extend(trades)
        except Exception as e:
            # Likely no trades for this symbol
            err_msg = str(e)
            if "401" in err_msg or "403" in err_msg:
                print(f"  认证失败: {err_msg}", file=sys.stderr)
                sys.exit(1)
            continue

    if not all_trades:
        print("  未找到任何成交记录", file=sys.stderr)
        sys.exit(0)

    # Sort by time
    all_trades.sort(key=lambda t: t["time"])

    # Write CSV
    fieldnames = [
        "交易时间(UTC)", "交易对", "方向", "价格", "数量", "成交金额",
        "手续费", "手续费币种", "交易ID", "订单ID",
    ]
    with open(args.output, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(fieldnames)
        for t in all_trades:
            trade_time = datetime.fromtimestamp(t["time"] / 1000, tz=timezone.utc)
            side = "买入" if t["isBuyer"] else "卖出"
            price = float(t["price"])
            qty = float(t["qty"])
            quote_qty = float(t["quoteQty"])
            commission = float(t.get("commission", 0) or 0)
            commission_asset = t.get("commissionAsset", "")
            writer.writerow([
                trade_time.strftime("%Y-%m-%d %H:%M:%S"),
                t["symbol"],
                side,
                f"{price:.8f}".rstrip("0").rstrip("."),
                f"{qty:.8f}".rstrip("0").rstrip("."),
                f"{quote_qty:.2f}",
                f"{commission:.8f}".rstrip("0").rstrip("."),
                commission_asset,
                t["id"],
                t["orderId"],
            ])

    total_buy = sum(float(t["quoteQty"]) for t in all_trades if t["isBuyer"])
    total_sell = sum(float(t["quoteQty"]) for t in all_trades if not t["isBuyer"])
    total_commission_usdt = 0.0
    for t in all_trades:
        comm = float(t.get("commission", 0) or 0)
        asset = t.get("commissionAsset", "")
        if asset == "USDT" or asset == "USDC" or asset == "BUSD":
            total_commission_usdt += comm

    print(f"  完成! 共 {len(all_trades)} 笔成交", file=sys.stderr)
    print(f"  总买入: {total_buy:,.2f} USDT  |  总卖出: {total_sell:,.2f} USDT", file=sys.stderr)
    print(f"  手续费: ~{total_commission_usdt:.2f} USDT", file=sys.stderr)
    print(f"  已导出到: {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
