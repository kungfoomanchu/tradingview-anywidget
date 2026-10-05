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
- **Missing values** (NaN, None) are skipped, or kept as gaps with `gaps=True` (candlestick, bar, line, area, baseline, histogram).
- **Extra keyword arguments** are passed through as Lightweight Charts series options, in snake_case or camelCase, e.g. `W.line(df, color="#f00", title="Close", line_style="dashed")`.
  Numbered options also take names: `line_style` (`"solid"`, `"dotted"`, `"dashed"`, ...), `line_type` (`"simple"`, `"steps"`, `"curved"`), `last_price_animation`.

### Series config

Each helper returns a plain dict you can edit before passing it in `series_data`:

| Key | Meaning |
|-----|---------|
| `type` | `"Candlestick"`, `"Bar"`, `"Line"`, `"Area"`, `"Baseline"` or `"Histogram"` |
| `data` | List of points, e.g. `{"time": "2024-01-15", "value": 1.5}` |
| `options` | Series options (`color`, `title`, `priceScaleId`, ...) |
| `pane` | Pane index: `0` = main price pane (default), `1`+ = panes below it |
| `priceScale` | Options for the series' price scale in its own pane, e.g. `W.price_scale(mode="log", margins=(0.8, 0))` |
| `markers` | List of `W.marker(...)` dicts |
| `price_lines` | List of `W.price_line(...)` dicts |

### Chart options

`chart_options=` takes any Lightweight Charts chart option as a nested dict. Helpers
build the common ones; `W.merge_options()` deep-merges them with a theme:

```python
chart_options=W.merge_options(
    W.theme("dark"),
    W.time_scale(bar_spacing=10, right_offset=5, fix_left_edge=True),
    W.interaction(mouse_wheel=False),  # leave the mouse wheel to the page
    W.crosshair(mode="magnet_ohlc", style="dotted"),
    W.localization(locale="de-DE", time_formatter=W.date_format(day="2-digit", month="long")),
)
```

A series with `price_scale_id="left"` shows the left price axis automatically.
Intraday data shows the time of day on the time axis automatically.

Formatters are JavaScript functions in Lightweight Charts, so they are described
with [Intl](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Intl)
options instead: `W.number_format(style="currency", currency="EUR")` (per series as
`price_format=`, or chart-wide in `W.localization(price_formatter=...)`) and
`W.date_format(...)` for the crosshair time label and time-axis ticks.

Other widget arguments: `watermark=` takes `{"text": ...}`, `W.image_watermark(path_or_url)`
or a list of them; `pane_heights=[3, 1, 1]` sets relative pane heights;
`sync_group="name"` links the crosshair and scrolling of every chart with that name;
`x_axis="number"` (e.g. option strikes) or `"yield_curve"` (maturities in months)
replaces the time axis.

### Events

