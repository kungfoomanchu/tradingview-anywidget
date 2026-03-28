# Project Notes for AI Agents

## Updating API Coverage

When wrapping additional lightweight-charts features (new traitlets, JS event handlers, helper methods, etc.), **you must also update the "Lightweight Charts API Coverage" section in README.md**. This includes:

1. Moving items from "NOT yet wrapped" to "IS wrapped"
2. Updating the coverage percentages in the summary table
3. Removing items from the "not wrapped" lists once implemented

Look for the `<!-- COVERAGE-NOTE -->` comment in README.md as a reminder.

## Phase 2: pandas-ta Integration

A future goal is to integrate [pandas-ta](https://github.com/twopirllc/pandas-ta) for technical indicators. This will add helpers like `W.rsi()`, `W.macd()`, `W.bollinger_bands()`, etc. that compute indicators via pandas-ta and return series configs. Multi-pane support (see coverage gaps) will be needed for indicators like RSI that belong on a separate pane.

## Project Structure

- `src/tradingview_anywidget/__init__.py` - Widget class + Python helpers
- `src/tradingview_anywidget/chart.js` - ESM module (imports lightweight-charts v5 from CDN)
- `src/tradingview_anywidget/chart.css` - Minimal light/dark mode styles
- `examples/demo.py` - Marimo notebook showcasing all features
- `lightweight-charts/` - Git submodule (reference only, not a build dependency)
