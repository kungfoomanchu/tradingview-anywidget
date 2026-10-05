# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo",
#     "yfinance>=0.2.0",
#     "pandas>=1.5.0",
#     "pandas-ta>=0.3.14b",
#     "tradingview-anywidget",
# ]
#
# [tool.uv.sources]
# tradingview-anywidget = { path = "..", editable = true }
# ///

import marimo

__generated_with = "0.21.1"
app = marimo.App(width="full")


@app.cell
def _():
    import marimo as mo
    import yfinance as yf
    from tradingview_anywidget import LightweightChartWidget

    W = LightweightChartWidget
    return W, mo, yf


@app.cell
def _(mo):
    mo.md("""
    # TradingView Lightweight Charts in marimo

    Every chart below is a `LightweightChartWidget` built from a pandas DataFrame
    with helpers like `W.candlestick(df)` and `W.volume(df)`. Change the ticker,
    period or theme here and every chart updates.
    """)
    return


@app.cell
def _(mo):
    ticker_input = mo.ui.text(value="AAPL", label="Ticker")
    period_dropdown = mo.ui.dropdown(
        options=["1mo", "3mo", "6mo", "1y", "2y", "5y"],
        value="1y",
        label="Period",
    )
    theme_dropdown = mo.ui.dropdown(
        options=["dark", "light"],
        value=mo.app_meta().theme,
        label="Theme",
    )
    mo.hstack([ticker_input, period_dropdown, theme_dropdown], justify="start", gap=1)
    return period_dropdown, theme_dropdown, ticker_input


@app.cell
def _(mo, yf):
    @mo.cache
    def load_prices(ticker, period):
        """Download daily OHLCV data from Yahoo Finance as a flat DataFrame."""
        prices = yf.download(ticker, period=period, auto_adjust=True, progress=False)
        # yfinance returns (field, ticker) MultiIndex columns; keep the field names
        prices.columns = prices.columns.get_level_values(0)
        return prices.reset_index()

    return (load_prices,)


@app.cell
def _(W, load_prices, period_dropdown, theme_dropdown, ticker_input):
    df = load_prices(ticker_input.value.strip().upper(), period_dropdown.value)
    theme = W.theme(theme_dropdown.value)
    return df, theme


@app.cell
def _(mo):
    mo.md("""
    ## 1. Series types

    All six Lightweight Charts series types, with volume overlaid on the bottom
    of the price pane and the ticker as a watermark.
    """)
    return


@app.cell
def _(mo):
    chart_type = mo.ui.dropdown(
        options=["Candlestick", "Bar", "Line", "Area", "Baseline", "Histogram"],
        value="Candlestick",
        label="Chart type",
    )
    show_volume = mo.ui.checkbox(value=True, label="Show volume")
    mo.hstack([chart_type, show_volume], justify="start", gap=1)
    return chart_type, show_volume


@app.cell
def _(W, chart_type, df, mo, show_volume, theme, ticker_input):
    builders = {
        "Candlestick": lambda: W.candlestick(df),
        "Bar": lambda: W.bar(df),
        "Line": lambda: W.line(df),
        "Area": lambda: W.area(df),
        # Green above the period's average price, red below
        "Baseline": lambda: W.baseline(df, base_value=float(df["Close"].mean())),
        "Histogram": lambda: W.histogram(df),
    }
    series_types_chart = mo.ui.anywidget(
        W(
            series_data=[builders[chart_type.value]()] + ([W.volume(df)] if show_volume.value else []),
            chart_options=theme,
            watermark={"text": ticker_input.value.upper(), "color": "rgba(128, 128, 128, 0.15)", "fontSize": 64},
            height=450,
        )
    )
    series_types_chart
    return


@app.cell
def _(mo):
    mo.md("""
    ## 2. Moving averages

    `W.sma()` and `W.ema()` are computed in pure Python, so they need no extra
    dependencies.
    """)
    return


