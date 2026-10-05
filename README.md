# lightweight-charts-anywidget

A TradingView [Lightweight Charts](https://github.com/tradingview/lightweight-charts) widget for [marimo](https://marimo.io/) notebooks, built with [anywidget](https://anywidget.dev/).

Made for marimo, and tested only there.

![The interactive playground in the marimo demo notebook: a control panel above a candlestick chart with moving averages, buy/sell markers, volume, and RSI and MACD panes](https://raw.githubusercontent.com/kungfoomanchu/tradingview-anywidget/main/docs/screenshot.png)

## Install

Not on PyPI yet; install from GitHub:

```bash
uv pip install "lightweight-charts-anywidget @ git+https://github.com/kungfoomanchu/tradingview-anywidget"
# optional: technical indicators via pandas-ta
uv pip install pandas-ta
```

## Quick Start

```python
import marimo as mo
from lightweight_charts_anywidget import LightweightChartWidget

W = LightweightChartWidget

# From a pandas/polars DataFrame with OHLCV columns:
chart = mo.ui.anywidget(
    W(
        series_data=[W.candlestick(df), W.volume(df), W.sma(df, period=20)],
        chart_options=W.theme(mo.app_meta().theme),  # follow the notebook's light/dark theme
        height=500,
    )
)
chart
```

Indicators that aren't on the price scale go in their own pane below the chart:

```python
series_data = [W.candlestick(df), W.volume(df), W.pta_rsi(df)] + W.pta_macd(df, pane=2)
```

See [examples/demo.py](examples/demo.py): an interactive playground with every feature on one chart, followed by a reference section explaining each feature with its code.

### Data

All helpers take a pandas or polars DataFrame:

- **Columns** are matched case-insensitively (`Close` or `close`); a missing column raises `KeyError`.
- **Times** come from `time_column=` (default `"date"`), any `time`/`date`/`datetime`/`timestamp` column, or a pandas `DatetimeIndex`.
  Daily data is sent as `"YYYY-MM-DD"`; intraday data as unix seconds, shown in the data's own wall-clock time.
- **Missing values** (NaN, None) are skipped.
- **Extra keyword arguments** are passed through as Lightweight Charts series options, e.g. `W.line(df, color="#f00", title="Close")`.

### Series config

Each helper returns a plain dict you can edit before passing it in `series_data`:

| Key | Meaning |
|-----|---------|
| `type` | `"Candlestick"`, `"Bar"`, `"Line"`, `"Area"`, `"Baseline"` or `"Histogram"` |
| `data` | List of points, e.g. `{"time": "2024-01-15", "value": 1.5}` |
| `options` | Series options (`color`, `title`, `priceScaleId`, ...) |
| `pane` | Pane index: `0` = main price pane (default), `1`+ = panes below it |
| `priceScale` | Options for the series' price scale in its own pane (e.g. `scaleMargins`, `mode`) |
| `markers` | List of `W.marker(...)` dicts |
| `price_lines` | List of `W.price_line(...)` dicts |

### Events

`crosshair_data`, `clicked_data` and `visible_range` are synced back to Python
(`chart.value["crosshair_data"]` in marimo). Crosshair updates are throttled to
10 per second and range updates are sent once scrolling stops.

## Lightweight Charts API Coverage

<!-- COVERAGE-NOTE: When adding new wrapped features, update this section to reflect the change. -->

### Summary

| Category | Wrapped | Available | Coverage |
|----------|---------|-----------|----------|
| Series Types | 6 | 6 | **100%** |
| Chart Methods | ~8 | 15+ | ~50% |
| Series Methods | ~4 | 20+ | ~20% |
| Time Scale | 3 | 15+ | ~20% |
| Price Scale | 3 | 6 | ~50% |
| Pane API | 3 | 15+ | ~20% |
| Events | 3 | 5+ | ~60% |
| Chart Options | 4 groups | 20+ | ~20% |
| Series Options | ~15 | 60+ | ~25% |
| Plugins | 2 | 4+ | ~50% |

**Overall: ~30%** of the lightweight-charts v5 API surface (v5.2).

### What IS wrapped

- **All 6 series types**: Candlestick, Line, Area, Bar, Baseline, Histogram
- **Chart creation**: `createChart()` with width/height/autoSize
- **Dynamic updates**: `applyOptions()` for chart options, series add/remove/setData
- **Panes**: series `pane` index (`addSeries(type, options, paneIndex)`), automatic pane sizing (`setStretchFactor`), per-pane legends
- **Overlays**: Price lines, series markers (`createSeriesMarkers`), text watermark (`createTextWatermark`)
- **Price scales**: per-series `priceScale` options (`mode` for log/percentage/indexed, `scaleMargins`, `invertScale`, `autoScale`) applied to that series' own pane only
- **Events**: Crosshair move, click (with OHLC data), visible time range change (bidirectional)
- **Basic chart options**: Layout (background, textColor), grid (line colors), crosshair mode (Normal/Magnet/Hidden)
- **Series titles**: every helper sets a `title`, shown in the legend
- **Legend**: OHLC / series values with titles and colors, formatted with each series' price formatter
- **Python helpers**: SMA, EMA, volume overlay, dark/light themes (`W.theme()`), pandas/polars DataFrame conversion (daily and intraday)
- **pandas-ta integration** (optional `pip install pandas-ta`):
  - Generic `W.pta(df, "indicator_name")` works with any of 200+ indicators
  - 10 curated helpers with smart defaults: `pta_rsi`, `pta_macd`, `pta_bbands`, `pta_stoch`, `pta_atr`, `pta_adx`, `pta_obv`, `pta_supertrend`, `pta_vwap`, `pta_ichimoku`
  - Auto-detects overlay vs oscillator placement (oscillators get their own pane)
  - Built-in overbought/oversold reference lines (RSI, Stochastic), green/red histogram (MACD), directional coloring (Supertrend)

### What is NOT yet wrapped

**High value (recommended next):**

- **Time scale options** - `rightOffset`, `barSpacing`, `timeVisible`, `secondsVisible`, `borderVisible`, `fixLeftEdge`/`fixRightEdge`, tick formatters
- **More price scale options** - `visible`, `borderVisible`, left price scale helpers
- **More series options** - `visible` (toggle series on/off), `lineStyle` (Solid/Dotted/Dashed), `lineType` (Simple/Steps/Curved), `pointMarkersVisible`, `crosshairMarkerVisible`, `lastPriceAnimation`
- **Series data queries** - `data()`, `dataByIndex()`, `barsInLogicalRange()`
- **Scroll/zoom control** - `scrollToPosition()`, `scrollToRealTime()`, fine-grained `handleScroll`/`handleScale`

**Medium value:**

- **More pane control** - `removePane()`, `swapPanes()`, explicit pane heights (`setHeight()`)
- **Coordinate conversions** - `priceToCoordinate()`, `coordinateToPrice()`, `timeToCoordinate()` (needed for custom overlays)
- **More events** - `dblClick`, `subscribeDataChanged`, `subscribeVisibleLogicalRangeChange`, `subscribeSizeChange`, hovered series (`hoveredItem`, v5.2)
- **Crosshair sub-options** - `vertLine`/`horzLine` colors, width, style, label visibility
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

Features that **cannot** be accessed via passthrough (and require JS changes) include: method calls (`scrollToRealTime()`, coordinate conversions, data queries) and pane methods other than placing series in panes.

## Development

### How the widget uses lightweight-charts

The widget runs TradingView's official **published release** of
[Lightweight Charts™](https://github.com/tradingview/lightweight-charts): `chart.js`
imports it from the esm.sh CDN as `lightweight-charts@5.2`, which serves the newest
5.2.x release. Bug-fix releases therefore reach users automatically; new minor or
major versions need the import updated (see below).

The `lightweight-charts/` folder is a **git submodule with TradingView's source code,
for reference only**: reading the API, debugging and release notes. It is not used at
runtime and is not included in the PyPI package. It tracks TradingView's `master`
branch, so it can contain changes that aren't released yet; the released code is
available inside it as tags (e.g. `git -C lightweight-charts diff v5.2.1 -- src`).

When cloning, pull it in with:

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

If the pull brings in a new TradingView release, `tests/test_lightweight_charts_version.py`
fails until the CDN import in `src/lightweight_charts_anywidget/chart.js` matches it.
To upgrade: change `lightweight-charts@5.x` to the new minor version, read
`lightweight-charts/website/docs/release-notes.md` for API changes, run the tests and
check the demo notebook.

### Run the tests

```bash
uv run --extra dev pytest
```

### Agent skills

This project includes AI agent skills (in `.agents/skills/`, symlinked into `.claude/skills/`) managed by [skills.sh](https://skills.sh):

- `marimo-notebook`, `anywidget-generator` and `wasm-compatibility` from [marimo-team/skills](https://github.com/marimo-team/skills)
- `lightweight-charts` from [tradingview/lightweight-charts](https://github.com/tradingview/lightweight-charts) (v5 API conventions and foot-guns)

The skills are committed, so a fresh clone already has them. To re-download them
from `skills-lock.json` (into `.agents/skills/`):

```bash
npx skills experimental_install
```

**Add them from scratch:**

```bash
npx skills add marimo-team/skills -s marimo-notebook -y
npx skills add marimo-team/skills -s anywidget-generator -y
npx skills add marimo-team/skills -s wasm-compatibility -y
npx skills add tradingview/lightweight-charts -s lightweight-charts -y
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
uv run --extra dev marimo edit examples/demo.py
# or in an isolated sandbox using the script's own dependencies:
uvx marimo edit --sandbox examples/demo.py
```