`crosshair_data`, `clicked_data`, `double_clicked_data`, `visible_range`,
`logical_range` and `visible_bars` are synced back to Python
(`chart.value["crosshair_data"]` in marimo). Crosshair and click events include
the bar's values, the `price` and bar index (`logical`) under the mouse, the
`pane`, and the series, marker or price line under the mouse (`hovered_series`,
`hovered_type`, `hovered_object_id` = the marker's `id=`). Crosshair updates are
throttled to 10 per second and range updates are sent once scrolling stops.
`W.rows_in_range(df, chart.value["visible_range"])` returns the rows on screen.

### Moving the chart from Python

Keep a reference to the widget and call its methods from any cell, or set its
ranges:

```python
chart = W(series_data=[W.candlestick(df)])
mo.ui.anywidget(chart)

chart.show_all()                  # fit every bar
chart.scroll_to_real_time()       # jump to the latest bar
chart.scroll_to_position(-50)     # latest bar 50 bars past the right edge
chart.logical_range = {"from": len(df) - 50, "to": len(df) - 1}  # last 50 bars
chart.update({"time": "2024-06-03", "open": 1, "high": 2, "low": 1, "close": 2})  # live data
```

`chart.update(point, series=0)` adds a bar or replaces the latest one without
redrawing the chart. `chart.set_crosshair(time)` / `chart.clear_crosshair()` move the
crosshair. `chart.take_screenshot(download="chart.png")` saves a PNG through the
browser and sends it back to Python (`chart.screenshot_png()`);
`chart.save_screenshot(path)` writes it to a file. Click a name in the legend to hide
or show that series.

## Lightweight Charts API Coverage

<!-- COVERAGE-NOTE: When adding new wrapped features, update this section to reflect the change. -->

### Summary

| Category | Wrapped | Available | Coverage |
|----------|---------|-----------|----------|
| Series Types | 6 | 6 | **100%** |
| Chart Methods | ~13 | 15+ | ~85% |
| Series Methods | ~8 | 20+ | ~40% |
| Time Scale | ~11 | 15+ | ~70% |
| Price Scale | 5 | 6 | ~85% |
| Pane API | 4 | 15+ | ~25% |
| Events | 5 | 5+ | ~95% |
| Chart Options | 11 groups | 20+ | ~60% |
| Series Options | ~30 | 60+ | ~50% |
| Plugins | 3 | 4+ | ~75% |

**Overall: ~55%** of the lightweight-charts v5 API surface (v5.2).

### What IS wrapped

- **All 6 series types**: Candlestick, Line, Area, Bar, Baseline, Histogram
- **Chart creation**: `createChart()` with width/height/autoSize, `createOptionsChart()` (`x_axis="number"`) and `createYieldCurveChart()` (`x_axis="yield_curve"`)
- **Screenshots**: `takeScreenshot()` (with the HTML legends drawn in) via `chart.take_screenshot()`, `chart.screenshot_png()`, `chart.save_screenshot()`
- **Synced charts**: crosshair (`setCrosshairPosition()` / `clearCrosshairPosition()`) and visible range shared in the browser between charts with the same `sync_group`; `chart.set_crosshair()` / `chart.clear_crosshair()` from Python
- **Whitespace data**: `gaps=True` keeps missing rows as time-only points (line, area and baseline series also break their line at the gap)
- **Data conflation** (v5.2): `W.time_scale(enable_conflation=True, min_bar_spacing=...)` for very long series
- **Dynamic updates**: `applyOptions()` for chart options, series add/remove/setData
- **Panes**: series `pane` index (`addSeries(type, options, paneIndex)`), pane sizing (`setStretchFactor`, automatic or via `pane_heights`), per-pane legends. Panes follow `series_data`, so removing, adding or reordering panes is done by changing series' `pane` indices rather than `removePane()`/`swapPanes()`.
- **Overlays**: Price lines and series markers (`createSeriesMarkers`), both with optional `id`; text and image watermarks (`createTextWatermark`, `createImageWatermark` via `W.image_watermark()`), several per chart, in any pane
- **Live data**: `series.update()` via `chart.update(point, series=0)`, which also keeps `series_data` in step
- **Price scales**: per-series `priceScale` options (`mode` for log/percentage/indexed, `scaleMargins`, `invertScale`, `autoScale`, `borderVisible`) applied to that series' own pane only, built with `W.price_scale()`; left price scale shown automatically for series with `priceScaleId: "left"`; axis `visible` (chart-wide)
- **Time scale**: `W.time_scale()` for `barSpacing`, `rightOffset`, `minBarSpacing`, `timeVisible`, `secondsVisible`, `fixLeftEdge`/`fixRightEdge`, `visible`, `borderVisible` (and any other option by name); `timeVisible`/`secondsVisible` set automatically for intraday data
- **Scroll/zoom control**: `scrollToRealTime()`, `scrollToPosition()`, `fitContent()` as widget methods (`chart.scroll_to_real_time()`, `chart.scroll_to_position()`, `chart.show_all()`), `setVisibleLogicalRange()` via the bidirectional `logical_range` traitlet, fine-grained `handleScroll`/`handleScale` via `W.interaction()`
- **Series data queries**: `barsInLogicalRange()` of the first series synced as `visible_bars` (first/last visible time, bars before/after); `W.rows_in_range()` filters the DataFrame to the visible range. (`data()`/`dataByIndex()` aren't wrapped: the data is already in Python, in `series_data`.)
- **Series options**: snake_case names and named values for `lineStyle`, `lineType`, `lastPriceAnimation`; `visible` toggled by clicking the legend
- **Events**: Crosshair move, click and double-click (`subscribeDblClick`) with OHLC data, the price under the mouse (`coordinateToPrice()`), bar index (`logical`), pane, and hovered series/marker/price line (`hoveredSeries`, `hoveredObjectId`, `hoveredInfo`, v5.2); visible time range change and visible logical range change (both bidirectional)
- **Crosshair**: `W.crosshair()` for mode (Normal/Magnet/Magnet OHLC/Hidden) and `vertLine`/`horzLine` color, width, style, visibility, labels
- **Localization**: `W.localization()` for `locale`, `dateFormat`, `priceFormatter`, `timeFormatter` and the time scale's `tickMarkFormatter`; formatters (and per-series `priceFormat` `custom` formatters) are built in the browser from `Intl` options given with `W.number_format()` / `W.date_format()`
- **Basic chart options**: Layout (background, textColor), grid (line colors), deep-merged with `W.merge_options()`
- **Series titles**: every helper sets a `title`, shown in the legend
- **Legend**: OHLC / series values with titles and colors, formatted like the price axis
- **Python helpers**: SMA, EMA, volume overlay, dark/light themes (`W.theme()`), pandas/polars DataFrame conversion (daily and intraday)
- **pandas-ta integration** (optional `pip install pandas-ta`):
  - Generic `W.pta(df, "indicator_name")` works with any of 200+ indicators
  - 10 curated helpers with smart defaults: `pta_rsi`, `pta_macd`, `pta_bbands`, `pta_stoch`, `pta_atr`, `pta_adx`, `pta_obv`, `pta_supertrend`, `pta_vwap`, `pta_ichimoku`
  - Auto-detects overlay vs oscillator placement (oscillators get their own pane)
  - Built-in overbought/oversold reference lines (RSI, Stochastic), green/red histogram (MACD), directional coloring (Supertrend)

### What is NOT yet wrapped

**High value (recommended next):**

- **Binary data transfer** - sending long series as binary buffers instead of JSON (250,000 points currently take about a second to convert and send)
- **Up/down markers** - `createUpDownMarkers()` (v5), arrows that flash on price changes, a natural fit for `chart.update()`
- **Pane control from the UI** - syncing pane heights back to Python after the user drags a separator, `preserveEmptyPane`
- **Price scale extras** - `autoscaleInfoProvider` (fixed or padded ranges) via a declarative wrapper, per-pane `ensureEdgeTickMarksVisible`
- **Truly proportional numeric axes** - `createOptionsChart()` spaces points evenly by row; a custom horizontal scale behavior could space them by value

Deliberately not wrapped: `subscribeDataChanged` and `subscribeSizeChange` (the data
and size come from Python, so Python already knows), `data()`/`dataByIndex()` (the
data is in `series_data`), and coordinate conversions other than the price under the
mouse (only useful for drawing custom overlays in JS).

**Lower priority:**

- **Custom series** - `addCustomSeries()` with `ICustomSeriesPaneView` (heatmaps, stacked areas, etc.)
- **Series/pane primitives** - low-level drawing API for custom renderers (drawing tools, trend lines), which would also need `priceToCoordinate()`/`timeToCoordinate()`
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

Features that **cannot** be accessed via passthrough (and require JS changes) include: method calls other than the wrapped ones (e.g. `takeScreenshot()`, `setCrosshairPosition()`), JS function options other than the `Intl`-based formatters and pane methods other than placing series in panes.

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
