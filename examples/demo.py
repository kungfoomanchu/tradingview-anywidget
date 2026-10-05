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

__generated_with = "0.25.1"
app = marimo.App(width="full")


@app.cell
def _():
    import marimo as mo
    import yfinance as yf
    from tradingview_anywidget import LightweightChartWidget

    W = LightweightChartWidget
    return W, mo, yf


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    # TradingView Lightweight Charts for marimo

    `tradingview-anywidget` puts TradingView's
    [Lightweight Charts™](https://tradingview.github.io/lightweight-charts/) (v5)
    into marimo notebooks. You build charts in Python from a pandas or polars
    DataFrame, and the chart reports mouse and scroll events back to Python.

    This notebook has two parts:

    1. **Interactive playground** (right below): one chart with every feature
       behind a switch. No code, just try things.
    2. **Feature reference**: each feature on its own, with an explanation and
       the code that builds it.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ---

    # Interactive playground

    A live demo of everything the widget can do. Pick a ticker, then turn
    features on and off in the panel. The chart redraws on every change; hover
    over it to see values in the legend, drag the pane separators to resize
    panes, scroll to zoom.

    Pick a few features at a time rather than all of them: each oscillator adds
    a pane, and several overlays on one price chart get hard to read.

    Two features in the reference below don't fit on this chart: **comparing
    tickers** (section 5) rescales every ticker to % change, so it's a different
    kind of chart, and **sparklines** (section 8) are several small charts side
    by side.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    # Data controls - shared with the feature reference below
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

    # Playground-only controls
    ma_periods = {"Off": None, "10": 10, "20": 20, "50": 50, "100": 100, "200": 200}
    pg_chart_type = mo.ui.dropdown(
        options=["Candlestick", "Bar", "Line", "Area", "Baseline", "Histogram"],
        value="Candlestick",
        label="Chart type",
    )
    pg_volume = mo.ui.dropdown(options=["Off", "Overlay", "Own pane"], value="Overlay", label="Volume")
    pg_sma = mo.ui.dropdown(options=ma_periods, value="20", label="SMA")
    pg_ema = mo.ui.dropdown(options=ma_periods, value="Off", label="EMA")
    pg_overlay = mo.ui.dropdown(
        options=["Off", "Bollinger Bands", "Supertrend", "VWAP (monthly)", "Ichimoku Cloud"],
        value="Off",
        label="Indicator overlay",
    )
    pg_oscillators = mo.ui.multiselect(
        options=["RSI", "MACD", "Stochastic", "ATR", "ADX", "OBV"],
        value=["RSI"],
        label="Oscillator panes",
    )
    pg_signals = mo.ui.checkbox(value=False, label="Buy/sell markers (SMA 10/30 cross)")
    pg_levels = mo.ui.checkbox(value=False, label="Support / resistance lines")
    pg_watermark = mo.ui.checkbox(value=True, label="Ticker watermark")
    pg_grid = mo.ui.checkbox(value=True, label="Grid")
    pg_crosshair = mo.ui.dropdown(options={"Normal": 0, "Magnet": 1, "Hidden": 2}, value="Normal", label="Crosshair")
    pg_scale = mo.ui.dropdown(
        options={"Normal": 0, "Logarithmic": 1, "Percentage": 2, "Indexed to 100": 3},
        value="Normal",
        label="Price scale",
    )

    def panel_row(title, *items):
        return mo.hstack([mo.md(f"**{title}**").style(width="110px"), *items], justify="start", align="center", gap=1.5, wrap=True)

    mo.callout(
        mo.vstack(
            [
                panel_row("Data", ticker_input, period_dropdown, theme_dropdown, pg_chart_type),
                panel_row("On the price", pg_volume, pg_sma, pg_ema, pg_overlay),
                panel_row("Below the price", pg_oscillators),
                panel_row("Annotations", pg_signals, pg_levels, pg_watermark),
                panel_row("Chart options", pg_grid, pg_crosshair, pg_scale),
            ],
            gap=0.75,
        ),
        kind="info",
    )
    return (
        period_dropdown,
        pg_chart_type,
        pg_crosshair,
        pg_ema,
        pg_grid,
        pg_levels,
        pg_oscillators,
        pg_overlay,
        pg_scale,
        pg_signals,
        pg_sma,
        pg_volume,
        pg_watermark,
        theme_dropdown,
        ticker_input,
    )


@app.cell(hide_code=True)
def _(
    W,
    crossover_markers,
    df,
    mo,
    pg_chart_type,
    pg_crosshair,
    pg_ema,
    pg_grid,
    pg_levels,
    pg_oscillators,
    pg_overlay,
    pg_scale,
    pg_signals,
    pg_sma,
    pg_volume,
    pg_watermark,
    theme,
    ticker,
):
    main_builders = {
        "Candlestick": lambda: W.candlestick(df),
        "Bar": lambda: W.bar(df),
        "Line": lambda: W.line(df),
        "Area": lambda: W.area(df),
        "Baseline": lambda: W.baseline(df, base_value=float(df["Close"].mean())),
        "Histogram": lambda: W.histogram(df),
    }
    main_series = main_builders[pg_chart_type.value]()
    # Set the scale mode on the price pane only, so oscillator panes keep a normal scale
    main_series["priceScale"] = {"mode": pg_scale.value}
    if pg_signals.value:
        main_series["markers"] = crossover_markers(W.sma(df, period=10), W.sma(df, period=30))
    if pg_levels.value:
        top, bottom = float(df["High"].max()), float(df["Low"].min())
        main_series["price_lines"] = [
            W.price_line(top, color="#26a69a", title="Resistance"),
            W.price_line(bottom, color="#ef5350", title="Support"),
        ]
    pg_series = [main_series]

    if pg_sma.value:
        pg_series.append(W.sma(df, period=pg_sma.value))
    if pg_ema.value:
        pg_series.append(W.ema(df, period=pg_ema.value))

    pg_overlays = {
        "Off": lambda: [],
        "Bollinger Bands": lambda: W.pta_bbands(df),
        "Supertrend": lambda: [W.pta_supertrend(df)],
        "VWAP (monthly)": lambda: [W.pta_vwap(df, anchor="M")],
        "Ichimoku Cloud": lambda: W.pta_ichimoku(df),
    }
    pg_series += pg_overlays[pg_overlay.value]()

    next_pane = 1
    if pg_volume.value == "Overlay":
        pg_series.append(W.volume(df))
    elif pg_volume.value == "Own pane":
        pg_series.append(
            {**W.volume(df, priceScaleId="right"), "pane": next_pane,
             "priceScale": {"scaleMargins": {"top": 0.1, "bottom": 0}}}
        )
        next_pane += 1

    pg_oscillator_builders = {
        "RSI": lambda pane: [W.pta_rsi(df, pane=pane)],
        "MACD": lambda pane: W.pta_macd(df, pane=pane),
        "Stochastic": lambda pane: W.pta_stoch(df, pane=pane),
        "ATR": lambda pane: [W.pta_atr(df, pane=pane)],
        "ADX": lambda pane: [W.pta_adx(df, pane=pane)],
        "OBV": lambda pane: [W.pta_obv(df, pane=pane)],
    }
    for oscillator in pg_oscillators.value:
        pg_series += pg_oscillator_builders[oscillator](next_pane)
        next_pane += 1

    pg_grid_color = theme["grid"]["vertLines"]["color"] if pg_grid.value else "transparent"
    playground = mo.ui.anywidget(
        W(
            series_data=pg_series,
            chart_options={
                **theme,
                "grid": {"vertLines": {"color": pg_grid_color}, "horzLines": {"color": pg_grid_color}},
                "crosshair": {"mode": pg_crosshair.value},
            },
            watermark={"text": ticker, "color": "rgba(128, 128, 128, 0.15)", "fontSize": 64} if pg_watermark.value else {},
            height=460 + 140 * (next_pane - 1),
        )
    )
    playground
    return (playground,)


@app.cell(hide_code=True)
def _(describe_event, mo, playground):
    mo.md(
        f"""
        **Crosshair:** {describe_event(playground.value.get("crosshair_data", {}), "hover over the chart")}<br>
        **Last click:** {describe_event(playground.value.get("clicked_data", {}), "click on the chart")}
        """
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ---

    # Feature reference

    Each section below shows one feature with the code that builds it. They use
    the ticker, period and theme picked in the playground above.

    ## Getting data in

    Every helper on `W` (short for `LightweightChartWidget`) takes a **pandas or
    polars DataFrame** and returns a plain dict describing one series:

    - **Columns** are found by name in any letter case, so yfinance's `Close`
      and a lowercase `close` both work. A missing column raises `KeyError`.
    - **Times** come from a `date`, `time`, `datetime` or `timestamp` column, a
      pandas `DatetimeIndex`, or whichever column you name with `time_column=`.
      Daily data and intraday data (minutes, hours) are both handled.
    - **Missing values** (NaN) are skipped, which is why indicators start a few
      bars in.
    - **Extra keyword arguments** become Lightweight Charts series options,
      e.g. `W.line(df, color="#f00", title="Close")`.

    The cell below downloads daily prices from Yahoo Finance. `@mo.cache`
    remembers each download, so moving a slider doesn't fetch the data again.
    """)
    return


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
    ticker = ticker_input.value.strip().upper()
    df = load_prices(ticker, period_dropdown.value)
    theme = W.theme(theme_dropdown.value)
    return df, theme, ticker


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## 1. Series types, volume and watermark

    Lightweight Charts has six series types, each with a helper:

    | Helper | Draws | Columns used |
    |---|---|---|
    | `W.candlestick(df)` | Candles, green up / red down | open, high, low, close |
    | `W.bar(df)` | OHLC bars | open, high, low, close |
    | `W.line(df, column="close")` | A line | one column |
    | `W.area(df, column="close")` | A line with a filled area below | one column |
    | `W.baseline(df, base_value=...)` | Green above `base_value`, red below | one column |
    | `W.histogram(df, column="close")` | Vertical bars | one column |

    `W.volume(df)` is a histogram of the `volume` column, colored green or red
    by whether the bar closed up or down. It sits in the bottom 20% of the price
    pane on its own hidden scale, so it doesn't distort the price axis.

    `watermark=` puts large faint text behind the chart: pass `text`, and
    optionally `color`, `fontSize`, `horzAlign` and `vertAlign`.
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
def _(W, chart_type, df, mo, show_volume, theme, ticker):
    builders = {
        "Candlestick": lambda: W.candlestick(df),
        "Bar": lambda: W.bar(df),
        "Line": lambda: W.line(df),
        "Area": lambda: W.area(df),
        # Green above the period's average price, red below
        "Baseline": lambda: W.baseline(df, base_value=float(df["Close"].mean())),
        "Histogram": lambda: W.histogram(df),
    }
    mo.ui.anywidget(
        W(
            series_data=[builders[chart_type.value]()] + ([W.volume(df)] if show_volume.value else []),
            chart_options=theme,
            watermark={"text": ticker, "color": "rgba(128, 128, 128, 0.15)", "fontSize": 64},
            height=450,
        )
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## 2. Moving averages

    `W.sma(df, period=20)` (simple moving average) and `W.ema(df, period=20)`
    (exponential moving average, which reacts faster to recent prices) are
    computed in pure Python, so they need no extra packages. Both average the
    `close` column by default; pass `column=` to average something else.

    They're drawn as thin lines with a title (`SMA 20`) that shows in the
    legend, and without the price-axis label so they don't clutter the axis.
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


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## 3. Signals with series markers

    Markers are arrows, circles or squares pinned to a bar, with optional text.
    Build each one with `W.marker(time, position, shape, color, text)` and attach
    the list to a series under the `"markers"` key:

    - `position`: `"aboveBar"`, `"belowBar"` or `"inBar"`
    - `shape`: `"arrowUp"`, `"arrowDown"`, `"circle"` or `"square"`
    - `time` must match the time of a bar in that series exactly, otherwise
      the marker is silently dropped. Taking times from the series' own `data`,
      as below, guarantees a match.

    This example marks a **buy** where the 10-day SMA crosses above the 30-day
    SMA (a "golden cross") and a **sell** where it crosses below.
    """)
    return


@app.cell
def _(W):
    def crossover_markers(fast, slow):
        """Buy/sell markers where the `fast` series crosses the `slow` one."""
        slow_by_time = {p["time"]: p["value"] for p in slow["data"]}
        markers = []
        prev_diff = None
        for point in fast["data"]:
            if point["time"] not in slow_by_time:
                continue
            diff = point["value"] - slow_by_time[point["time"]]
            if prev_diff is not None and prev_diff <= 0 < diff:
                markers.append(W.marker(point["time"], "belowBar", "arrowUp", "#26a69a", "Buy"))
            elif prev_diff is not None and prev_diff >= 0 > diff:
                markers.append(W.marker(point["time"], "aboveBar", "arrowDown", "#ef5350", "Sell"))
            prev_diff = diff
        return markers

    return (crossover_markers,)


@app.cell
def _(W, crossover_markers, df, mo, theme):
    sma_fast = W.sma(df, period=10, color="#FF6D00")
    sma_slow = W.sma(df, period=30, color="#2196F3")

    mo.ui.anywidget(
        W(
            series_data=[
                {**W.candlestick(df), "markers": crossover_markers(sma_fast, sma_slow)},
                sma_fast,
                sma_slow,
            ],
            chart_options=theme,
            height=400,
        )
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## 4. Price lines (support / resistance)

    A price line is a horizontal line across the chart at a fixed price, with a
    label on the price axis. Build one with
    `W.price_line(price, color, line_width, line_style, title)` and attach a
    list of them to a series under `"price_lines"`.

    `line_style` is `0` solid, `1` dotted, `2` dashed (default), `3` large
    dashes, `4` sparse dots. Here the lines mark the period's high, low and
    midpoint.
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


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## 5. Comparing tickers

    Stocks at different prices can't share a price axis, so each one is
    rescaled to **% change since the start of the period** and drawn with
    `W.line()`. Any DataFrame column can be plotted this way: add the column
    with pandas, then pass its name as `column=`.

    `title=` labels each line in the legend, and the series option
    `priceFormat={"type": "percent"}` adds a `%` to the axis labels.
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
    for i, compare_ticker in enumerate(compare_tickers):
        prices = load_prices(compare_ticker, period_dropdown.value)
        pct_change = prices.assign(pct=(prices["Close"] / prices["Close"].iloc[0] - 1) * 100)
        compare_series.append(
            W.line(pct_change, column="pct", color=palette[i % len(palette)], title=compare_ticker,
                   priceFormat={"type": "percent"})
        )

    mo.ui.anywidget(W(series_data=compare_series, chart_options=theme, height=400))
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## 6. Chart options and themes

    `chart_options=` takes any Lightweight Charts
    [chart option](https://tradingview.github.io/lightweight-charts/docs/api/interfaces/ChartOptionsBase)
    as a nested dict. A few useful ones:

    - `"crosshair": {"mode": ...}`: `0` follows the mouse freely, `1` snaps to
      the closing price (magnet), `2` hides the crosshair.
    - `"rightPriceScale": {"mode": ...}`: `0` normal, `1` logarithmic (good for
      long periods of growth), `2` % change, `3` indexed to 100.
    - `"grid"`: grid line colors.

    `rightPriceScale` applies to the price scale of **every pane**, so a log
    scale would also squash an RSI pane. To change only the price pane, set the
    scale on the price series instead: `{**W.candlestick(df), "priceScale": {"mode": 1}}`.

    `W.theme("dark")` and `W.theme("light")` return a full set of colors for the
    background, text, grid and borders; `W.theme(mo.app_meta().theme)` follows
    the notebook's own theme. Merge your own options on top with `{**theme, ...}`.
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


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## 7. Click, crosshair and scroll events

    The chart sends three things back to Python, available in another cell as
    `chart.value[...]`:

    - `crosshair_data`: the bar under the mouse, as `{"time", "series_values", "x", "y"}`.
      `series_values` has one entry per series under the crosshair
      (`open`/`high`/`low`/`close` for candles, `value` for lines).
    - `clicked_data`: the same, for the last bar clicked.
    - `visible_range`: the `{"from", "to"}` times currently on screen, updated
      after scrolling or zooming. Setting it from Python scrolls the chart.

    Any cell that reads these reruns when they change, like the summary below
    the chart. Crosshair updates are limited to 10 per second so the notebook
    doesn't rerun on every pixel of mouse movement.
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
def _():
    def describe_event(event, empty_text):
        """One-line summary of a crosshair or click event on a candlestick chart."""
        if not event.get("series_values"):
            return empty_text
        bar = event["series_values"][0]
        if "close" not in bar:
            return f"`{event['time']}` · **{bar['value']:.2f}**"
        return (
            f"`{event['time']}` · O **{bar['open']:.2f}** H **{bar['high']:.2f}** "
            f"L **{bar['low']:.2f}** C **{bar['close']:.2f}**"
        )

    return (describe_event,)


@app.cell
def _(describe_event, events_chart, mo):
    visible = events_chart.value.get("visible_range", {})
    mo.md(
        f"""
        - **Crosshair:** {describe_event(events_chart.value.get("crosshair_data", {}), "move your mouse over the chart")}
        - **Last click:** {describe_event(events_chart.value.get("clicked_data", {}), "click on the chart")}
        - **Visible range:** {visible.get("from", "?")} → {visible.get("to", "?")}
        """
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## 8. Sparklines

    Small, static charts for dashboards: a short `height`, scrolling and zooming
    turned off (`handleScroll`, `handleScale`), and the axes, grid and crosshair
    hidden. `mo.hstack` lays several out side by side.
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


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    # Technical indicators with pandas-ta

    The `pta_` helpers compute indicators with
    [pandas-ta](https://github.com/twopirllc/pandas-ta) (an optional extra:
    `uv pip install pandas-ta`) and return ready-styled series. Indicators on the
    same scale as the price are drawn **on the price chart**; the rest
    (oscillators) get **their own pane** below it.

    ## 9. Overlays on the price chart

    - `W.pta_bbands(df, length=20, std=2.0)`, **Bollinger Bands**: a moving
      average with bands `std` standard deviations above and below. Wide bands
      mean a volatile market.
    - `W.pta_supertrend(df, length=7, multiplier=3.0)`, **Supertrend**: a
      trailing line that is green below the price in an uptrend and red above
      it in a downtrend.
    - `W.pta_vwap(df, anchor="M")`, **VWAP**: the average price weighted by
      volume, restarting each `anchor` period (`"D"` day, `"W"` week, `"M"`
      month). Use `"D"` for intraday data; on daily bars use `"W"` or `"M"`.
    - `W.pta_ichimoku(df)`, **Ichimoku Cloud**: five lines. The two Senkou spans
      form the "cloud" and extend 26 bars past the last candle.
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


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## 10. Oscillators in panes

    Each oscillator helper puts its series in pane `1` (just below the price) by
    default. To stack several, give each a different `pane=`, as this example
    does. Panes below the price start at about 40% of its height; drag the
    separators to resize them.

    - `W.pta_rsi(df, length=14)`, **RSI**: momentum from 0 to 100, with dashed
      lines at 70 (overbought) and 30 (oversold).
    - `W.pta_macd(df, fast=12, slow=26, signal=9)`, **MACD**: the MACD and
      signal lines plus a green/red histogram of the gap between them.
    - `W.pta_stoch(df, k=14, d=3)`, **Stochastic**: %K and %D lines from 0 to
      100, with lines at 80 and 20.
    - `W.pta_atr(df, length=14)`, **ATR**: average true range, a measure of
      volatility in price units.
    - `W.pta_adx(df, length=14)`, **ADX**: trend strength from 0 to 100, with a
      line at 25 (above it, the market is trending).
    - `W.pta_obv(df)`, **OBV**: on-balance volume, a running total of volume
      on up days minus down days.

    Any series can go in its own pane the same way: add `"pane": n` to its dict,
    e.g. `{**W.volume(df), "pane": 1}`.
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


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## 11. Any pandas-ta indicator

    `W.pta(df, "name", **kwargs)` runs **any** of pandas-ta's 200+ indicators by
    name and returns a list of series, one per output column. Keyword arguments
    go straight to pandas-ta, e.g. `W.pta(df, "rsi", length=21)`.

    It decides placement for you: oscillators go in pane 1, price-like
    indicators stay on the price chart, and an indicator's non-price outputs
    (such as the Bollinger bandwidth) are moved off the price chart so they
    don't squash the candles. Columns pandas-ta marks as histograms (like
    MACD's) are drawn as bars. Pass `pane=` to override.

    Use the curated `pta_` helpers above when they exist: they add reference
    lines, colors and titles that the generic version can't know about.
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
