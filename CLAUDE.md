# Project Notes for AI Agents

## Updating API Coverage

When wrapping additional lightweight-charts features (new traitlets, JS event handlers, helper methods, etc.), **you must also update the "Lightweight Charts API Coverage" section in README.md**. This includes:

1. Moving items from "NOT yet wrapped" to "IS wrapped"
2. Updating the coverage percentages in the summary table
3. Removing items from the "not wrapped" lists once implemented

Look for the `<!-- COVERAGE-NOTE -->` comment in README.md as a reminder.

## Keeping the demo notebook in sync

`examples/demo.py` is the main documentation. It has two parts: an **interactive playground** at the top (code hidden, one chart with every feature behind a control) and a **feature reference** below (one section per feature: a `mo.md` explanation cell, then the visible code). Whenever you add, remove, rename or change the behavior of a feature (helper, parameter, default, series config key, event, chart option handling):

1. **Update the explanation** in the matching reference section's markdown (`mo.md` in a `hide_code=True` cell) so it describes the current behavior, parameters and defaults. Search the demo for the old name/behavior to catch every mention, including the "Getting data in" section and the playground intro.
2. **Add or update the reference example** (visible code) for the feature.
3. **Add a playground control** if the feature can be combined with a price chart; otherwise say in the playground intro why it isn't there.
4. Run `uv run --extra dev pytest` - `tests/test_demo_docs.py` fails if a public `W.*` helper has no example in the demo code or no mention as `W.name(` in its markdown.
5. Check the notebook in a browser (see "Verifying changes"), including a few playground combinations.

The test only checks that helpers are mentioned; keeping the wording accurate (defaults, parameter names, behavior) is on you.

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

`.agents/skills/` holds `marimo-notebook`, `anywidget-generator`, `wasm-compatibility` (marimo-team/skills) and `lightweight-charts` (tradingview/lightweight-charts, the official v5 API skill). Use the lightweight-charts skill before changing `chart.js`.

## Project Structure

- `src/tradingview_anywidget/__init__.py` - Widget class + Python helpers
- `src/tradingview_anywidget/chart.js` - ESM module (imports lightweight-charts v5.2 from CDN; keep in step with the submodule)
- `src/tradingview_anywidget/chart.css` - Minimal styles (legend colors come from the chart theme)
- `tests/test_helpers.py` - pytest tests for the Python helpers
- `tests/test_demo_docs.py` - checks every public helper is shown and explained in the demo
- `examples/demo.py` - Marimo notebook: interactive playground + feature reference (see "Keeping the demo notebook in sync")
- `lightweight-charts/` - Git submodule (reference only, not a build dependency)
