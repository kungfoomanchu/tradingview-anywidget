# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo",
#     "yfinance>=0.2.0",
#     "pandas>=1.5.0",
#     "pandas-ta>=0.3.14b",
#     "lightweight-charts-anywidget",
# ]
#
# [tool.uv.sources]
# lightweight-charts-anywidget = { path = "..", editable = true }
# ///

import marimo

__generated_with = "0.25.1"
app = marimo.App(width="full")


@app.cell
def _():
    import marimo as mo
    import yfinance as yf
    from lightweight_charts_anywidget import LightweightChartWidget

    W = LightweightChartWidget
    return W, mo, yf


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    # TradingView Lightweight Charts for marimo

    `lightweight-charts-anywidget` puts TradingView's
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
    a pane, and several overlays on one price chart get hard to read. Click a
    name in the legend to hide or show that series, and use the buttons below
    the chart to move it from Python. Below the chart, the events reported back
    to Python update as you hover, click and double-click.

    Three features in the reference below don't fit on this chart: **comparing
    tickers** (section 5) rescales every ticker to % change, so it's a different
    kind of chart; **sparklines** (section 8) are several small charts side by
    side; and **live data** (section 14) streams new bars into a chart, which
    would leave this chart's indicators behind.
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
    pg_volume = mo.ui.dropdown(
        options=["Off", "Overlay", "Overlay, left axis", "Own pane"], value="Overlay", label="Volume"
    )
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
    pg_watermark = mo.ui.dropdown(
        options=["Off", "Ticker text", "Logo image", "Both"], value="Ticker text", label="Watermark"
    )
    pg_grid = mo.ui.checkbox(value=True, label="Grid")
    pg_crosshair = mo.ui.dropdown(
        options={"Normal": "normal", "Magnet (close)": "magnet", "Magnet (OHLC)": "magnet_ohlc", "Hidden": "hidden"},
        value="Normal",
        label="Crosshair",
    )
    pg_crosshair_style = mo.ui.dropdown(
        options=["large_dashed", "dashed", "dotted", "solid"], value="large_dashed", label="Crosshair line"
    )
    pg_format = mo.ui.dropdown(
        options=["Default", "US dollars", "Euros, German dates", "Compact numbers"],
        value="Default",
        label="Number and date format",
    )
    pg_pane_size = mo.ui.slider(start=0.2, stop=1.0, step=0.1, value=0.4, label="Lower pane size", show_value=True)
    pg_scale = mo.ui.dropdown(
        options={"Normal": "normal", "Logarithmic": "log", "Percentage": "percentage", "Indexed to 100": "indexed"},
        value="Normal",
        label="Price scale",
    )
    pg_line_type = mo.ui.dropdown(options=["simple", "steps", "curved"], value="simple", label="Line type")
    pg_points = mo.ui.checkbox(value=False, label="Point markers")
    pg_ma_style = mo.ui.dropdown(options=["solid", "dotted", "dashed"], value="solid", label="Average line style")
    pg_bar_spacing = mo.ui.slider(start=2, stop=20, value=6, label="Bar spacing", show_value=True)
    pg_right_offset = mo.ui.slider(start=0, stop=30, value=0, label="Right offset", show_value=True)
    pg_wheel = mo.ui.dropdown(
        options={"Zooms the chart": True, "Scrolls the page": False}, value="Zooms the chart", label="Mouse wheel"
    )

    def panel_row(title, *items):
        return mo.hstack([mo.md(f"**{title}**").style(width="110px"), *items], justify="start", align="center", gap=1.5, wrap=True)

    mo.callout(
        mo.vstack(
            [
                panel_row("Data", ticker_input, period_dropdown, theme_dropdown, pg_chart_type),
                panel_row("On the price", pg_volume, pg_sma, pg_ema, pg_overlay),
                panel_row("Below the price", pg_oscillators, pg_pane_size),
                panel_row("Annotations", pg_signals, pg_levels, pg_watermark),
                panel_row("Line style", pg_line_type, pg_points, pg_ma_style),
                panel_row("Chart options", pg_grid, pg_crosshair, pg_crosshair_style, pg_scale),
                panel_row("Formatting", pg_format),
                panel_row("Time axis", pg_bar_spacing, pg_right_offset, pg_wheel),
            ],
            gap=0.75,
        ),
        kind="info",
    )
    return (
        period_dropdown,
        pg_chart_type,
        pg_crosshair,
        pg_crosshair_style,
        pg_bar_spacing,
        pg_ema,
        pg_format,
        pg_grid,
        pg_levels,
        pg_line_type,
        pg_ma_style,
        pg_oscillators,
        pg_overlay,
        pg_pane_size,
        pg_points,
        pg_right_offset,
        pg_scale,
        pg_signals,
        pg_sma,
        pg_volume,
        pg_watermark,
        pg_wheel,
        theme_dropdown,
        ticker_input,
    )


