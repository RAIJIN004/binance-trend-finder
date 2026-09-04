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

def get_klines(symbol: str, interval: str = "1d", limit: int = 7) -> list:
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

def score_streak(changes: list, min_pct: float = 3.0) -> dict:
    if len(changes) < 2:
        return {"avg": 0, "streak": 0, "consecutive_big": 0, "positive_days": 0}

    abs_changes = [abs(c) for c in changes]
    avg = sum(abs_changes) / len(abs_changes)

    streak = 0
    for c in reversed(abs_changes):
        if c >= avg * 0.7:
            streak += 1
        else:
            break

    consecutive_big = sum(1 for c in abs_changes if c >= min_pct)
    positive_days = sum(1 for c in changes if c > 0)

    return {
        "avg": round(avg, 2),
        "streak": streak,
        "consecutive_big": consecutive_big,
        "positive_days": positive_days
    }

def scan_market(min_volume: float = 5_000_000, top_n: int = 20) -> list:
    tickers = get_all_usdt_tickers(min_volume)
    results = []
    total = len(tickers)

    for i, t in enumerate(tickers):
        sym = t["symbol"]
        pct_24h = float(t["priceChangePercent"])
        vol = float(t["quoteVolume"])
        high_24h = float(t["highPrice"])
        low_24h = float(t["lowPrice"])
        price = float(t["lastPrice"])

        try:
            klines = get_klines(sym, "1d", 7)
            daily = calc_daily_changes(klines)
            score = score_streak(daily)

            range_24h = ((high_24h - low_24h) / low_24h) * 100

            results.append({
                "symbol": sym,
                "price": price,
                "pct_24h": round(pct_24h, 2),
                "range_24h": round(range_24h, 2),
                "volume_24h": round(vol, 0),
                "avg_week": score["avg"],
                "streak": score["streak"],
                "days_above_threshold": score["consecutive_big"],
                "positive_days": score["positive_days"],
                "daily_changes": daily
            })
        except Exception as e:
            continue

        if (i + 1) % 50 == 0:
            time.sleep(0.5)

    results.sort(key=lambda x: (x["streak"], x["days_above_threshold"], x["avg_week"]), reverse=True)
    return results[:top_n]

def get_ticker_detail(symbol: str) -> dict:
    r = requests.get(f"{BASE_URL}/api/v3/ticker/24hr", params={"symbol": symbol}, timeout=10)
    r.raise_for_status()
    return r.json()

def get_klines_detailed(symbol: str, interval: str = "1d", limit: int = 7) -> list:
    klines = get_klines(symbol, interval, limit)
    result = []
    for k in klines:
        result.append({
            "open": float(k[1]),
            "high": float(k[2]),
            "low": float(k[3]),
            "close": float(k[4]),
            "volume": float(k[5]),
            "change_pct": round(((float(k[4]) - float(k[1])) / float(k[1])) * 100, 2)
        })
    return result
