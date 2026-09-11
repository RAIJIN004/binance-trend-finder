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

def get_intraday_momentum(symbol: str) -> dict | None:
    """Momentum intradía real: cambio 1h y 4h + spike de volumen (velas 15m).
    Filtro principal: detecta lo que se mueve AHORA, no ayer."""
    try:
        ks = get_klines(symbol, "15m", 17)
    except Exception:
        return None
    if len(ks) < 17:
        return None
    closes = [float(k[4]) for k in ks]
    quote_vols = [float(k[5]) * float(k[4]) for k in ks]
    chg_1h = (closes[-1] / closes[-5] - 1) * 100 if closes[-5] > 0 else 0
    chg_4h = (closes[-1] / closes[0] - 1) * 100 if closes[0] > 0 else 0
    base_vol = sum(quote_vols[:-4]) / 13
    spike = (sum(quote_vols[-4:]) / 4) / base_vol if base_vol > 0 else 0
    green_1h = sum(1 for i in range(-4, 0) if closes[i] > closes[i - 1])
    return {
        "chg_1h": round(chg_1h, 2),
        "chg_4h": round(chg_4h, 2),
        "vol_spike": round(spike, 1),
        "green_candles_1h": f"{green_1h}/4",
        "price": closes[-1],
    }

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
    min_1h_pct: float = 1.5,
    min_4h_pct: float = 2.0,
    min_vol_spike: float = 1.0,
    min_24h_pct: float = 0.0,
    only_positive: bool = True,
) -> list:
    """Filtro INTRADIA (reemplaza al ATR diario): solo monedas moviéndose AHORA.
    1 request (15m x17) por moneda. El ATR diario quedó como dato informativo
    en get_coin_analysis, ya no filtra."""
    tickers = get_all_usdt_tickers(min_volume)
    results = []

    for i, t in enumerate(tickers):
        sym = t["symbol"]
        pct_24h = float(t["priceChangePercent"])
        vol = float(t["quoteVolume"])

        if only_positive and pct_24h < min_24h_pct:
            continue

        intra = get_intraday_momentum(sym)
        if intra is None:
            continue

        if only_positive:
            if intra["chg_1h"] < min_1h_pct:
                continue
            if intra["chg_4h"] < min_4h_pct:
                continue
        if intra["vol_spike"] < min_vol_spike:
            continue

        results.append({
            "symbol": sym,
            "price": intra["price"],
            "chg_1h": intra["chg_1h"],
            "chg_4h": intra["chg_4h"],
            "vol_spike": intra["vol_spike"],
            "green_candles_1h": intra["green_candles_1h"],
            "pct_24h": round(pct_24h, 2),
            "volume_24h": round(vol, 0),
        })

        if (i + 1) % 50 == 0:
            time.sleep(0.5)

    # Orden: 1h, spike de volumen, 4h
    results.sort(key=lambda x: (x["chg_1h"], x["vol_spike"], x["chg_4h"]), reverse=True)

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