@app.cell(hide_code=True)
def _(
    W,
    crossover_markers,
    df,
    logo_svg,
    mo,
    pg_bar_spacing,
    pg_chart_type,
    pg_crosshair,
    pg_crosshair_style,
    pg_ema,
    pg_format,
    pg_grid,
    pg_levels,
    pg_line_type,
    pg_ma_style,
    pg_oscillators,
    pg_overlay,
    pg_pane_size,
    pg_points,
    pg_right_offset,
    pg_scale,
    pg_signals,
    pg_sma,
    pg_volume,
    pg_watermark,
    pg_wheel,
    theme,
    ticker,
):
    # Line styles only apply to the line-based series types
    pg_line_style = {"line_type": pg_line_type.value, "point_markers_visible": pg_points.value}
    main_builders = {
        "Candlestick": lambda: W.candlestick(df),
        "Bar": lambda: W.bar(df),
        "Line": lambda: W.line(df, **pg_line_style),
        "Area": lambda: W.area(df, **pg_line_style),
        "Baseline": lambda: W.baseline(df, base_value=float(df["Close"].mean()), **pg_line_style),
        "Histogram": lambda: W.histogram(df),
    }
    main_series = main_builders[pg_chart_type.value]()
    # Set the scale mode on the price pane only, so oscillator panes keep a normal scale
    main_series["priceScale"] = W.price_scale(mode=pg_scale.value)
    if pg_signals.value:
        main_series["markers"] = crossover_markers(W.sma(df, period=10), W.sma(df, period=30))
    if pg_levels.value:
        top, bottom = float(df["High"].max()), float(df["Low"].min())
        main_series["price_lines"] = [
            W.price_line(top, color="#26a69a", title="Resistance", id="resistance"),
            W.price_line(bottom, color="#ef5350", title="Support", id="support"),
        ]
    pg_series = [main_series]

    if pg_sma.value:
        pg_series.append(W.sma(df, period=pg_sma.value, line_style=pg_ma_style.value))
    if pg_ema.value:
        pg_series.append(W.ema(df, period=pg_ema.value, line_style=pg_ma_style.value))

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
    elif pg_volume.value == "Overlay, left axis":
        # A series on the "left" scale shows the left axis automatically
        pg_series.append(W.volume(df, price_scale_id="left"))
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

    # (chart_options, the price series' price format): currency goes on the price
    # series only, so oscillator panes keep plain numbers
    pg_formats = {
        "Default": ({}, None),
        "US dollars": (
            W.localization(
                locale="en-US",
                time_formatter=W.date_format(weekday="short", month="short", day="numeric", year="numeric"),
            ),
            W.number_format(style="currency", currency="USD"),
        ),
        "Euros, German dates": (
            W.localization(
                locale="de-DE",
                time_formatter=W.date_format(day="2-digit", month="2-digit", year="numeric"),
                tick_formatters={"day": W.date_format(day="numeric", month="numeric")},
            ),
            W.number_format(style="currency", currency="EUR"),
        ),
        "Compact numbers": ({}, W.number_format(notation="compact", maximum_significant_digits=4)),
    }
    pg_format_options, pg_price_format = pg_formats[pg_format.value]
    if pg_price_format:
        main_series["options"]["priceFormat"] = pg_price_format
    pg_text_mark = {"text": ticker, "color": "rgba(128, 128, 128, 0.15)", "fontSize": 64}
    pg_logo_mark = W.image_watermark(logo_svg, alpha=0.12, max_height=140, padding=20)
    pg_watermarks = {
        "Off": [],
        "Ticker text": [pg_text_mark],
        "Logo image": [pg_logo_mark],
        "Both": [{**pg_text_mark, "vertAlign": "top"}, pg_logo_mark],
    }
    pg_grid_color = theme["grid"]["vertLines"]["color"] if pg_grid.value else "transparent"
    pg_widget = W(
        series_data=pg_series,
        chart_options=W.merge_options(
            theme,
            {"grid": {"vertLines": {"color": pg_grid_color}, "horzLines": {"color": pg_grid_color}}},
            W.crosshair(mode=pg_crosshair.value, style=pg_crosshair_style.value),
            W.time_scale(bar_spacing=pg_bar_spacing.value, right_offset=pg_right_offset.value),
            W.interaction(mouse_wheel=pg_wheel.value),
            pg_format_options,
        ),
        watermark=pg_watermarks[pg_watermark.value],
        # Main pane 1, every pane below it pg_pane_size
        pane_heights=[1] + [pg_pane_size.value] * (next_pane - 1),
        # Keep the bar spacing picked above instead of fitting every bar on screen
        fit_content=False,
        height=460 + int(350 * pg_pane_size.value) * (next_pane - 1),
    )
    playground = mo.ui.anywidget(pg_widget)
    playground
    return pg_widget, playground