@app.cell
def _(mo):
    sma_period = mo.ui.slider(start=5, stop=100, value=20, step=5, label="SMA period")
    ema_period = mo.ui.slider(start=5, stop=100, value=50, step=5, label="EMA period")
    mo.hstack([sma_period, ema_period], justify="start", gap=2)
    return ema_period, sma_period


@app.cell
def _(W, df, ema_period, mo, sma_period, theme):
    mo.ui.anywidget(
        W(
            series_data=[
                W.candlestick(df),
                W.sma(df, period=sma_period.value),
                W.ema(df, period=ema_period.value),
                W.volume(df),
            ],
            chart_options=theme,
            height=400,
        )
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ## 3. Signals with series markers

    Buy/sell markers where the 10-day SMA crosses the 30-day SMA.
    """)
    return


@app.cell
def _(W, df, mo, theme):
    sma_fast = W.sma(df, period=10, color="#FF6D00")
    sma_slow = W.sma(df, period=30, color="#2196F3")

    slow_by_time = {p["time"]: p["value"] for p in sma_slow["data"]}
    crossings = []
    prev_diff = None
    for point in sma_fast["data"]:
        if point["time"] not in slow_by_time:
            continue
        diff = point["value"] - slow_by_time[point["time"]]
        if prev_diff is not None and prev_diff <= 0 < diff:
            crossings.append(W.marker(point["time"], "belowBar", "arrowUp", "#26a69a", "Buy"))
        elif prev_diff is not None and prev_diff >= 0 > diff:
            crossings.append(W.marker(point["time"], "aboveBar", "arrowDown", "#ef5350", "Sell"))
        prev_diff = diff

    mo.ui.anywidget(
        W(
            series_data=[{**W.candlestick(df), "markers": crossings}, sma_fast, sma_slow],
            chart_options=theme,
            height=400,
        )
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ## 4. Price lines (support / resistance)
    """)
    return


@app.cell
def _(W, df, mo, theme):
    period_high = float(df["High"].max())
    period_low = float(df["Low"].min())

    mo.ui.anywidget(
        W(
            series_data=[
                {
                    **W.candlestick(df),
                    "price_lines": [
                        W.price_line(period_high, color="#26a69a", title="Resistance"),
                        W.price_line(period_low, color="#ef5350", title="Support"),
                        W.price_line((period_high + period_low) / 2, color="#787B86", title="Mid", line_style=1),
                    ],
                },
                W.volume(df),
            ],
            chart_options=theme,
            height=400,
        )
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ## 5. Comparing tickers

    Each ticker as % change since the start of the period.
    """)
    return


@app.cell
def _(mo):
    compare_input = mo.ui.text(value="AAPL, MSFT, GOOGL", label="Tickers (comma-separated)")
    compare_input
    return (compare_input,)


@app.cell
def _(W, compare_input, load_prices, mo, period_dropdown, theme):
    palette = ["#2962FF", "#FF6D00", "#26a69a", "#AB47BC", "#FF5252"]
    compare_tickers = [t.strip().upper() for t in compare_input.value.split(",") if t.strip()]

    compare_series = []
    for i, ticker in enumerate(compare_tickers):
        prices = load_prices(ticker, period_dropdown.value)
        pct_change = prices.assign(pct=(prices["Close"] / prices["Close"].iloc[0] - 1) * 100)
        compare_series.append(
            W.line(pct_change, column="pct", color=palette[i % len(palette)], title=ticker,
                   priceFormat={"type": "percent"})
        )

    mo.ui.anywidget(W(series_data=compare_series, chart_options=theme, height=400))
    return


@app.cell
def _(mo):
    mo.md("""
    ## 6. Chart options

    Anything in the Lightweight Charts `ChartOptions` can be passed through
    `chart_options`.
    """)
    return


@app.cell
def _(mo):
    grid_visible = mo.ui.checkbox(value=True, label="Grid visible")
    crosshair_mode = mo.ui.dropdown(
        options={"Normal": 0, "Magnet": 1, "Hidden": 2},
        value="Normal",
        label="Crosshair mode",
    )
    price_scale_mode = mo.ui.dropdown(
        options={"Normal": 0, "Logarithmic": 1, "Percentage": 2, "Indexed to 100": 3},
        value="Normal",
        label="Price scale",
    )
    mo.hstack([grid_visible, crosshair_mode, price_scale_mode], justify="start", gap=1)
    return crosshair_mode, grid_visible, price_scale_mode


@app.cell
def _(W, crosshair_mode, df, grid_visible, mo, price_scale_mode, theme):
    grid_color = theme["grid"]["vertLines"]["color"] if grid_visible.value else "transparent"
    mo.ui.anywidget(
        W(
            series_data=[W.candlestick(df), W.volume(df)],
            chart_options={
                **theme,
                "grid": {"vertLines": {"color": grid_color}, "horzLines": {"color": grid_color}},
                "crosshair": {"mode": crosshair_mode.value},
                "rightPriceScale": {**theme["rightPriceScale"], "mode": price_scale_mode.value},
            },
            height=400,
        )
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ## 7. Click & crosshair events

    The widget's `crosshair_data`, `clicked_data` and `visible_range` are synced
    back to Python, so other cells can react to them.
    """)
    return


