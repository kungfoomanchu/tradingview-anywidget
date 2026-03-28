# tradingview-anywidget

A TradingView [Lightweight Charts](https://github.com/tradingview/lightweight-charts) widget for [marimo](https://marimo.io/) notebooks, built with [anywidget](https://anywidget.dev/).

## Install

```bash
uv pip install tradingview-anywidget
```

## Quick Start

```python
import marimo as mo
from tradingview_anywidget import LightweightChartWidget

W = LightweightChartWidget

# From a pandas/polars DataFrame with OHLCV columns:
chart = mo.ui.anywidget(
    W(
        series_data=[W.candlestick(df), W.volume(df)],
        chart_options=W.dark_theme(),
        height=500,
    )
)
chart
```

See [examples/demo.py](examples/demo.py) for a full interactive demo.

## Development

### Clone with submodule

The [lightweight-charts](https://github.com/tradingview/lightweight-charts) source is included as a git submodule for reference. When cloning, pull it in with:

```bash
git clone --recurse-submodules <repo-url>

# Or if already cloned:
git submodule update --init
```

### Update lightweight-charts to latest

```bash
cd lightweight-charts
git checkout master
git pull
cd ..
git add lightweight-charts
git commit -m "Update lightweight-charts submodule"
```

### Run the demo notebook

```bash
uv run marimo edit examples/demo.py
```