@app.cell(hide_code=True)
def _(mo, pg_widget):
    # Depends on the widget object, not its value, so the buttons aren't rebuilt on every mouse move
    pg_bar_count = len(pg_widget.series_data[0]["data"])

    def pg_show_last(n):
        pg_widget.logical_range = {"from": pg_bar_count - n, "to": pg_bar_count - 1}

    # Buttons must be assigned to variables for marimo to run their on_click
    pg_show_all = mo.ui.button(label="Show all", on_click=lambda _: pg_widget.show_all())
    pg_last_50 = mo.ui.button(label="Last 50 bars", on_click=lambda _: pg_show_last(50))
    pg_back_50 = mo.ui.button(label="Back 50 bars", on_click=lambda _: pg_widget.scroll_to_position(-50, animated=True))
    pg_latest = mo.ui.button(label="Latest bar", on_click=lambda _: pg_widget.scroll_to_real_time())
    mo.hstack([pg_show_all, pg_last_50, pg_back_50, pg_latest], justify="start", gap=0.5)
    return


@app.cell(hide_code=True)
def _(mo, playground):
    mo.md(f"""
    **Crosshair:** {describe_event(playground.value.get("crosshair_data", {}), "hover over the chart")}<br>
    **Mouse at:** {describe_pointer(playground.value.get("crosshair_data", {}))}<br>
    **Last click:** {describe_event(playground.value.get("clicked_data", {}), "click on the chart")}<br>
    **Last double-click:** {describe_event(playground.value.get("double_clicked_data", {}), "double-click on the chart")}<br>
    **On screen:** {describe_visible_bars(playground.value.get("visible_bars", {}))}
    """)
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


@app.cell(hide_code=True)
def _():
    # A small logo for the image watermark examples (any URL, file path or image bytes works)
    logo_svg = b"""<svg xmlns="http://www.w3.org/2000/svg" width="240" height="160" viewBox="0 0 240 160">
      <polyline points="10,140 70,90 110,110 170,40 230,60" fill="none" stroke="#2962FF" stroke-width="14"
        stroke-linecap="round" stroke-linejoin="round"/>
      <circle cx="170" cy="40" r="16" fill="#FF6D00"/>
    </svg>"""
    return (logo_svg,)


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

    `watermark=` puts large faint text or an image behind the chart:

    - **Text:** `{"text": "AAPL"}`, optionally with `color`, `fontSize`,
      `horzAlign` (`"left"`, `"center"`, `"right"`) and `vertAlign` (`"top"`,
      `"center"`, `"bottom"`).
    - **Image:** `W.image_watermark(src, alpha=0.3, max_width=, max_height=, padding=0)`.
      `src` is an image URL, a local file path or image bytes (files and bytes
      are embedded in the notebook).
    - Pass a **list** for several watermarks, and add `"pane": n` to one (or
      `pane=n` to `W.image_watermark`) to put it in a lower pane.
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
    watermark_kind = mo.ui.dropdown(options=["Text", "Image", "Text and image"], value="Text", label="Watermark")
    mo.hstack([chart_type, show_volume, watermark_kind], justify="start", gap=1)
    return chart_type, show_volume, watermark_kind


