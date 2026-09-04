from mcp.server.fastmcp import FastMCP
from scanner import scan_market, get_ticker_detail, get_klines_detailed, get_all_usdt_tickers
from datetime import datetime

mcp = FastMCP(
    "binance-trend-finder",
    description="Binance market scanner - detects coins with sustained extensive 24h movements"
)

@mcp.tool()
def scan_extensive_movements(
    min_volume: float = 5_000_000,
    top_n: int = 20
) -> dict:
    """
    Scan Binance USDT pairs and find coins with sustained extensive 24h movements.
    Analyzes 7-day history to find coins with continuous high volatility streaks.
    
    Args:
        min_volume: Minimum 24h quote volume in USDT (default: 5M)
        top_n: Number of top results to return (default: 20)
    
    Returns:
        Dictionary with top coins ranked by movement streak and intensity
    """
    results = scan_market(min_volume=min_volume, top_n=top_n)

    return {
        "scan_time": datetime.utcnow().isoformat(),
        "pairs_scanned": len(results),
        "top_coins": results,
        "summary": {
            "best_streak": results[0] if results else None,
            "highest_avg": max(results, key=lambda x: x["avg_week"]) if results else None,
            "most_volatile_24h": max(results, key=lambda x: x["range_24h"]) if results else None
        }
    }

@mcp.tool()
def get_coin_analysis(symbol: str) -> dict:
    """
    Get detailed analysis of a specific coin's movements.
    
    Args:
        symbol: Trading pair symbol (e.g., 'BTCUSDT', 'ETHUSDT')
    
    Returns:
        Detailed price data and movement analysis
    """
    symbol = symbol.upper()
    if not symbol.endswith("USDT"):
        symbol += "USDT"

    ticker = get_ticker_detail(symbol)
    klines = get_klines_detailed(symbol, "1d", 7)

    daily_changes = [abs(k["change_pct"]) for k in klines]
    avg = sum(daily_changes) / len(daily_changes) if daily_changes else 0

    streak = 0
    for c in reversed(daily_changes):
        if c >= avg * 0.7:
            streak += 1
        else:
            break

    return {
        "symbol": symbol,
        "current_price": float(ticker["lastPrice"]),
        "price_change_24h": float(ticker["priceChangePercent"]),
        "range_24h": round(((float(ticker["highPrice"]) - float(ticker["lowPrice"])) / float(ticker["lowPrice"])) * 100, 2),
        "volume_24h": float(ticker["quoteVolume"]),
        "klines_7d": klines,
        "analysis": {
            "avg_daily_change": round(avg, 2),
            "current_streak": streak,
            "days_above_3pct": sum(1 for c in daily_changes if c >= 3.0),
            "trend": "BULLISH" if sum(k["change_pct"] for k in klines) > 0 else "BEARISH"
        }
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
