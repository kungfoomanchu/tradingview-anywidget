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
- Oscillators auto-detect separate price scale placement
- Single-series helpers return `dict`, multi-series return `list[dict]`
- Polars users must call `.to_pandas()` first (pandas-ta requires pandas)

When adding new curated `pta_*` helpers, follow the existing pattern and update the README coverage section.

## Project Structure

- `src/tradingview_anywidget/__init__.py` - Widget class + Python helpers
- `src/tradingview_anywidget/chart.js` - ESM module (imports lightweight-charts v5 from CDN)
- `src/tradingview_anywidget/chart.css` - Minimal light/dark mode styles
- `examples/demo.py` - Marimo notebook showcasing all features
- `lightweight-charts/` - Git submodule (reference only, not a build dependency)