@app.cell
def _(W, chart_type, df, logo_svg, mo, show_volume, theme, ticker, watermark_kind):
    builders = {
        "Candlestick": lambda: W.candlestick(df),
        "Bar": lambda: W.bar(df),
        "Line": lambda: W.line(df),
        "Area": lambda: W.area(df),
        # Green above the period's average price, red below
        "Baseline": lambda: W.baseline(df, base_value=float(df["Close"].mean())),
        "Histogram": lambda: W.histogram(df),
    }
    text_mark = {"text": ticker, "color": "rgba(128, 128, 128, 0.15)", "fontSize": 64}
    logo_mark = W.image_watermark(logo_svg, alpha=0.15, max_height=150)
    mo.ui.anywidget(
        W(
            series_data=[builders[chart_type.value]()] + ([W.volume(df)] if show_volume.value else []),
            chart_options=theme,
            watermark={
                "Text": [text_mark],
                "Image": [logo_mark],
                "Text and image": [{**text_mark, "vertAlign": "top"}, logo_mark],
            }[watermark_kind.value],
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
    - `id=` (optional) names the marker: while the mouse is over it, events
      report it as `hovered_object_id` (section 7, and the playground's
      "Mouse at" line).

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
                markers.append(W.marker(point["time"], "belowBar", "arrowUp", "#26a69a", "Buy", id=f"Buy {point['time']}"))
            elif prev_diff is not None and prev_diff >= 0 > diff:
                markers.append(W.marker(point["time"], "aboveBar", "arrowDown", "#ef5350", "Sell", id=f"Sell {point['time']}"))
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

    `line_style` is `"solid"`, `"dotted"`, `"dashed"` (default),
    `"large_dashed"` or `"sparse_dotted"` (or `0`-`4`). `id=` works as for
    markers. Here the lines mark the period's high, low and midpoint.
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
                        W.price_line((period_high + period_low) / 2, color="#787B86", title="Mid", line_style="dotted"),
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
      the closing price (magnet), `2` hides the crosshair, `3` snaps to the
      nearest open/high/low/close. `W.crosshair()` (section 12) styles it too.
    - `"rightPriceScale": {"mode": ...}`: `0` normal, `1` logarithmic (good for
      long periods of growth), `2` % change, `3` indexed to 100.
    - `"grid"`: grid line colors.

    `rightPriceScale` applies to the price scale of **every pane**, so a log
    scale would also squash an RSI pane. To change only the price pane, set the
    scale on the price series instead:
    `{**W.candlestick(df), "priceScale": W.price_scale(mode="log")}` (section 9).

    `W.theme("dark")` and `W.theme("light")` return a full set of colors for the
    background, text, grid and borders; `W.theme(mo.app_meta().theme)` follows
    the notebook's own theme. Add your own options on top with
    `W.merge_options(theme, {...})`, which merges nested dicts key by key, so
    `{"rightPriceScale": {"mode": 1}}` keeps the theme's border color. (A plain
    `{**theme, ...}` replaces the whole `rightPriceScale` dict.)
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
            chart_options=W.merge_options(
                theme,
                {
                    "grid": {"vertLines": {"color": grid_color}, "horzLines": {"color": grid_color}},
                    "crosshair": {"mode": crosshair_mode.value},
                    "rightPriceScale": {"mode": price_scale_mode.value},
                },
            ),
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
      (`open`/`high`/`low`/`close` for candles, `value` for lines). It also has
      `price` (the price at the mouse, on the scale of the first series in
      that pane), `logical` (the bar index), `pane`, and when the mouse is over
      a series, marker or price line: `hovered_series` (its index in
      `series_data`), `hovered_type` (`"marker"`, `"price-line"`,
      `"series-point"`, ...) and `hovered_object_id` (the marker's or line's `id`).
    - `clicked_data` / `double_clicked_data`: the same, for the last bar
      clicked or double-clicked. Clicking at a price, e.g. to add a price line
      there, is `clicked_data["price"]`.
    - `visible_range`: the `{"from", "to"}` times currently on screen, updated
      after scrolling or zooming. Setting it from Python scrolls the chart.
    - `logical_range`: the same range as bar indices (`0` is the first bar;
      fractions and values past the last bar are allowed). Setting it from
      Python also scrolls the chart (section 11).
    - `visible_bars`: the first series' bars on screen, as
      `{"from", "to", "bars_before", "bars_after"}`: the times of the first and
      last visible bar and how many bars are off screen on each side. A small
      `bars_before` means the user scrolled to the start of the data.

    `W.rows_in_range(df, chart.value["visible_range"])` returns the DataFrame
    rows that are on screen (pandas or polars), for stats about what the user
    is looking at, like the return over the visible bars below.

    Any cell that reads these reruns when they change, like the summary below
    the chart. Crosshair updates are limited to 10 per second, and range
    updates are sent once scrolling stops, so the notebook doesn't rerun on
    every pixel of mouse movement.
    """)
    return


@app.cell
def _(W, df, mo, theme):
    events_chart = mo.ui.anywidget(
        W(series_data=[W.candlestick(df), W.volume(df)], chart_options=theme, height=350)
    )
    events_chart
    return (events_chart,)


@app.function
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


@app.function
def describe_pointer(event):
    """Price, pane and hovered object of a crosshair event."""
    if "price" not in event:
        return "hover over the chart"
    text = f"price **{event['price']:.2f}** in pane {event.get('pane', 0)}"
    if "hovered_object_id" in event:
        text += f" · over {event.get('hovered_type', 'object')} `{event['hovered_object_id']}`"
    elif "hovered_series" in event:
        text += f" · over series {event['hovered_series']}"
    return text


@app.function
def describe_visible_bars(bars):
    """One-line summary of a visible_bars event."""
    if not bars:
        return "scroll or zoom the chart"
    return (
        f"`{bars['from']}` → `{bars['to']}` · {bars['bars_before']} bars before, "
        f"{bars['bars_after']} after"
    )


@app.cell
def _(W, df, events_chart, mo):
    visible = events_chart.value.get("visible_range", {})
    logical = events_chart.value.get("logical_range", {})
    on_screen = W.rows_in_range(df, visible)
    visible_return = (on_screen["Close"].iloc[-1] / on_screen["Close"].iloc[0] - 1) * 100 if len(on_screen) else 0
    mo.md(
        f"""
        - **Crosshair:** {describe_event(events_chart.value.get("crosshair_data", {}), "move your mouse over the chart")}
        - **Mouse at:** {describe_pointer(events_chart.value.get("crosshair_data", {}))}
        - **Last click:** {describe_event(events_chart.value.get("clicked_data", {}), "click on the chart")}
        - **Last double-click:** {describe_event(events_chart.value.get("double_clicked_data", {}), "double-click on the chart")}
        - **Visible range:** {visible.get("from", "?")} → {visible.get("to", "?")}
        - **Visible bars:** {describe_visible_bars(events_chart.value.get("visible_bars", {}))}
        - **Logical range:** bars {logical.get("from", 0):.1f} → {logical.get("to", 0):.1f}
        - **Return over the visible bars:** {len(on_screen)} rows, {visible_return:+.1f}%
        """
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## 8. Sparklines

    Small, static charts for dashboards: a short `height`, scrolling and zooming
    turned off with `W.interaction(scroll=False, zoom=False)`, and the axes,
    grid and crosshair hidden. `mo.hstack` lays several out side by side.
    """)
    return


