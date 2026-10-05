# Project Notes for AI Agents

## Updating API Coverage

When wrapping additional lightweight-charts features (new traitlets, JS event handlers, helper methods, etc.), **you must also update the "Lightweight Charts API Coverage" section in README.md**. This includes:

1. Moving items from "NOT yet wrapped" to "IS wrapped"
2. Updating the coverage percentages in the summary table
3. Removing items from the "not wrapped" lists once implemented

Look for the `<!-- COVERAGE-NOTE -->` comment in README.md as a reminder.

## pandas-ta Integration (Implemented)

pandas-ta is now integrated as an optional dependency (`pip install pandas-ta`). All TA methods are prefixed with `pta_` (e.g., `W.pta_rsi()`, `W.pta_macd()`). A generic `W.pta(df, "indicator_name")` method works with any of the 200+ pandas-ta indicators.

- 10 curated helpers: `pta_rsi`, `pta_macd`, `pta_bbands`, `pta_stoch`, `pta_atr`, `pta_adx`, `pta_obv`, `pta_supertrend`, `pta_vwap`, `pta_ichimoku`
- Oscillators go in their own pane (`"pane": 1` in the series config, overridable with `pane=`); overlays stay on pane 0
- Single-series helpers return `dict`, multi-series return `list[dict]`
- Polars DataFrames are converted to pandas internally (without pyarrow)

When adding new curated `pta_*` helpers, follow the existing pattern (`_pta_input` → `_pta_points` → `_series`) and update the README coverage section.

## Data conventions

All DataFrame handling goes through `_time_values`, `_column_values`, `_line_points` and `_ohlc_points` in `__init__.py` - use them rather than reading columns directly.

- Columns are matched case-insensitively; missing columns raise `KeyError`.
- A whole time column gets one format: `"YYYY-MM-DD"` if every value is midnight, otherwise unix seconds (wall-clock, timezone dropped). Lightweight Charts requires one time format per series and unique ascending times.
- Missing values are dropped, never sent as `null`.

## Verifying changes

- `uv run --extra dev pytest` - helper tests (synthetic data, no network)
- `uvx marimo check examples/demo.py` - notebook lint
- JS changes can only be verified in a browser: `uv run --extra dev marimo run examples/demo.py` and check the console.

## Agent skills

`.agents/skills/` holds `marimo-notebook`, `anywidget-generator` (marimo-team/skills) and `lightweight-charts` (tradingview/lightweight-charts, the official v5 API skill). Use the lightweight-charts skill before changing `chart.js`.

## Project Structure

- `src/tradingview_anywidget/__init__.py` - Widget class + Python helpers
- `src/tradingview_anywidget/chart.js` - ESM module (imports lightweight-charts v5.2 from CDN; keep in step with the submodule)
- `src/tradingview_anywidget/chart.css` - Minimal styles (legend colors come from the chart theme)
- `tests/test_helpers.py` - pytest tests for the Python helpers
- `examples/demo.py` - Marimo notebook showcasing all features
- `lightweight-charts/` - Git submodule (reference only, not a build dependency)
