# Binance MCP Server

MCP server for scanning Binance markets to detect coins with sustained extensive 24h movements.

## Features

- **Scan Extensive Movements**: Find coins with continuous high volatility streaks over 7 days
- **Coin Analysis**: Detailed analysis of individual coin movements
- **List Active Pairs**: Browse all active USDT trading pairs

## Installation

```bash
pip install binance-mcp-server
```

Or from source:

```bash
git clone https://github.com/jhonv/binance-mcp-server.git
cd binance-mcp-server
pip install -e .
```

## Usage with Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "binance-scanner": {
      "command": "python",
      "args": ["path/to/binance-mcp-server/server.py"]
    }
  }
}
```

## Available Tools

### `scan_extensive_movements`

Scans all Binance USDT pairs and returns coins with sustained extensive movements.

**Parameters:**
- `min_volume` (float, default: 5000000): Minimum 24h volume in USDT
- `top_n` (int, default: 20): Number of top results to return

**Returns:**
- Top coins ranked by movement streak and intensity
- 7-day daily changes for each coin
- Summary with best streak, highest average, and most volatile

### `get_coin_analysis`

Get detailed analysis of a specific coin.

**Parameters:**
- `symbol` (string): Trading pair (e.g., "BTCUSDT")

**Returns:**
- Current price and 24h change
- 7-day kline data
- Trend analysis (BULLISH/BEARISH)

### `list_active_pairs`

List all active USDT trading pairs.

**Parameters:**
- `min_volume` (float, default: 10000000): Minimum volume filter

**Returns:**
- List of pairs with price, change, and volume

## Scoring Algorithm

The scanner ranks coins based on:

1. **Streak**: Consecutive days where movement is within 70% of the weekly average
2. **Days Above Threshold**: Number of days with >3% absolute movement
3. **Weekly Average**: Average absolute daily change over 7 days

## License

MIT
