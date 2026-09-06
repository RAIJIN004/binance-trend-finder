import requests
import time
from datetime import datetime

BASE_URL = "https://api.binance.com"

def get_all_usdt_tickers(min_volume: float = 5_000_000) -> list:
    r = requests.get(f"{BASE_URL}/api/v3/ticker/24hr", timeout=15)
    r.raise_for_status()
    data = r.json()
    return [
        d for d in data
        if d["symbol"].endswith("USDT")
        and float(d["quoteVolume"]) > min_volume
        and not any(x in d["symbol"] for x in ["UP", "DOWN", "BULL", "BEAR"])
    ]

def get_klines(symbol: str, interval: str = "1d", limit: int = 14) -> list:
    r = requests.get(
        f"{BASE_URL}/api/v3/klines",
        params={"symbol": symbol, "interval": interval, "limit": limit},
        timeout=15
    )
    r.raise_for_status()
    return r.json()

def calc_daily_changes(klines: list) -> list:
    changes = []
    for k in klines:
        o, c = float(k[1]), float(k[4])
        pct = ((c - o) / o) * 100
        changes.append(round(pct, 2))
    return changes

def calc_atr(klines: list, period: int = 14) -> dict:
    if len(klines) < 2:
        return {"atr": 0, "atr_pct": 0, "tr_values": []}

    tr_values = []
    for i in range(1, len(klines)):
        high = float(klines[i][2])
        low = float(klines[i][3])
        prev_close = float(klines[i-1][4])

        tr1 = high - low
        tr2 = abs(high - prev_close)
        tr3 = abs(low - prev_close)
        tr = max(tr1, tr2, tr3)
        tr_values.append(tr)

    if not tr_values:
        return {"atr": 0, "atr_pct": 0, "tr_values": []}

    atr_period = min(period, len(tr_values))
    atr = sum(tr_values[-atr_period:]) / atr_period

    current_price = float(klines[-1][4])
    atr_pct = (atr / current_price * 100) if current_price > 0 else 0

    return {
        "atr": round(atr, 6),
        "atr_pct": round(atr_pct, 2),
        "tr_values": [round(v, 6) for v in tr_values]
    }

def analyze_bullish_streak(daily_changes: list, klines: list) -> dict:
    if not daily_changes or len(klines) < 2:
        return {
            "positive_streak": 0,
            "positive_days": 0,
            "negative_days": 0,
            "net_change_pct": 0,
            "avg_daily_change": 0,
            "avg_positive_gain": 0
        }

    # Consecutive positive days from newest to oldest
    pos_streak = 0
    for c in reversed(daily_changes):
        if c > 0:
            pos_streak += 1
        else:
            break

    pos_days = sum(1 for c in daily_changes if c > 0)
    neg_days = sum(1 for c in daily_changes if c < 0)

    first_open = float(klines[0][1])
    last_close = float(klines[-1][4])
    net_change = round(((last_close - first_open) / first_open) * 100, 2) if first_open > 0 else 0

    avg_change = round(sum(daily_changes) / len(daily_changes), 2)
    pos_gains = [c for c in daily_changes if c > 0]
    avg_pos_gain = round(sum(pos_gains) / len(pos_gains), 2) if pos_gains else 0

    return {
        "positive_streak": pos_streak,
        "positive_days": pos_days,
        "negative_days": neg_days,
        "net_change_pct": net_change,
        "avg_daily_change": avg_change,
        "avg_positive_gain": avg_pos_gain
    }

def scan_market(
    min_volume: float = 5_000_000,
    top_n: int = 20,
    min_atr_pct: float = 2.0,
    only_positive: bool = True,
    min_positive_days: int = 4,
    min_24h_pct: float = 0.0,
    min_net_7d_pct: float = 0.0,
    interval: str = "1d"
) -> list:
    tickers = get_all_usdt_tickers(min_volume)
    results = []

    for i, t in enumerate(tickers):
        sym = t["symbol"]
        pct_24h = float(t["priceChangePercent"])
        vol = float(t["quoteVolume"])
        high_24h = float(t["highPrice"])
        low_24h = float(t["lowPrice"])
        price = float(t["lastPrice"])

        # Early filter: if user wants positive coins only, 24h must be >= threshold
        if only_positive and pct_24h < min_24h_pct:
            continue

        try:
            klines = get_klines(sym, interval, 14)
            if len(klines) < 8:
                continue

            # Analyze last 7 days + today for streak & net change
            recent_klines = klines[-8:]
            daily = calc_daily_changes(recent_klines)
            streak_info = analyze_bullish_streak(daily, recent_klines)
            atr_data = calc_atr(klines, period=14)

            range_24h = ((high_24h - low_24h) / low_24h) * 100 if low_24h > 0 else 0

            # Filter out flat / low-volatility coins
            if atr_data["atr_pct"] < min_atr_pct:
                continue

            # Bullish / Positive consistency filters
            if only_positive:
                if streak_info["net_change_pct"] < min_net_7d_pct:
                    continue
                if streak_info["positive_days"] < min_positive_days:
                    continue

            results.append({
                "symbol": sym,
                "price": price,
                "pct_24h": round(pct_24h, 2),
                "range_24h": round(range_24h, 2),
                "volume_24h": round(vol, 0),
                "atr": atr_data["atr"],
                "atr_pct": atr_data["atr_pct"],
                "positive_streak": streak_info["positive_streak"],
                "positive_days": f"{streak_info['positive_days']}/{len(daily)}",
                "net_7d_pct": streak_info["net_change_pct"],
                "avg_daily_change": streak_info["avg_daily_change"],
                "avg_positive_gain": streak_info["avg_positive_gain"],
                "daily_changes": daily[-7:]
            })
        except Exception:
            continue

        if (i + 1) % 50 == 0:
            time.sleep(0.5)

    # Sort primarily by:
    # 1. positive streak (consecutive green days)
    # 2. total positive days count
    # 3. net 7-day performance
    # 4. ATR volatility percentage
    if only_positive:
        results.sort(
            key=lambda x: (
                x["positive_streak"],
                int(x["positive_days"].split("/")[0]),
                x["net_7d_pct"],
                x["atr_pct"]
            ),
            reverse=True
        )
    else:
        results.sort(key=lambda x: (x["atr_pct"], x["pct_24h"]), reverse=True)

    return results[:top_n]

def get_ticker_detail(symbol: str) -> dict:
    r = requests.get(f"{BASE_URL}/api/v3/ticker/24hr", params={"symbol": symbol}, timeout=10)
    r.raise_for_status()
    return r.json()

def get_klines_detailed(symbol: str, interval: str = "1d", limit: int = 14) -> list:
    klines = get_klines(symbol, interval, limit)
    result = []
    for k in klines:
        o, h, l, c, v = float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])
        result.append({
            "open": o,
            "high": h,
            "low": l,
            "close": c,
            "volume": v,
            "change_pct": round(((c - o) / o) * 100, 2) if o > 0 else 0
        })
    return result
