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

## Lightweight Charts API Coverage

<!-- COVERAGE-NOTE: When adding new wrapped features, update this section to reflect the change. -->

### Summary

| Category | Wrapped | Available | Coverage |
|----------|---------|-----------|----------|
| Series Types | 6 | 6 | **100%** |
| Chart Methods | ~7 | 15+ | ~40% |
| Series Methods | ~4 | 20+ | ~20% |
| Time Scale | 3 | 15+ | ~20% |
| Price Scale | 1 | 6 | ~17% |
| Pane API | 0 | 15+ | 0% |
| Events | 2 | 5+ | ~40% |
| Chart Options | 4 groups | 20+ | ~20% |
| Series Options | ~15 | 60+ | ~25% |
| Plugins | 2 | 4+ | ~50% |

**Overall: ~20-25%** of the lightweight-charts v5 API surface.

### What IS wrapped

- **All 6 series types**: Candlestick, Line, Area, Bar, Baseline, Histogram
- **Chart creation**: `createChart()` with width/height/autoSize
- **Dynamic updates**: `applyOptions()` for chart options, series add/remove/setData
- **Overlays**: Price lines, series markers (`createSeriesMarkers`), text watermark (`createTextWatermark`)
- **Events**: Crosshair move, click (with OHLC data), visible time range change (bidirectional)
- **Basic chart options**: Layout (background, textColor), grid (line colors), crosshair mode
- **Python helpers**: SMA, EMA, volume overlay, dark/light themes, pandas/polars DataFrame conversion

### What is NOT yet wrapped

**High value (recommended next):**

- **Time scale options** - `rightOffset`, `barSpacing`, `timeVisible`, `secondsVisible`, `borderVisible`, `fixLeftEdge`/`fixRightEdge`, tick formatters
- **Price scale options** - `mode` (Log/Percentage/IndexedTo100), `autoScale`, `invertScale`, `scaleMargins`, `visible`, `borderVisible`
- **More series options** - `title`, `visible` (toggle series on/off), `lineStyle` (Solid/Dotted/Dashed), `lineType` (Simple/Steps/Curved), `pointMarkersVisible`, `crosshairMarkerVisible`, `lastPriceAnimation`
- **Series data queries** - `data()`, `dataByIndex()`, `barsInLogicalRange()`
- **Scroll/zoom control** - `scrollToPosition()`, `scrollToRealTime()`, fine-grained `handleScroll`/`handleScale`

**Medium value:**

- **Multi-pane support** - `addPane()`, `removePane()`, `swapPanes()`, pane sizing (needed for separate indicator panels like RSI)
- **Coordinate conversions** - `priceToCoordinate()`, `coordinateToPrice()`, `timeToCoordinate()` (needed for custom overlays)
- **More events** - `dblClick`, `subscribeDataChanged`, `subscribeVisibleLogicalRangeChange`, `subscribeSizeChange`
- **Crosshair sub-options** - `vertLine`/`horzLine` colors, width, style, label visibility; all mode values (Normal/Magnet/Hidden)
- **Localization** - locale, date/number formatting
- **Image watermarks** - `createImageWatermark()`

**Lower priority:**

- **Custom series** - `addCustomSeries()` with `ICustomSeriesPaneView` (heatmaps, stacked areas, etc.)
- **Series/pane primitives** - low-level drawing API for custom renderers
- **Kinetic scroll** / tracking mode (mobile-specific)
- **Advanced layout** - pane separators, attribution logo, color space

### Passthrough for unlisted options

Many options not explicitly wrapped can still be passed through via `chart_options` and series `options` dicts:

```python
W(chart_options={
    "timeScale": {"rightOffset": 5, "barSpacing": 8, "timeVisible": True},
    "rightPriceScale": {"mode": 1},  # logarithmic
})
```

Features that **cannot** be accessed via passthrough (and require JS changes) include: method calls (`scrollToRealTime()`, coordinate conversions, data queries) and the multi-pane API.

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

### Agent skills

This project includes AI agent skills (in `.agents/skills/` and `.claude/skills/`) managed by [skills.sh](https://skills.sh). These provide coding agents with domain knowledge about marimo notebooks and anywidget development.

**Install skills into a fresh clone:**

```bash
npx skills add marimo-team/skills
```

**Check for updates:**

```bash
npx skills check
```

**Update all skills to latest:**

```bash
npx skills update
```

The `skills-lock.json` file pins skill versions. Commit it after updating so collaborators stay in sync.

### Run the demo notebook

```bash
uv run marimo edit examples/demo.py
```