@app.cell
def _(W, df, mo, theme):
    sparkline_options = W.merge_options(
        theme,
        W.interaction(scroll=False, zoom=False),
        W.time_scale(visible=False),
        {
            "rightPriceScale": W.price_scale(visible=False),
            "grid": {"vertLines": {"visible": False}, "horzLines": {"visible": False}},
            "crosshair": {"mode": 2},
        },
    )
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
    ## 9. Time axis, price axes and the mouse

    Four helpers build `chart_options` without looking up Lightweight Charts'
    option names. All take snake_case arguments; options you leave out keep
    their current value.

    - `W.time_scale(bar_spacing=, right_offset=, fix_left_edge=, fix_right_edge=, time_visible=, seconds_visible=, visible=, border_visible=)`
      returns `{"timeScale": {...}}`. `bar_spacing` is the width of one bar in
      pixels (the zoom level, default 6), `right_offset` leaves empty bars after
      the latest one, and the `fix_*_edge` options stop scrolling past the first
      or latest bar. Intraday data shows the time of day on the axis
      automatically (and seconds only when the data has them); pass
      `time_visible=` / `seconds_visible=` to override.
    - `W.price_scale(mode=, visible=, border_visible=, auto_scale=, invert_scale=, margins=(top, bottom))`
      returns options for one price scale. Put it on a series as
      `"priceScale"` to change only that series' scale in its pane. `mode` is
      `"normal"`, `"log"`, `"percentage"` or `"indexed"`.
    - **Left axis:** give a series `price_scale_id="left"` and the left axis
      appears automatically (hide it with
      `"priceScale": W.price_scale(visible=False)`). Below, volume gets its own
      labeled axis on the left. Showing or hiding the left or right axis
      applies to every pane, since the panes share their axis widths; the other
      `W.price_scale()` options apply only to the series' own pane.
    - `W.interaction(scroll=True, zoom=True, mouse_wheel=True)` controls the
      mouse and touch. `mouse_wheel=False` leaves the wheel to the page, so
      scrolling down the notebook doesn't get stuck zooming the chart.
    - `W.merge_options(theme, ...)` deep-merges any number of these dicts.

    With `fit_content=True` (the default) the chart zooms to fit every bar on
    each redraw, which overrides `bar_spacing`; the example turns it off.
    Any other time scale option (`ticks_visible`, `min_bar_spacing`, ...) can be
    passed by name too.
    """)
    return


@app.cell
def _(mo):
    bar_spacing = mo.ui.slider(start=2, stop=30, value=8, label="Bar spacing", show_value=True)
    right_offset = mo.ui.slider(start=0, stop=40, value=5, label="Right offset", show_value=True)
    fix_edges = mo.ui.checkbox(value=True, label="Stop at first/last bar")
    wheel_zooms = mo.ui.checkbox(value=False, label="Mouse wheel zooms the chart")
    mo.hstack([bar_spacing, right_offset, fix_edges, wheel_zooms], justify="start", gap=1.5, wrap=True)
    return bar_spacing, fix_edges, right_offset, wheel_zooms


@app.cell
def _(W, bar_spacing, df, fix_edges, mo, right_offset, theme, wheel_zooms):
    mo.ui.anywidget(
        W(
            series_data=[
                W.candlestick(df),
                # Volume on the left axis, with labels, in the bottom 25% of the pane
                {**W.volume(df, price_scale_id="left"), "priceScale": W.price_scale(margins=(0.75, 0))},
            ],
            chart_options=W.merge_options(
                theme,
                W.time_scale(
                    bar_spacing=bar_spacing.value,
                    right_offset=right_offset.value,
                    fix_left_edge=fix_edges.value,
                    fix_right_edge=fix_edges.value and right_offset.value == 0,
                ),
                W.interaction(mouse_wheel=wheel_zooms.value),
            ),
            fit_content=False,
            height=400,
        )
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## 10. Line styles and hiding series

    Keyword arguments to any helper become series options, written in
    snake_case or Lightweight Charts' own camelCase (`line_style` and
    `lineStyle` both work). Options that are numbered in Lightweight Charts
    also take names:

    | Option | Values |
    |---|---|
    | `line_style` | `"solid"`, `"dotted"`, `"dashed"`, `"large_dashed"`, `"sparse_dotted"` |
    | `line_type` | `"simple"`, `"steps"`, `"curved"` |
    | `last_price_animation` | `"disabled"`, `"continuous"` (a pulsing dot on the last value), `"on_data_update"` |

    Other useful ones: `line_width=`, `point_markers_visible=True` (a dot on
    every data point), `crosshair_marker_visible=False` and `visible=False`.

    **Click a name in the legend** to hide or show that series; hidden series
    are dimmed and struck through. `visible=False` starts a series hidden, like
    the EMA below.
    """)
    return


