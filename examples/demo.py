# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "marimo",
#     "anywidget>=0.9.0",
#     "traitlets>=5.0.0",
#     "yfinance>=0.2.0",
#     "pandas>=1.5.0",
#     "pandas-ta>=0.3.14b",
#     "tradingview-anywidget",
# ]
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
    ## 1. Interactive Chart with Controls
    """)
    return


@app.cell
def _(mo):
    ticker_input = mo.ui.text(value="AAPL", label="Ticker")
    period_dropdown = mo.ui.dropdown(
        options=["1mo", "3mo", "6mo", "1y", "2y", "5y"],
        value="6mo",
        label="Period",
    )
    chart_type = mo.ui.dropdown(
        options=["Candlestick", "Line", "Area", "Bar", "Baseline", "Histogram"],
        value="Candlestick",
        label="Chart type",
    )
    theme_toggle = mo.ui.dropdown(
        options=["Dark", "Light"],
        value="Dark",
        label="Theme",
    )
    show_volume = mo.ui.checkbox(value=True, label="Show volume")
    controls = mo.hstack(
        [ticker_input, period_dropdown, chart_type, theme_toggle, show_volume],
        justify="start",
        gap=1,
    )
    controls
    return chart_type, period_dropdown, show_volume, theme_toggle, ticker_input


@app.cell
def _(period_dropdown, ticker_input, yf):
    df = yf.download(ticker_input.value, period=period_dropdown.value)
    # Flatten MultiIndex columns from yfinance
    if hasattr(df.columns, "levels") and len(df.columns.names) > 1:
        df.columns = df.columns.get_level_values(0)
    df = df.reset_index()
    return (df,)


@app.cell
def _(W, chart_type, df, mo, show_volume, theme_toggle):
    type_name = chart_type.value
    if type_name == "Candlestick":
        main_series = W.candlestick(df)
    elif type_name == "Line":
        main_series = W.line(df, column="Close")
    elif type_name == "Area":
        main_series = W.area(df, column="Close")
    elif type_name == "Bar":
        main_series = W.bar(df)
    elif type_name == "Baseline":
        mid = (df["High"].mean() + df["Low"].mean()) / 2
        main_series = W.baseline(df, column="Close", base_value=float(mid))
    else:
        main_series = W.histogram(df, column="Close")

    series = [main_series]
    if show_volume.value:
        series.append(W.volume(df))

    theme = W.dark_theme() if theme_toggle.value == "Dark" else W.light_theme()

    chart1 = mo.ui.anywidget(
        W(series_data=series, chart_options=theme, height=450)
    )
    chart1
    return


@app.cell
def _(mo):
    mo.md("""
    ## 2. Moving Average Overlays (SMA & EMA)
    """)
    return


@app.cell
def _(mo):
    sma_period = mo.ui.slider(start=5, stop=100, value=20, step=5, label="SMA period")
    ema_period = mo.ui.slider(start=5, stop=100, value=12, step=1, label="EMA period")
    show_sma = mo.ui.checkbox(value=True, label="Show SMA")
    show_ema = mo.ui.checkbox(value=True, label="Show EMA")
    ma_controls = mo.hstack(
        [show_sma, sma_period, show_ema, ema_period], justify="start", gap=1
    )
    ma_controls
    return ema_period, show_ema, show_sma, sma_period


@app.cell
def _(W, df, ema_period, mo, show_ema, show_sma, sma_period):
    ma_series = [W.candlestick(df)]
    if show_sma.value:
        ma_series.append(
            W.sma(df, period=sma_period.value, color="#FF6D00")
        )
    if show_ema.value:
        ma_series.append(
            W.ema(df, period=ema_period.value, color="#2196F3")
        )
    ma_series.append(W.volume(df))

    chart2 = mo.ui.anywidget(
        W(series_data=ma_series, chart_options=W.dark_theme(), height=400)
    )
    chart2
    return


@app.cell
def _(mo):
    mo.md("""
    ## 3. Series Markers (Buy/Sell Signals)
    """)
    return


@app.cell
def _(W, df, mo):
    # Simple golden cross / death cross demo:
    # Mark where short SMA crosses above/below long SMA
    sma_short_data = W.sma(df, period=10)["data"]
    sma_long_data = W.sma(df, period=30)["data"]

    # Build lookup by time
    long_by_time = {d["time"]: d["value"] for d in sma_long_data}

    markers_list = []
    prev_diff = None
    for d in sma_short_data:
        t = d["time"]
        if t not in long_by_time:
            continue
        diff = d["value"] - long_by_time[t]
        if prev_diff is not None:
            if prev_diff <= 0 < diff:
                markers_list.append(
                    W.markers(t, position="belowBar", shape="arrowUp", color="#26a69a", text="Buy")
                )
            elif prev_diff >= 0 > diff:
                markers_list.append(
                    W.markers(t, position="aboveBar", shape="arrowDown", color="#ef5350", text="Sell")
                )
        prev_diff = diff

    candle = W.candlestick(df)
    candle["markers"] = markers_list

    chart3 = mo.ui.anywidget(
        W(
            series_data=[
                candle,
                W.sma(df, period=10, color="#FF6D00"),
                W.sma(df, period=30, color="#2196F3"),
                W.volume(df),
            ],
            chart_options=W.dark_theme(),
            height=400,
        )
    )
    chart3
    return


@app.cell
def _(mo):
    mo.md("""
    ## 4. Price Lines (Support / Resistance)
    """)
    return


@app.cell
def _(W, df, mo):
    high_val = float(df["High"].max())
    low_val = float(df["Low"].min())
    mid_val = (high_val + low_val) / 2

    candle_pl = W.candlestick(df)
    candle_pl["price_lines"] = [
        W.price_line(high_val, color="#26a69a", title="Resistance", line_style=2),
        W.price_line(low_val, color="#ef5350", title="Support", line_style=2),
        W.price_line(mid_val, color="#787B86", title="Mid", line_style=1, line_width=1),
    ]

    chart4 = mo.ui.anywidget(
        W(
            series_data=[candle_pl, W.volume(df)],
            chart_options=W.dark_theme(),
            height=400,
        )
    )
    chart4
    return


@app.cell
def _(mo):
    mo.md("""
    ## 5. Text Watermark
    """)
    return


@app.cell
def _(W, df, mo, ticker_input):
    chart5 = mo.ui.anywidget(
        W(
            series_data=[W.area(df, column="Close")],
            chart_options=W.dark_theme(),
            watermark={
                "text": ticker_input.value,
                "color": "rgba(171, 71, 188, 0.15)",
                "fontSize": 64,
                "fontStyle": "bold",
            },
            height=350,
        )
    )
    chart5
    return


@app.cell
def _(mo):
    mo.md("""
    ## 6. Multi-Series Comparison
    """)
    return


@app.cell
def _(mo):
    compare_input = mo.ui.text(
        value="AAPL,MSFT,GOOGL",
        label="Tickers (comma-separated)",
    )
    compare_input
    return (compare_input,)


@app.cell
def _(compare_input, yf):
    compare_tickers = [t.strip().upper() for t in compare_input.value.split(",") if t.strip()]
    compare_dfs = {}
    for _ticker in compare_tickers:
        _df = yf.download(_ticker, period="6mo")
        if hasattr(_df.columns, "levels") and len(_df.columns.names) > 1:
            _df.columns = _df.columns.get_level_values(0)
        compare_dfs[_ticker] = _df.reset_index()
    return compare_dfs, compare_tickers


@app.cell
def _(W, compare_dfs, compare_tickers, mo):
    # Normalize all to percentage change from first day
    colors = ["#2962FF", "#FF6D00", "#26a69a", "#AB47BC", "#FF5252"]
    compare_series = []
    for i, _ticker in enumerate(compare_tickers):
        _df = compare_dfs[_ticker]
        if _df.empty:
            continue
        first_close = float(_df["Close"].iloc[0])
        _df = _df.copy()
        _df["pct"] = (_df["Close"] / first_close - 1) * 100
        color = colors[i % len(colors)]
        _series = W.line(_df, column="pct", color=color, lineWidth=2)
        compare_series.append(_series)

    chart6 = mo.ui.anywidget(
        W(
            series_data=compare_series,
            chart_options={
                **W.dark_theme(),
                "rightPriceScale": {"mode": 0},
            },
            watermark={
                "text": " vs ".join(compare_tickers),
                "color": "rgba(255,255,255,0.06)",
                "fontSize": 36,
            },
            height=400,
        )
    )
    chart6
    return


@app.cell
def _(mo):
    mo.md("""
    ## 7. Baseline Chart (above/below reference)
    """)
    return


@app.cell
def _(W, df, mo):
    avg_price = float((df["High"].mean() + df["Low"].mean()) / 2)
    chart7 = mo.ui.anywidget(
        W(
            series_data=[W.baseline(df, column="Close", base_value=avg_price)],
            chart_options=W.dark_theme(),
            height=350,
        )
    )
    chart7
    return


@app.cell
def _(mo):
    mo.md("""
    ## 8. Custom Chart Options
    """)
    return


@app.cell
def _(mo):
    grid_visible = mo.ui.checkbox(value=True, label="Grid visible")
    crosshair_mode = mo.ui.dropdown(
        options={"Normal": 0, "Magnet": 1},
        value="Normal",
        label="Crosshair mode",
    )
    price_scale_mode = mo.ui.dropdown(
        options={"Normal": 0, "Logarithmic": 1, "Percentage": 2, "Indexed to 100": 3},
        value="Normal",
        label="Price scale",
    )
    opt_controls = mo.hstack(
        [grid_visible, crosshair_mode, price_scale_mode], justify="start", gap=1
    )
    opt_controls
    return crosshair_mode, grid_visible, price_scale_mode


@app.cell
def _(W, crosshair_mode, df, grid_visible, mo, price_scale_mode):
    grid_color = "rgba(42, 46, 57, 0.5)" if grid_visible.value else "transparent"
    custom_opts = {
        **W.dark_theme(),
        "grid": {
            "vertLines": {"color": grid_color},
            "horzLines": {"color": grid_color},
        },
        "crosshair": {"mode": crosshair_mode.value},
        "rightPriceScale": {"mode": price_scale_mode.value},
    }

    chart8 = mo.ui.anywidget(
        W(
            series_data=[W.candlestick(df), W.volume(df)],
            chart_options=custom_opts,
            height=400,
        )
    )
    chart8
    return


@app.cell
def _(mo):
    mo.md("""
    ## 9. Click & Crosshair Events
    """)
    return


@app.cell
def _(W, df, mo):
    chart9 = mo.ui.anywidget(
        W(
            series_data=[W.candlestick(df), W.volume(df)],
            chart_options=W.dark_theme(),
            height=350,
        )
    )
    chart9
    return (chart9,)


@app.cell
def _(chart9, mo):
    crosshair = chart9.value.get("crosshair_data", {})
    clicked = chart9.value.get("clicked_data", {})

    crosshair_text = "Move your mouse over the chart"
    if crosshair.get("series_values"):
        vals = crosshair["series_values"][0]
        if "close" in vals:
            crosshair_text = f"**Time:** {crosshair['time']} | **O:** {vals['open']:.2f} **H:** {vals['high']:.2f} **L:** {vals['low']:.2f} **C:** {vals['close']:.2f}"
        elif "value" in vals:
            crosshair_text = f"**Time:** {crosshair['time']} | **Value:** {vals['value']:.2f}"

    clicked_text = "Click on the chart to see data"
    if clicked.get("series_values"):
        vals = clicked["series_values"][0]
        if "close" in vals:
            clicked_text = f"**Clicked:** {clicked['time']} | **O:** {vals['open']:.2f} **H:** {vals['high']:.2f} **L:** {vals['low']:.2f} **C:** {vals['close']:.2f}"

    mo.vstack([
        mo.md(f"**Crosshair:** {crosshair_text}"),
        mo.md(f"**Last click:** {clicked_text}"),
    ])
    return


@app.cell
def _(mo):
    mo.md("""
    ## 10. Side-by-Side Charts (Different Heights)
    """)
    return


@app.cell
def _(W, df, mo):
    small_line = mo.ui.anywidget(
        W(
            series_data=[W.line(df, column="Close", color="#26a69a")],
            chart_options={**W.dark_theme(), "handleScroll": False, "handleScale": False},
            height=150,
        )
    )
    small_area = mo.ui.anywidget(
        W(
            series_data=[W.area(df, column="Close")],
            chart_options={**W.dark_theme(), "handleScroll": False, "handleScale": False},
            height=150,
        )
    )
    small_hist = mo.ui.anywidget(
        W(
            series_data=[W.volume(df)],
            chart_options={**W.dark_theme(), "handleScroll": False, "handleScale": False},
            height=150,
        )
    )
    mo.hstack([small_line, small_area, small_hist], widths="equal", gap=0.5)
    return


# =====================================================================
# pandas-ta Technical Indicators
# =====================================================================


@app.cell
def _(mo):
    mo.md("""
    # pandas-ta Technical Indicators

    The `pta_` methods integrate [pandas-ta](https://github.com/twopirllc/pandas-ta)
    for 200+ technical analysis indicators. Install with `pip install pandas-ta`.
    """)
    return


@app.cell
def _(mo):
    mo.md("""
    ## 11. RSI (Relative Strength Index)
    """)
    return


@app.cell
def _(mo):
    rsi_length = mo.ui.slider(start=5, stop=50, value=14, step=1, label="RSI length")
    rsi_length
    return (rsi_length,)


@app.cell
def _(W, df, mo, rsi_length):
    chart_rsi = mo.ui.anywidget(
        W(
            series_data=[W.candlestick(df), W.volume(df), W.pta_rsi(df, length=rsi_length.value)],
            chart_options=W.dark_theme(),
            height=500,
        )
    )
    chart_rsi
    return


@app.cell
def _(mo):
    mo.md("""
    ## 12. MACD (Moving Average Convergence Divergence)
    """)
    return


@app.cell
def _(W, df, mo):
    chart_macd = mo.ui.anywidget(
        W(
            series_data=[W.candlestick(df), W.volume(df)] + W.pta_macd(df),
            chart_options=W.dark_theme(),
            height=500,
        )
    )
    chart_macd
    return


@app.cell
def _(mo):
    mo.md("""
    ## 13. Bollinger Bands
    """)
    return


@app.cell
def _(mo):
    bb_length = mo.ui.slider(start=10, stop=50, value=20, step=1, label="BB length")
    bb_std = mo.ui.slider(start=1.0, stop=3.0, value=2.0, step=0.5, label="BB std dev")
    mo.hstack([bb_length, bb_std], justify="start", gap=1)
    return bb_length, bb_std


@app.cell
def _(W, bb_length, bb_std, df, mo):
    chart_bb = mo.ui.anywidget(
        W(
            series_data=[W.candlestick(df), W.volume(df)] + W.pta_bbands(df, length=bb_length.value, std=bb_std.value),
            chart_options=W.dark_theme(),
            height=450,
        )
    )
    chart_bb
    return


@app.cell
def _(mo):
    mo.md("""
    ## 14. Stochastic Oscillator
    """)
    return


@app.cell
def _(W, df, mo):
    chart_stoch = mo.ui.anywidget(
        W(
            series_data=[W.candlestick(df), W.volume(df)] + W.pta_stoch(df),
            chart_options=W.dark_theme(),
            height=500,
        )
    )
    chart_stoch
    return


@app.cell
def _(mo):
    mo.md("""
    ## 15. Supertrend Overlay
    """)
    return


@app.cell
def _(W, df, mo):
    chart_st = mo.ui.anywidget(
        W(
            series_data=[W.candlestick(df), W.volume(df), W.pta_supertrend(df)],
            chart_options=W.dark_theme(),
            height=450,
        )
    )
    chart_st
    return


@app.cell
def _(mo):
    mo.md("""
    ## 16. ATR, ADX & OBV
    """)
    return


@app.cell
def _(mo):
    sub_indicator = mo.ui.dropdown(
        options=["ATR", "ADX", "OBV"],
        value="ATR",
        label="Indicator",
    )
    sub_indicator
    return (sub_indicator,)


@app.cell
def _(W, df, mo, sub_indicator):
    if sub_indicator.value == "ATR":
        ind_series = W.pta_atr(df)
    elif sub_indicator.value == "ADX":
        ind_series = W.pta_adx(df)
    else:
        ind_series = W.pta_obv(df)

    chart_sub = mo.ui.anywidget(
        W(
            series_data=[W.candlestick(df), W.volume(df), ind_series],
            chart_options=W.dark_theme(),
            height=500,
        )
    )
    chart_sub
    return


@app.cell
def _(mo):
    mo.md("""
    ## 17. VWAP (Volume Weighted Average Price)
    """)
    return


@app.cell
def _(W, df, mo):
    chart_vwap = mo.ui.anywidget(
        W(
            series_data=[W.candlestick(df), W.volume(df), W.pta_vwap(df)],
            chart_options=W.dark_theme(),
            height=450,
        )
    )
    chart_vwap
    return


@app.cell
def _(mo):
    mo.md("""
    ## 18. Ichimoku Cloud
    """)
    return


@app.cell
def _(W, df, mo):
    chart_ich = mo.ui.anywidget(
        W(
            series_data=[W.candlestick(df)] + W.pta_ichimoku(df),
            chart_options=W.dark_theme(),
            height=500,
        )
    )
    chart_ich
    return


@app.cell
def _(mo):
    mo.md("""
    ## 19. Generic `W.pta()` - Any pandas-ta Indicator

    Use the dropdown to pick any indicator category, then select a specific
    indicator. This uses the generic `W.pta(df, indicator_name, **kwargs)` method.
    """)
    return


@app.cell
def _(mo):
    indicator_options = {
        "Momentum": ["rsi", "macd", "stoch", "stochrsi", "cci", "mfi", "willr", "roc", "ao", "uo", "ppo"],
        "Overlap": ["sma", "ema", "dema", "tema", "wma", "hma", "zlma", "kama", "vwma"],
        "Volatility": ["bbands", "atr", "natr", "kc", "donchian", "true_range"],
        "Trend": ["adx", "aroon", "supertrend", "chop"],
        "Volume": ["obv", "cmf", "ad", "efi", "mfi", "pvt"],
    }
    category_dd = mo.ui.dropdown(
        options=list(indicator_options.keys()),
        value="Momentum",
        label="Category",
    )
    category_dd
    return category_dd, indicator_options


@app.cell
def _(category_dd, indicator_options, mo):
    indicators_in_cat = indicator_options[category_dd.value]
    indicator_dd = mo.ui.dropdown(
        options=indicators_in_cat,
        value=indicators_in_cat[0],
        label="Indicator",
    )
    indicator_dd
    return (indicator_dd,)


@app.cell
def _(W, df, indicator_dd, mo):
    _name = indicator_dd.value
    try:
        _configs = W.pta(df, _name)
        chart_generic = mo.ui.anywidget(
            W(
                series_data=[W.candlestick(df), W.volume(df)] + _configs,
                chart_options=W.dark_theme(),
                height=500,
            )
        )
        chart_generic
    except Exception as e:
        mo.md(f"**Error computing `{_name}`:** {e}")
    return


if __name__ == "__main__":
    app.run()
