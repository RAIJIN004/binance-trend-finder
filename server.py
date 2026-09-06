from mcp.server.fastmcp import FastMCP
from scanner import (
    scan_market,
    get_ticker_detail,
    get_klines_detailed,
    get_all_usdt_tickers,
    calc_atr,
    calc_daily_changes,
    analyze_bullish_streak
)
from datetime import datetime

mcp = FastMCP(
    "binance-trend-finder",
    description="Binance market scanner - detects coins with sustained positive upward momentum and high ATR"
)

@mcp.tool()
def scan_extensive_movements(
    min_volume: float = 5_000_000,
    top_n: int = 20,
    min_atr_pct: float = 2.0,
    only_positive: bool = True,
    min_positive_days: int = 4,
    min_24h_pct: float = 0.0,
    min_net_7d_pct: float = 0.0,
    interval: str = "1d"
) -> dict:
    """
    Scan Binance USDT pairs and find coins with sustained extensive movements.
    Filters for consistent positive/bullish momentum (avoids falling/bleeding coins).
    
    Args:
        min_volume: Minimum 24h quote volume in USDT (default: 5M)
        top_n: Number of top results to return (default: 20)
        min_atr_pct: Minimum ATR percentage to filter out flat/low-volatility coins (default: 2.0)
        only_positive: If True, only returns coins in a sustained uptrend (green days, net positive 7d) (default: True)
        min_positive_days: Minimum positive/green days in the last 8 days (default: 4)
        min_24h_pct: Minimum 24h price change percentage (default: 0.0)
        min_net_7d_pct: Minimum net 7-day price gain percentage (default: 0.0)
        interval: Kline interval (default: '1d')
    
    Returns:
        Dictionary with top bullish coins ranked by positive streak, net 7d gain, and ATR
    """
    results = scan_market(
        min_volume=min_volume,
        top_n=top_n,
        min_atr_pct=min_atr_pct,
        only_positive=only_positive,
        min_positive_days=min_positive_days,
        min_24h_pct=min_24h_pct,
        min_net_7d_pct=min_net_7d_pct,
        interval=interval
    )

    return {
        "scan_time": datetime.utcnow().isoformat(),
        "filters_applied": {
            "only_positive": only_positive,
            "min_volume": min_volume,
            "min_atr_pct": min_atr_pct,
            "min_positive_days": min_positive_days,
            "min_24h_pct": min_24h_pct,
            "min_net_7d_pct": min_net_7d_pct,
            "interval": interval
        },
        "pairs_matched": len(results),
        "top_coins": results,
        "summary": {
            "top_momentum_coin": results[0] if results else None,
            "highest_7d_gain": max(results, key=lambda x: x["net_7d_pct"]) if results else None,
            "highest_atr": max(results, key=lambda x: x["atr_pct"]) if results else None
        }
    }

@mcp.tool()
def get_coin_analysis(symbol: str) -> dict:
    """
    Get detailed analysis of a specific coin's bullish momentum, ATR and streaks.
    
    Args:
        symbol: Trading pair symbol (e.g., 'BTCUSDT', 'NEARUSDT')
    
    Returns:
        Detailed price data, daily green/red streaks, net 7d gain, and ATR
    """
    symbol = symbol.upper()
    if not symbol.endswith("USDT"):
        symbol += "USDT"

    ticker = get_ticker_detail(symbol)
    klines_raw = get_klines_detailed(symbol, "1d", 14)
    klines_data = [[0, k["open"], k["high"], k["low"], k["close"]] for k in klines_raw]

    atr_info = calc_atr(klines_data, period=14)
    daily_changes = [k["change_pct"] for k in klines_raw[-8:]]
    streak_info = analyze_bullish_streak(daily_changes, klines_data[-8:])

    trend = "STRONG_BULLISH" if (streak_info["positive_streak"] >= 3 and streak_info["net_change_pct"] > 15) else (
        "BULLISH" if streak_info["net_change_pct"] > 0 else "BEARISH"
    )

    return {
        "symbol": symbol,
        "current_price": float(ticker["lastPrice"]),
        "price_change_24h": float(ticker["priceChangePercent"]),
        "range_24h": round(((float(ticker["highPrice"]) - float(ticker["lowPrice"])) / float(ticker["lowPrice"])) * 100, 2),
        "volume_24h": float(ticker["quoteVolume"]),
        "atr": atr_info["atr"],
        "atr_pct": atr_info["atr_pct"],
        "momentum": {
            "trend": trend,
            "positive_streak_days": streak_info["positive_streak"],
            "green_days": f"{streak_info['positive_days']}/{len(daily_changes)}",
            "net_7d_pct": streak_info["net_change_pct"],
            "avg_daily_change": streak_info["avg_daily_change"],
            "avg_positive_gain": streak_info["avg_positive_gain"]
        },
        "recent_daily_candles": klines_raw[-7:]
    }

@mcp.tool()
def list_active_pairs(min_volume: float = 10_000_000) -> dict:
    """
    List all active USDT trading pairs on Binance with volume filter.
    
    Args:
        min_volume: Minimum 24h quote volume in USDT (default: 10M)
    
    Returns:
        List of active trading pairs with basic info
    """
    tickers = get_all_usdt_tickers(min_volume)

    pairs = []
    for t in tickers:
        pairs.append({
            "symbol": t["symbol"],
            "price": float(t["lastPrice"]),
            "change_24h": float(t["priceChangePercent"]),
            "volume_24h": float(t["quoteVolume"]),
            "high_24h": float(t["highPrice"]),
            "low_24h": float(t["lowPrice"])
        })

    pairs.sort(key=lambda x: x["volume_24h"], reverse=True)

    return {
        "total_pairs": len(pairs),
        "min_volume_filter": min_volume,
        "pairs": pairs
    }

if __name__ == "__main__":
    mcp.run()