@app.cell
def _(mo):
    line_type = mo.ui.dropdown(options=["simple", "steps", "curved"], value="steps", label="Close line type")
    ma_style = mo.ui.dropdown(
        options=["solid", "dotted", "dashed", "large_dashed", "sparse_dotted"], value="dashed", label="SMA style"
    )
    mo.hstack([line_type, ma_style], justify="start", gap=1)
    return line_type, ma_style


@app.cell
def _(W, df, line_type, ma_style, mo, theme):
    recent = df.tail(60)
    mo.ui.anywidget(
        W(
            series_data=[
                W.line(recent, title="Close", line_type=line_type.value, point_markers_visible=True,
                       last_price_animation="continuous"),
                W.sma(recent, period=10, line_style=ma_style.value, line_width=2),
                W.ema(recent, period=10, line_width=2, visible=False),
            ],
            chart_options=theme,
            height=350,
        )
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## 11. Moving the chart from Python

    Keep a reference to the widget (`chart = W(...)`, then
    `mo.ui.anywidget(chart)`) and call these from a button or any other cell:

    - `chart.show_all()`: zoom out so every bar fits.
    - `chart.scroll_to_real_time()`: jump to the latest bar, keeping the zoom.
    - `chart.scroll_to_position(position, animated=False)`: put the latest bar
      `position` bars from the right edge; negative values scroll back in time.
    - `chart.logical_range = {"from": first, "to": last}`: show exactly these
      bars, by index. `{"from": n - 50, "to": n - 1}` shows the last 50 of `n`.
    - `chart.visible_range = {"from": "2024-01-01", "to": "2024-06-30"}` does
      the same with times.

    The methods send a one-off command to the chart, so they also work when the
    chart is already showing the same range. Read the result back from
    `chart.value[...]` (section 7).

    The buttons' cell refers to the widget object (`nav_chart`), not the
    `mo.ui.anywidget` wrapper's value, so it doesn't rerun on every mouse move.
    """)
    return


@app.cell
def _(W, df, mo, theme):
    nav_chart = W(series_data=[W.candlestick(df), W.volume(df)], chart_options=theme, height=350)
    mo.ui.anywidget(nav_chart)
    return (nav_chart,)


@app.cell
def _(mo, nav_chart):
    bar_count = len(nav_chart.series_data[0]["data"])

    def show_last(n):
        nav_chart.logical_range = {"from": bar_count - n, "to": bar_count - 1}

    # Buttons must be assigned to variables for marimo to run their on_click
    show_all_button = mo.ui.button(label="Show all", on_click=lambda _: nav_chart.show_all())
    last_30_button = mo.ui.button(label="Last 30 bars", on_click=lambda _: show_last(30))
    back_30_button = mo.ui.button(label="Back 30 bars", on_click=lambda _: nav_chart.scroll_to_position(-30, animated=True))
    latest_button = mo.ui.button(label="Latest bar", on_click=lambda _: nav_chart.scroll_to_real_time())
    mo.hstack([show_all_button, last_30_button, back_30_button, latest_button], justify="start", gap=0.5)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## 12. Crosshair styling

    `W.crosshair(mode=, color=, width=, style=, labels=, vert_line=, horz_line=)`
    returns `{"crosshair": {...}}` for `chart_options`:

    - `mode`: `"normal"` follows the mouse, `"magnet"` snaps to the close,
      `"magnet_ohlc"` snaps to the nearest open, high, low or close, and
      `"hidden"` turns the crosshair off.
    - `color`, `width` (pixels) and `style` (`"solid"`, `"dotted"`, `"dashed"`,
      `"large_dashed"`, `"sparse_dotted"`) style both lines; `labels=False`
      hides their labels on the axes.
    - `vert_line=` / `horz_line=` override one line, e.g.
      `vert_line={"visible": False}` or `horz_line={"label_background_color": "#2962FF"}`.
    """)
    return