@app.cell
def _(W, df, mo, theme):
    events_chart = mo.ui.anywidget(
        W(series_data=[W.candlestick(df), W.volume(df)], chart_options=theme, height=350)
    )
    events_chart
    return (events_chart,)


@app.cell
def _(events_chart, mo):
    def describe(event, empty_text):
        if not event.get("series_values"):
            return empty_text
        bar = event["series_values"][0]
        return (
            f"`{event['time']}` · O **{bar['open']:.2f}** H **{bar['high']:.2f}** "
            f"L **{bar['low']:.2f}** C **{bar['close']:.2f}**"
        )

    visible = events_chart.value.get("visible_range", {})
    mo.md(
        f"""
        - **Crosshair:** {describe(events_chart.value.get("crosshair_data", {}), "move your mouse over the chart")}
        - **Last click:** {describe(events_chart.value.get("clicked_data", {}), "click on the chart")}
        - **Visible range:** {visible.get("from", "?")} → {visible.get("to", "?")}
        """
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ## 8. Sparklines

    Small, static charts: scrolling and zooming disabled, axes hidden.
    """)
    return


@app.cell
def _(W, df, mo, theme):
    sparkline_options = {
        **theme,
        "handleScroll": False,
        "handleScale": False,
        "rightPriceScale": {"visible": False},
        "timeScale": {"visible": False},
        "grid": {"vertLines": {"visible": False}, "horzLines": {"visible": False}},
        "crosshair": {"mode": 2},
    }
    mo.hstack(
        [
            mo.ui.anywidget(W(series_data=[W.line(df, color="#26a69a")], chart_options=sparkline_options, height=120)),
            mo.ui.anywidget(W(series_data=[W.area(df)], chart_options=sparkline_options, height=120)),
            mo.ui.anywidget(W(series_data=[W.volume(df, priceScaleId="right")], chart_options=sparkline_options, height=120)),
        ],
        widths="equal",
        gap=1,
    )
    return


@app.cell
def _(mo):
    mo.md("""
    # Technical indicators with pandas-ta

    The `pta_` helpers wrap [pandas-ta](https://github.com/twopirllc/pandas-ta)
    (`uv pip install pandas-ta`). Overlays are drawn on the price chart;
    oscillators get their own pane below it.

    ## 9. Overlays
    """)
    return


@app.cell
def _(mo):
    overlay_dropdown = mo.ui.dropdown(
        options=["Bollinger Bands", "Supertrend", "VWAP (monthly)", "Ichimoku Cloud"],
        value="Bollinger Bands",
        label="Overlay",
    )
    overlay_dropdown
    return (overlay_dropdown,)


@app.cell
def _(W, df, mo, overlay_dropdown, theme):
    overlays = {
        "Bollinger Bands": lambda: W.pta_bbands(df),
        "Supertrend": lambda: [W.pta_supertrend(df)],
        "VWAP (monthly)": lambda: [W.pta_vwap(df, anchor="M")],
        "Ichimoku Cloud": lambda: W.pta_ichimoku(df),
    }
    mo.ui.anywidget(
        W(
            series_data=[W.candlestick(df), W.volume(df)] + overlays[overlay_dropdown.value](),
            chart_options=theme,
            height=450,
        )
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ## 10. Oscillators in panes

    Each selected oscillator gets its own pane. Drag the pane separators to
    resize them.
    """)
    return


@app.cell
def _(mo):
    oscillator_select = mo.ui.multiselect(
        options=["RSI", "MACD", "Stochastic", "ATR", "ADX", "OBV"],
        value=["RSI", "MACD"],
        label="Oscillators",
    )
    rsi_length = mo.ui.slider(start=5, stop=50, value=14, label="RSI length")
    mo.hstack([oscillator_select, rsi_length], justify="start", gap=2)
    return oscillator_select, rsi_length


@app.cell
def _(W, df, mo, oscillator_select, rsi_length, theme):
    oscillators = {
        "RSI": lambda pane: [W.pta_rsi(df, length=rsi_length.value, pane=pane)],
        "MACD": lambda pane: W.pta_macd(df, pane=pane),
        "Stochastic": lambda pane: W.pta_stoch(df, pane=pane),
        "ATR": lambda pane: [W.pta_atr(df, pane=pane)],
        "ADX": lambda pane: [W.pta_adx(df, pane=pane)],
        "OBV": lambda pane: [W.pta_obv(df, pane=pane)],
    }
    oscillator_series = [W.candlestick(df), W.volume(df)]
    for pane_index, name in enumerate(oscillator_select.value, start=1):
        oscillator_series += oscillators[name](pane_index)

    mo.ui.anywidget(
        W(
            series_data=oscillator_series,
            chart_options=theme,
            height=350 + 130 * len(oscillator_select.value),
        )
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ## 11. Any pandas-ta indicator

    `W.pta(df, "name", **kwargs)` works with any pandas-ta indicator and decides
    whether it belongs on the price chart or in its own pane.
    """)
    return


@app.cell
def _(mo):
    indicator_options = {
        "Momentum": ["rsi", "macd", "stoch", "stochrsi", "cci", "mfi", "willr", "roc", "ao", "uo", "ppo"],
        "Overlap": ["sma", "ema", "dema", "tema", "wma", "hma", "zlma", "kama", "vwma"],
        "Volatility": ["bbands", "atr", "natr", "kc", "donchian", "true_range"],
        "Trend": ["adx", "aroon", "supertrend", "chop"],
        "Volume": ["obv", "cmf", "ad", "efi", "pvt"],
    }
    category_dropdown = mo.ui.dropdown(
        options=list(indicator_options),
        value="Momentum",
        label="Category",
    )
    category_dropdown
    return category_dropdown, indicator_options


@app.cell
def _(category_dropdown, indicator_options, mo):
    indicator_dropdown = mo.ui.dropdown(
        options=indicator_options[category_dropdown.value],
        value=indicator_options[category_dropdown.value][0],
        label="Indicator",
    )
    indicator_dropdown
    return (indicator_dropdown,)


@app.cell
def _(W, df, indicator_dropdown, mo, theme):
    mo.ui.anywidget(
        W(
            series_data=[W.candlestick(df), W.volume(df)] + W.pta(df, indicator_dropdown.value),
            chart_options=theme,
            height=500,
        )
    )
    return


if __name__ == "__main__":
    app.run()
