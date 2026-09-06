# Binance Trend Finder (MCP Server)

MCP server for scanning Binance markets to detect coins with **sustained positive upward momentum**, continuous green streaks, and high ATR volatility (filtering out misleading bleeding/dumping coins).

## Key Improvements

- **Filtro de Momentum Positivo (`only_positive=True`)**: Descarta monedas engañosas que caen continuamente. Solo selecciona activos en tendencia alcista genuina.
- **Racha Verde (`positive_streak`)**: Cuenta días consecutivos cerrando en verde hasta el día de hoy.
- **Filtro de Consistencia (`positive_days >= 4/8`)**: Exige mayoría de velas alcistas en la semana y ganancia neta semanal positiva (`net_7d_pct > 0`).
- **Filtro de Volatilidad Real (`min_atr_pct >= 2.0%`)**: Evita monedas planas o monedas estables (como PAXG o stablecoins), asegurando rango operable.

## Installation

```bash
pip install -e .
```

Or install dependencies directly:

```bash
pip install mcp requests
```

## Usage with Claude Desktop / OpenCode / Hermes

### OpenCode (`opencode.json`):
```json
{
  "mcp": {
    "binance-trend-finder": {
      "type": "local",
      "command": [
        "C:\\Python313\\python.exe",
        "C:\\Users\\jhonv\\Downloads\\binance-mcp-server\\server.py"
      ],
      "timeout": 120,
      "enabled": true
    }
  }
}
```

### Hermes Agent (`config.yaml`):
```yaml
mcp_servers:
  binance-trend-finder:
    command: C:\Python313\python.exe
    args:
      - C:\Users\jhonv\Downloads\binance-mcp-server\server.py
    connect_timeout: 60
    enabled: true
```

## Available MCP Tools

### `scan_extensive_movements`
Scans all Binance USDT pairs for sustained bullish momentum.

**Parameters:**
- `only_positive` (bool, default: `True`): Solo devuelve monedas con racha positiva y rendimiento neto semanal positivo.
- `min_positive_days` (int, default: `4`): Mínimo de días verdes en los últimos 8 días.
- `min_atr_pct` (float, default: `2.0`): Filtro de ATR % para descartar monedas sin rango ni volatilidad.
- `min_24h_pct` (float, default: `0.0`): Cambio mínimo positivo en las últimas 24h.
- `min_net_7d_pct` (float, default: `0.0`): Rendimiento neto mínimo en 7 días.
- `min_volume` (float, default: `5000000`): Volumen mínimo 24h en USDT.
- `top_n` (int, default: `20`): Número de resultados a retornar.

### `get_coin_analysis`
Detailed analysis of a specific symbol (`BTCUSDT`, `NEARUSDT`, etc.) including green streaks, net 7d gain, ATR %, and trend verdict.

### `list_active_pairs`
Quick overview of active USDT pairs filtered by volume.

## License

MIT