@app.cell
def _(mo):
    crosshair_style_mode = mo.ui.dropdown(
        options=["normal", "magnet", "magnet_ohlc", "hidden"], value="magnet_ohlc", label="Mode"
    )
    crosshair_line_style = mo.ui.dropdown(
        options=["solid", "dotted", "dashed", "large_dashed", "sparse_dotted"], value="dotted", label="Line style"
    )
    crosshair_color = mo.ui.text(value="#FF6D00", label="Color")
    crosshair_vertical = mo.ui.checkbox(value=True, label="Vertical line")
    crosshair_labels = mo.ui.checkbox(value=True, label="Axis labels")
    mo.hstack(
        [crosshair_style_mode, crosshair_line_style, crosshair_color, crosshair_vertical, crosshair_labels],
        justify="start", gap=1, wrap=True,
    )
    return crosshair_color, crosshair_labels, crosshair_line_style, crosshair_style_mode, crosshair_vertical


@app.cell
def _(
    W,
    crosshair_color,
    crosshair_labels,
    crosshair_line_style,
    crosshair_style_mode,
    crosshair_vertical,
    df,
    mo,
    theme,
):
    mo.ui.anywidget(
        W(
            series_data=[W.candlestick(df.tail(80))],
            chart_options=W.merge_options(
                theme,
                W.crosshair(
                    mode=crosshair_style_mode.value,
                    color=crosshair_color.value,
                    width=1,
                    style=crosshair_line_style.value,
                    labels=crosshair_labels.value,
                    vert_line={"visible": crosshair_vertical.value},
                    horz_line={"label_background_color": crosshair_color.value},
                ),
            ),
            height=350,
        )
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## 13. Number and date formatting

    Lightweight Charts formats prices and dates with JavaScript functions,
    which can't be sent from Python. Instead, describe the format and the
    chart builds the function with the browser's
    [Intl](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Intl)
    formatters:

    - `W.number_format(locale=None, min_move=None, **options)` takes
      [Intl.NumberFormat options](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Intl/NumberFormat/NumberFormat#options),
      e.g. `style="currency", currency="EUR"` or `notation="compact"`.
    - `W.date_format(locale=None, **options)` takes
      [Intl.DateTimeFormat options](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Intl/DateTimeFormat/DateTimeFormat#options),
      e.g. `weekday="short", day="numeric", month="short"`.

    Use them in `W.localization(locale=, date_format=, price_formatter=, time_formatter=, tick_formatters=)`,
    which returns `chart_options`:

    - `locale` alone (e.g. `"de-DE"`) switches the time axis to German month
      names. Prices keep their default format.
    - `price_formatter` formats every price axis on the chart, in every pane
      (an RSI pane would also show `€`), plus the crosshair label and legend.
      It suits single-pane charts.
    - `time_formatter` formats the time label under the crosshair.
    - `tick_formatters` formats the time-axis labels, per kind of tick:
      `{"year": ..., "month": ..., "day": ..., "time": ..., "time_with_seconds": ...}`.
      Kinds left out keep the built-in labels.

    For **one series only**, pass the number format as its price format:
    `W.candlestick(df, price_format=W.number_format(style="currency", currency="EUR"))`.
    That's what the example below does, so the volume keeps its short format
    (`14.5M`).
    """)
    return


@app.cell
def _(mo):
    format_locale = mo.ui.dropdown(
        options={"English (US)": ("en-US", "USD"), "German": ("de-DE", "EUR"), "Japanese": ("ja-JP", "JPY"),
                 "French": ("fr-FR", "EUR")},
        value="German",
        label="Locale",
    )
    format_currency = mo.ui.checkbox(value=True, label="Prices as currency")
    format_dates = mo.ui.checkbox(value=True, label="Long crosshair date")
    mo.hstack([format_locale, format_currency, format_dates], justify="start", gap=1)
    return format_currency, format_dates, format_locale


@app.cell
def _(W, df, format_currency, format_dates, format_locale, mo, theme):
    locale, currency = format_locale.value
    mo.ui.anywidget(
        W(
            series_data=[
                W.candlestick(
                    df, price_format=W.number_format(style="currency", currency=currency) if format_currency.value else None
                ),
                W.volume(df),
            ],
            chart_options=W.merge_options(
                theme,
                W.localization(
                    locale=locale,
                    time_formatter=(
                        W.date_format(weekday="long", day="numeric", month="long", year="numeric")
                        if format_dates.value else None
                    ),
                    tick_formatters={"month": W.date_format(month="long")},
                ),
            ),
            height=400,
        )
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## 14. Live data

    `chart.update(point, series=0)` adds a new bar, or replaces the latest one,
    without redrawing the chart: the view, zoom and hidden series stay as they
    are. A point with the same time as the latest bar replaces it (a price
    moving within the day); a later time adds a bar. Older times are ignored.

    - `point` is one data point, like the ones in `series_data`:
      `{"time", "open", "high", "low", "close"}` or `{"time", "value"}`. `time`
      can be a `date`/`datetime`; it's converted to the series' time format.
    - `series` is the index in `series_data`, so a volume series is updated
      with its own call.
    - `series_data` is updated in place, so Python always has the latest bar.

    Below, `mo.ui.refresh` reruns a cell on a timer, and each run moves the
    price a little, sometimes starting the next day's bar. Pick an interval to
    start streaming. Indicators (SMA, RSI, ...) aren't recomputed by `update()`;
    to keep them in step, update their series too, or redraw the chart.
    """)
    return


@app.cell
def _(mo):
    live_stream = mo.ui.refresh(options=["0.5s", "1s", "2s"], label="Stream a price every")
    live_stream
    return (live_stream,)


@app.cell
def _(W, df, mo, theme):
    live_chart = W(
        series_data=[W.candlestick(df.tail(60)), W.volume(df.tail(60))],
        chart_options=W.merge_options(theme, W.time_scale(right_offset=3)),
        height=350,
    )
    mo.ui.anywidget(live_chart)
    return (live_chart,)


@app.cell
def _(live_chart, live_stream):
    import datetime as _dt
    import random as _random

    live_stream  # rerun on every refresh tick

    _last = live_chart.series_data[0]["data"][-1]
    _last_volume = live_chart.series_data[1]["data"][-1]
    _price = round(_last["close"] * (1 + _random.gauss(0, 0.004)), 2)
    if _random.random() < 0.25:
        # Start the next weekday's bar
        _day = _dt.date.fromisoformat(_last["time"]) + _dt.timedelta(days=1)
        while _day.weekday() >= 5:
            _day += _dt.timedelta(days=1)
        _open, _high, _low, _volume = _last["close"], max(_last["close"], _price), min(_last["close"], _price), 0
    else:
        # Move the latest bar
        _day = _last["time"]
        _open, _high, _low, _volume = _last["open"], max(_last["high"], _price), min(_last["low"], _price), _last_volume["value"]
    _volume += _random.randint(200_000, 2_000_000)

    live_chart.update({"time": _day, "open": _open, "high": _high, "low": _low, "close": _price})
    live_chart.update(
        {"time": _day, "value": _volume, "color": "rgba(38,166,154,0.5)" if _price >= _open else "rgba(239,83,80,0.5)"},
        series=1,
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

    ## 15. Overlays on the price chart

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
    ## 16. Oscillators in panes

    Each oscillator helper puts its series in pane `1` (just below the price) by
    default. To stack several, give each a different `pane=`, as this example
    does. Panes below the price start at 40% of its height; drag the
    separators to resize them, or set `pane_heights=` on the widget: relative
    sizes from the top pane down, e.g. `pane_heights=[3, 1, 1]`.

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
    oscillator_height = mo.ui.slider(start=0.2, stop=1.0, step=0.1, value=0.4, label="Oscillator pane size", show_value=True)
    mo.hstack([oscillator_select, rsi_length, oscillator_height], justify="start", gap=2)
    return oscillator_height, oscillator_select, rsi_length


@app.cell
def _(W, df, mo, oscillator_height, oscillator_select, rsi_length, theme):
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
            pane_heights=[1] + [oscillator_height.value] * len(oscillator_select.value),
            height=350 + int(330 * oscillator_height.value) * len(oscillator_select.value),
        )
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## 17. Any pandas-ta indicator

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
