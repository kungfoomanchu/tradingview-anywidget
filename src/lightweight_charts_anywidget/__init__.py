"""TradingView Lightweight Charts anywidget for marimo notebooks."""

import calendar
import datetime
import math
import re
from pathlib import Path

import anywidget
import traitlets

_DIR = Path(__file__).parent

_TIME_COLUMNS = ("time", "date", "datetime", "timestamp")

UP_COLOR = "#26a69a"
DOWN_COLOR = "#ef5350"


# ---------------------------------------------------------------------------
# DataFrame helpers (work with both pandas and polars, no hard dependency)
# ---------------------------------------------------------------------------


def _find_column(df, name):
    """Return the actual column name matching `name` (exact match first, then case-insensitive)."""
    columns = [str(c) for c in df.columns]
    if name in columns:
        return name
    for c in columns:
        if c.lower() == name.lower():
            return c
    raise KeyError(f"Column {name!r} not found. Available columns: {columns}")


def _column_values(df, name):
    """Return a column as a list of floats, with None for NaN/Inf/missing values."""
    return [_safe_float(v) for v in df[_find_column(df, name)].to_list()]


def _safe_float(v):
    """Convert to float, returning None if missing, NaN or Inf."""
    if v is None:
        return None
    f = float(v)
    if math.isnan(f) or math.isinf(f):
        return None
    return f


def _is_missing(v):
    return v is None or v != v  # NaN and NaT are not equal to themselves


def _to_unix_seconds(dt):
    """Datetime -> UTC seconds, keeping the wall-clock time (timezone info is dropped).

    Lightweight Charts displays all timestamps as UTC, so dropping the timezone makes
    a 09:30 New York bar show as 09:30 on the axis.
    """
    return calendar.timegm(dt.replace(tzinfo=None).timetuple())


def _convert_times(values):
    """Convert a column of dates/datetimes into Lightweight Charts times.

    The whole column gets one format, as required by Lightweight Charts:
    - all dates at midnight -> "YYYY-MM-DD" strings (daily or slower data)
    - any time-of-day       -> unix seconds (intraday data)
    Strings and numbers are passed through unchanged. Missing values become None.
    """
    present = [v for v in values if not _is_missing(v)]
    if not present or not all(isinstance(v, datetime.date) for v in present):
        return [None if _is_missing(v) else v for v in values]
    intraday = any(
        isinstance(v, datetime.datetime) and v.time() != datetime.time() for v in present
    )
    if intraday:
        return [None if _is_missing(v) else _to_unix_seconds(v) for v in values]
    return [None if _is_missing(v) else v.strftime("%Y-%m-%d") for v in values]


def _point_time(value, data):
    """Convert one time to the format already used by `data` (date string or unix seconds)."""
    if not isinstance(value, datetime.date):
        return value
    if data and isinstance(data[-1]["time"], str):
        return value.strftime("%Y-%m-%d")
    if data or (isinstance(value, datetime.datetime) and value.time() != datetime.time()):
        if not isinstance(value, datetime.datetime):
            value = datetime.datetime.combine(value, datetime.time())
        return _to_unix_seconds(value)
    return value.strftime("%Y-%m-%d")


def _time_values(df, time_column="date"):
    """Return the time of each row, from `time_column`, a common time column, or the index."""
    for candidate in (time_column, *_TIME_COLUMNS):
        try:
            return _convert_times(df[_find_column(df, candidate)].to_list())
        except KeyError:
            continue
    index = getattr(df, "index", None)  # pandas only; polars has no index
    if index is not None and len(index) and isinstance(index[0], datetime.date):
        return _convert_times(index.to_list())
    raise KeyError(
        f"No time column found. Looked for {time_column!r} and {list(_TIME_COLUMNS)} "
        f"(case-insensitive) and a datetime index. Pass time_column=... to choose one."
    )


def _value_points(times, values, gaps=False):
    """Zip times and values into [{time, value}], skipping rows with a missing time or value.

    With gaps=True, rows with a missing value become whitespace points ({time} only),
    which leave a gap in the series instead of joining its neighbours.
    """
    return [
        {"time": t, "value": v} if v is not None else {"time": t}
        for t, v in zip(times, values)
        if t is not None and (gaps or v is not None)
    ]


def _line_points(df, column, time_column, gaps=False):
    return _value_points(_time_values(df, time_column), _column_values(df, column), gaps)


def _ohlc_points(df, time_column, gaps=False):
    """[{time, open, high, low, close}], skipping rows with any missing value (or, with
    gaps=True, keeping them as whitespace points that leave an empty slot)."""
    times = _time_values(df, time_column)
    ohlc = [_column_values(df, k) for k in ("open", "high", "low", "close")]
    return [
        {"time": t, "open": o, "high": h, "low": l, "close": c} if None not in (o, h, l, c) else {"time": t}
        for t, o, h, l, c in zip(times, *ohlc)
        if t is not None and (gaps or None not in (o, h, l, c))
    ]


def _camel(name):
    """snake_case -> camelCase ("line_style" -> "lineStyle"); camelCase names are unchanged."""
    first, *rest = name.split("_")
    return first + "".join(part[:1].upper() + part[1:] for part in rest)


# Option values that can be given by name instead of Lightweight Charts' enum numbers
_ENUMS = {
    "lineStyle": {"solid": 0, "dotted": 1, "dashed": 2, "large_dashed": 3, "sparse_dotted": 4},
    "lineType": {"simple": 0, "steps": 1, "curved": 2},
    "lastPriceAnimation": {"disabled": 0, "continuous": 1, "on_data_update": 2},
    "mode": {"normal": 0, "log": 1, "logarithmic": 1, "percentage": 2, "indexed": 3, "indexed_to_100": 3},
}


def _enum_value(key, value):
    if isinstance(value, str) and key in _ENUMS:
        try:
            return _ENUMS[key][value.lower()]
        except KeyError:
            raise ValueError(f"Unknown {key} {value!r}. Use one of {list(_ENUMS[key])}") from None
    return value


def _options(options):
    """Convert user options to Lightweight Charts names: camelCase keys, enum names to numbers.

    `None` values are dropped, so helpers can default every option to None.
    """
    result = {}
    for key, value in options.items():
        if value is None:
            continue
        key = _camel(key)
        result[key] = _enum_value(key, value)
    return result


def _series(type_, data, defaults, options, **extra):
    """Build a series config dict, letting user `options` override `defaults`."""
    return {"type": type_, "data": data, "options": {**defaults, **_options(options)}, **extra}


# Options shared by indicator lines that shouldn't clutter the price axis
_QUIET = {"priceLineVisible": False, "lastValueVisible": False}


# ---------------------------------------------------------------------------
# pandas-ta helpers (optional dependency)
# ---------------------------------------------------------------------------


def _require_pandas_ta():
    """Lazily import pandas-ta, raising a clear error if missing."""
    try:
        import pandas_ta
    except ImportError:
        raise ImportError(
            "pandas-ta is required for pta_ indicator helpers. "
            "Install it with:  uv pip install pandas-ta"
        ) from None
    return pandas_ta


def _pta_input(df, time_column):
    """Prepare a DataFrame for pandas-ta.

    Returns (pandas_ta module, pandas DataFrame indexed by datetime, row times, OHLCV dict).
    A DatetimeIndex is required by some indicators (VWAP) and makes forward-shifted
    outputs (Ichimoku spans) carry real future dates.
    """
    import pandas as pd

    pta = _require_pandas_ta()
    if not isinstance(df, pd.DataFrame):
        if not hasattr(df, "to_dict"):
            raise TypeError(f"pta_ helpers need a pandas or polars DataFrame, got {type(df).__name__}")
        df = pd.DataFrame(df.to_dict(as_series=False))  # polars -> pandas without pyarrow

    times = _time_values(df, time_column)
    if not isinstance(df.index, pd.DatetimeIndex):
        for candidate in (time_column, *_TIME_COLUMNS):
            try:
                col = _find_column(df, candidate)
            except KeyError:
                continue
            df = df.set_index(pd.DatetimeIndex(df[col]))
            break

    ohlcv = {}
    for name in ("open", "high", "low", "close", "volume"):
        try:
            ohlcv[name] = df[_find_column(df, name)].astype(float)
        except KeyError:
            pass
    return pta, df, times, ohlcv


def _pta_check(result, name):
    if result is None:
        raise ValueError(
            f"pandas-ta {name} returned None - check the DataFrame has enough rows "
            "and the required OHLCV columns."
        )
    return result


def _pta_column(result, prefix):
    """Find a pandas-ta output column by prefix, e.g. "MACDh_" -> "MACDh_12_26_9"."""
    return next(c for c in result.columns if c.startswith(prefix))


def _pta_points(series, times):
    return _value_points(times, [_safe_float(v) for v in series])


# pandas-ta names histogram columns like MACDh_12_26_9, PPOh_12_26_9, ...
_HISTOGRAM_COLUMN = re.compile(r"^[A-Z]+h_")

# Indicators whose values are NOT on the price scale (oscillators/volume indicators).
# The generic W.pta() puts these in their own pane below the price chart.
_OSCILLATOR_INDICATORS = frozenset([
    # Momentum / oscillators
    "rsi", "stoch", "stochrsi", "cci", "mfi", "willr", "roc", "mom",
    "macd", "ppo", "dpo", "kst", "trix", "uo", "ao", "apo",
    "bop", "cfo", "cg", "cmo", "coppock", "er", "fisher", "inertia",
    "pgo", "psl", "qqe", "slope", "smi", "squeeze", "td_seq",
    # Trend (bounded 0-100)
    "adx", "aroon", "chop",
    # Volume-based (different magnitude from price)
    "obv", "ad", "adosc", "cmf", "efi", "eom", "kvo", "nvi",
    "pvi", "pvol", "pvr", "pvt", "vfi",
    # Volatility (different scale)
    "atr", "natr", "true_range",
])

_PALETTE = ["#2962FF", "#FF6D00", "#E040FB", "#00BCD4", "#76FF03"]


def _guide_line(price, color, title):
    """Dashed horizontal reference line, e.g. RSI overbought at 70."""
    return {"price": price, "color": color, "lineWidth": 1, "lineStyle": 2, "axisLabelVisible": True, "title": title}


class LightweightChartWidget(anywidget.AnyWidget):
    """TradingView Lightweight Charts widget.

    Attributes:
        series_data: List of series configs. Each is a dict with keys:
            - type: "Candlestick", "Line", "Area", "Bar", "Baseline", "Histogram"
            - data: list of data points (dicts with 'time' key)
            - options: dict of series-specific options (colors, title, etc.)
            - pane: optional pane index (0 = main price pane, 1+ = panes below it)
            - priceScale: optional price scale options for this series' scale
            - markers: optional list of markers for this series
            - price_lines: optional list of price lines for this series
        chart_options: Dict of chart-level options (layout, grid, crosshair, etc.)
        width: Chart width in pixels (0 = fill the container width)
        height: Chart height in pixels
        watermark: Watermark dict ({"text": ...} or W.image_watermark(...)), or a list of them
        pane_heights: Relative pane heights, e.g. [3, 1, 1] (empty = sub panes at 40% of the main pane)
        x_axis: "time" (default), "number" (any numeric x, e.g. option strikes) or
            "yield_curve" (x in months). Only read when the chart is first shown.
        sync_group: Charts with the same non-empty name share their crosshair and
            scrolling (in the browser, without a round trip to Python)
        fit_content: Whether to auto-fit content when data changes
        visible_range: Time range to display {from, to} - bidirectional
        logical_range: Bar-index range to display {from, to} - bidirectional
        crosshair_data: Current crosshair position (read from JS)
        clicked_data: Last clicked data point (read from JS)
        double_clicked_data: Last double-clicked data point (read from JS)
        visible_bars: First series' bars on screen {from, to, bars_before, bars_after} (read from JS)
        screenshot: PNG data: URI of the last take_screenshot() (read from JS)
    """

    _esm = _DIR / "chart.js"
    _css = _DIR / "chart.css"

    # --- Data & Series ---
    series_data = traitlets.List([]).tag(sync=True)

    # --- Chart Options ---
    chart_options = traitlets.Dict({}).tag(sync=True)
    width = traitlets.Int(0).tag(sync=True)
    height = traitlets.Int(400).tag(sync=True)

    # --- Overlays ---
    watermark = traitlets.Union([traitlets.Dict(), traitlets.List()], default_value={}).tag(sync=True)

    # --- Layout ---
    pane_heights = traitlets.List([]).tag(sync=True)
    x_axis = traitlets.Enum(["time", "number", "yield_curve"], default_value="time").tag(sync=True)
    sync_group = traitlets.Unicode("").tag(sync=True)

    # --- Navigation ---
    fit_content = traitlets.Bool(True).tag(sync=True)
    visible_range = traitlets.Dict({}).tag(sync=True)
    logical_range = traitlets.Dict({}).tag(sync=True)

    # --- Events (JS -> Python) ---
    crosshair_data = traitlets.Dict({}).tag(sync=True)
    clicked_data = traitlets.Dict({}).tag(sync=True)
    double_clicked_data = traitlets.Dict({}).tag(sync=True)
    visible_bars = traitlets.Dict({}).tag(sync=True)
    screenshot = traitlets.Unicode("").tag(sync=True)

    # ------------------------------------------------------------------
    # Navigation commands (sent to every view of the chart)
    # ------------------------------------------------------------------

    def scroll_to_real_time(self):
        """Scroll to the latest bar, keeping the current zoom."""
        self.send({"command": "scrollToRealTime"})

    def scroll_to_position(self, position, animated=False):
        """Scroll so the latest bar is `position` bars from the right edge.

        Positive values leave empty space on the right; negative values scroll back
        into history (e.g. -50 hides the last 50 bars off the right edge).
        """
        self.send({"command": "scrollToPosition", "position": position, "animated": animated})

    def show_all(self):
        """Zoom out so every bar fits on screen (Lightweight Charts' fitContent)."""
        self.send({"command": "fitContent"})

    def update(self, point, series=0):
        """Add or replace the latest bar of a series without redrawing the chart (live data).

        Args:
            point: One data point, e.g. {"time": ..., "open": ..., "high": ...,
                "low": ..., "close": ...} or {"time": ..., "value": ...}. `time` may be
                a date/datetime; it's converted to the series' time format.
            series: Index of the series in series_data.

        A point with the same time as the latest bar replaces it; a later time adds
        a new bar. Earlier times are ignored. series_data is updated in place too,
        so Python sees the new bar, without redrawing the chart.
        """
        data = self.series_data[series].setdefault("data", [])
        point = {**point, "time": _point_time(point["time"], data)}
        if data and point["time"] == data[-1]["time"]:
            data[-1] = point
        elif not data or point["time"] > data[-1]["time"]:
            data.append(point)
        else:
            return
        self.send({"command": "update", "series": series, "point": point})

    def set_crosshair(self, time, series=0):
        """Show the crosshair on the bar at `time` of a series, as if the mouse were there.

        `time` may be a date/datetime (converted like update()). If the series has no
        bar at that time, the crosshair is hidden. Synced charts follow it too.
        """
        data = self.series_data[series].get("data", [])
        self.send({"command": "setCrosshair", "series": series, "time": _point_time(time, data)})

    def clear_crosshair(self):
        """Hide a crosshair shown with set_crosshair()."""
        self.send({"command": "clearCrosshair"})

    # ------------------------------------------------------------------
    # Screenshots
    # ------------------------------------------------------------------

    def take_screenshot(self, download=None):
        """Take a PNG screenshot of the chart (including legends and watermarks).

        The PNG arrives in the `screenshot` value (a data: URI) once the browser has
        drawn it, so read it in another cell or with screenshot_png(). Pass a file
        name as `download` to also save it through the browser's download dialog.
        """
        # Clear the last one, so an identical new screenshot still counts as a change
        self.screenshot = ""
        self.send({"command": "screenshot", "download": download})

    def screenshot_png(self):
        """The last screenshot as PNG bytes, or None if none was taken yet."""
        import base64

        if not self.screenshot:
            return None
        return base64.b64decode(self.screenshot.split(",", 1)[1])

    def save_screenshot(self, path):
        """Take a screenshot and write it to `path` when it arrives from the browser."""
        path = Path(path)

        def write(change):
            if change["new"]:
                path.write_bytes(self.screenshot_png())
                self.unobserve(write, names="screenshot")

        self.take_screenshot()
        self.observe(write, names="screenshot")

    # ------------------------------------------------------------------
    # Series builders
    #
    # All builders take a pandas or polars DataFrame. Column names are matched
    # case-insensitively. Times come from `time_column`, a common time column
    # (time/date/datetime/timestamp) or a datetime index. Rows with missing
    # values are skipped. Extra keyword arguments are passed through as
    # Lightweight Charts series options and override the defaults.
    # ------------------------------------------------------------------

    @staticmethod
    def candlestick(df, time_column="date", gaps=False, **options):
        """Candlestick series from open/high/low/close columns."""
        defaults = {
            "upColor": UP_COLOR,
            "downColor": DOWN_COLOR,
            "borderVisible": False,
            "wickUpColor": UP_COLOR,
            "wickDownColor": DOWN_COLOR,
        }
        return _series("Candlestick", _ohlc_points(df, time_column, gaps), defaults, options)

    @staticmethod
    def bar(df, time_column="date", gaps=False, **options):
        """OHLC bar series from open/high/low/close columns."""
        defaults = {"upColor": UP_COLOR, "downColor": DOWN_COLOR}
        return _series("Bar", _ohlc_points(df, time_column, gaps), defaults, options)

    @staticmethod
    def line(df, column="close", time_column="date", gaps=False, **options):
        """Line series from one column."""
        defaults = {"color": "#2962FF", "lineWidth": 2}
        return _series("Line", _line_points(df, column, time_column, gaps), defaults, options)

    @staticmethod
    def area(df, column="close", time_column="date", gaps=False, **options):
        """Area series from one column."""
        defaults = {
            "lineColor": "#2962FF",
            "topColor": "rgba(41, 98, 255, 0.56)",
            "bottomColor": "rgba(41, 98, 255, 0.04)",
        }
        return _series("Area", _line_points(df, column, time_column, gaps), defaults, options)

    @staticmethod
    def baseline(df, column="close", time_column="date", base_value=0, gaps=False, **options):
        """Baseline series: green above `base_value`, red below."""
        defaults = {
            "baseValue": {"type": "price", "price": base_value},
            "topLineColor": "rgba(38, 166, 154, 1)",
            "topFillColor1": "rgba(38, 166, 154, 0.28)",
            "topFillColor2": "rgba(38, 166, 154, 0.05)",
            "bottomLineColor": "rgba(239, 83, 80, 1)",
            "bottomFillColor1": "rgba(239, 83, 80, 0.05)",
            "bottomFillColor2": "rgba(239, 83, 80, 0.28)",
        }
        return _series("Baseline", _line_points(df, column, time_column, gaps), defaults, options)

    @staticmethod
    def histogram(df, column="close", time_column="date", gaps=False, **options):
        """Histogram series from one column."""
        defaults = {"color": UP_COLOR}
        return _series("Histogram", _line_points(df, column, time_column, gaps), defaults, options)

    @staticmethod
    def volume(df, time_column="date", up_color="rgba(38,166,154,0.5)", down_color="rgba(239,83,80,0.5)", **options):
        """Volume histogram, green/red by close vs open, overlaid on the bottom 20% of the price pane.

        For a separate volume pane instead, set `config["pane"] = 1` on the result.
        """
        times = _time_values(df, time_column)
        volumes = _column_values(df, "volume")
        opens = _column_values(df, "open")
        closes = _column_values(df, "close")
        data = [
            {"time": t, "value": v, "color": up_color if (c or 0) >= (o or 0) else down_color}
            for t, v, o, c in zip(times, volumes, opens, closes)
            if t is not None and v is not None
        ]
        defaults = {"priceFormat": {"type": "volume"}, "priceScaleId": "volume", "title": "Vol", **_QUIET}
        return _series(
            "Histogram", data, defaults, options,
            priceScale={"scaleMargins": {"top": 0.8, "bottom": 0}},
        )

    @staticmethod
    def sma(df, period=20, column="close", time_column="date", **options):
        """Simple Moving Average line. Pure Python - no extra dependencies needed."""
        times = _time_values(df, time_column)
        values = _column_values(df, column)
        data = []
        for i in range(period - 1, len(values)):
            window = values[i - period + 1 : i + 1]
            if times[i] is not None and None not in window:
                data.append({"time": times[i], "value": round(sum(window) / period, 4)})
        defaults = {"color": "#FF6D00", "lineWidth": 1, "title": f"SMA {period}", **_QUIET}
        return _series("Line", data, defaults, options)

    @staticmethod
    def ema(df, period=20, column="close", time_column="date", **options):
        """Exponential Moving Average line, seeded with the SMA of the first `period` values.

        Pure Python - no extra dependencies needed.
        """
        times = _time_values(df, time_column)
        values = _column_values(df, column)
        multiplier = 2 / (period + 1)
        data = []
        ema_val = None
        for i, v in enumerate(values):
            if v is None:
                continue
            if ema_val is None:
                window = values[max(i - period + 1, 0) : i + 1]
                if len(window) < period or None in window:
                    continue
                ema_val = sum(window) / period
            else:
                ema_val = (v - ema_val) * multiplier + ema_val
            if times[i] is not None:
                data.append({"time": times[i], "value": round(ema_val, 4)})
        defaults = {"color": "#2196F3", "lineWidth": 1, "title": f"EMA {period}", **_QUIET}
        return _series("Line", data, defaults, options)

    # ------------------------------------------------------------------
    # pandas-ta integration (optional dependency: uv pip install pandas-ta)
    # All methods prefixed with pta_ to keep autocomplete clean.
    # Oscillators are placed in pane 1, below the price chart; pass pane=2
    # etc. to stack several of them.
    # ------------------------------------------------------------------

    @staticmethod
    def pta(df, indicator_name, time_column="date", pane=None, **kwargs):
        """Compute ANY pandas-ta indicator and return series configs.

        Works with all 200+ pandas-ta indicators. Oscillators (RSI, MACD, ...) go in
        their own pane below the price chart; overlays (SMA, BBands, ...) stay on it.

        Args:
            df:             pandas or polars DataFrame with OHLCV data.
            indicator_name: Any pandas-ta indicator name, e.g. "rsi", "macd",
                            "bbands", "stoch", "adx". Case-insensitive.
            time_column:    Name of the date/time column (default "date").
            pane:           Pane index override (default: 1 for oscillators, 0 otherwise).
            **kwargs:       Passed directly to the pandas-ta function,
                            e.g. length=14, fast=12, slow=26.

        Returns:
            list[dict]: One or more series config dicts.

        Usage::

            series_data = [W.candlestick(df)] + W.pta(df, "bbands", length=20)
            series_data = [W.candlestick(df)] + W.pta(df, "rsi", length=14)
        """
        import pandas as pd

        pta, pdf, times, ohlcv = _pta_input(df, time_column)
        name = indicator_name.lower()
        fn = getattr(pta, name, None)
        if fn is None:
            raise ValueError(
                f"pandas-ta has no indicator {indicator_name!r}. "
                "Check spelling or run: import pandas_ta as pta; pta.indicators()"
            )

        # Pass all OHLCV columns as keyword args so multi-input indicators
        # (stoch, adx, ...) get the right inputs
        result = _pta_check(fn(**{**ohlcv, **kwargs}), indicator_name)
        if isinstance(result, tuple):  # e.g. ichimoku returns (values, forward spans)
            result = result[0]
        if isinstance(result, pd.Series):
            result = result.to_frame()

        if pane is None:
            pane = 1 if name in _OSCILLATOR_INDICATORS else 0

        # Overlays can include non-price columns (bbands bandwidth, supertrend direction);
        # these go in their own pane so they don't squash the price chart
        prices = [v for k in ("low", "high") if k in ohlcv for v in ohlcv[k].tolist() if v == v]

        def looks_like_price(data):
            if not prices:
                return True
            median = sorted(p["value"] for p in data)[len(data) // 2]
            return min(prices) * 0.5 < median < max(prices) * 2

        configs = []
        for i, col in enumerate(result.columns):
            data = _pta_points(result[col], times)
            if not data:
                continue
            col_pane = pane if pane or looks_like_price(data) else 1
            if _HISTOGRAM_COLUMN.match(str(col)):
                config = _series("Histogram", data, {"color": UP_COLOR, **_QUIET}, {})
            else:
                opts = {
                    "color": _PALETTE[i % len(_PALETTE)],
                    "lineWidth": 1 if len(result.columns) > 1 else 2,
                    "title": str(col),
                    "priceLineVisible": False,
                    "lastValueVisible": i == 0,
                }
                config = _series("Line", data, opts, {})
            if col_pane:
                config["pane"] = col_pane
            configs.append(config)
        return configs

    @staticmethod
    def pta_rsi(df, length=14, time_column="date", pane=1, **options):
        """RSI (Relative Strength Index) in its own pane, with overbought (70) / oversold (30) lines."""
        pta, _, times, ohlcv = _pta_input(df, time_column)
        result = _pta_check(pta.rsi(ohlcv["close"], length=length), "RSI")
        defaults = {"color": "#7B1FA2", "lineWidth": 2, "title": f"RSI {length}", "priceLineVisible": False}
        return _series(
            "Line", _pta_points(result, times), defaults, options,
            pane=pane,
            price_lines=[
                _guide_line(70, "rgba(239,83,80,0.5)", "OB"),
                _guide_line(30, "rgba(38,166,154,0.5)", "OS"),
            ],
        )

    @staticmethod
    def pta_macd(df, fast=12, slow=26, signal=9, time_column="date", pane=1):
        """MACD in its own pane: green/red histogram + MACD line + signal line.

        Returns list[dict] with 3 series configs.
        """
        pta, _, times, ohlcv = _pta_input(df, time_column)
        result = _pta_check(pta.macd(ohlcv["close"], fast=fast, slow=slow, signal=signal), "MACD")

        hist = _pta_points(result[_pta_column(result, "MACDh_")], times)
        for point in hist:
            point["color"] = UP_COLOR if point["value"] >= 0 else DOWN_COLOR

        return [
            _series("Histogram", hist, _QUIET, {}, pane=pane),
            _series(
                "Line", _pta_points(result[_pta_column(result, "MACD_")], times),
                {"color": "#2962FF", "lineWidth": 2, "title": "MACD", "priceLineVisible": False}, {},
                pane=pane,
            ),
            _series(
                "Line", _pta_points(result[_pta_column(result, "MACDs_")], times),
                {"color": "#FF6D00", "lineWidth": 1, "title": "Signal", **_QUIET}, {},
                pane=pane,
            ),
        ]

    @staticmethod
    def pta_bbands(df, length=20, std=2.0, column="close", time_column="date"):
        """Bollinger Bands (upper/middle/lower) overlaid on the price chart.

        Returns list[dict] with 3 series configs.
        """
        pta, pdf, times, _ = _pta_input(df, time_column)
        result = _pta_check(pta.bbands(pdf[_find_column(pdf, column)].astype(float), length=length, std=std), "BBands")
        band = {"color": "rgba(33, 150, 243, 0.6)", "lineWidth": 1, "lineStyle": 2, **_QUIET}
        return [
            _series("Line", _pta_points(result[_pta_column(result, "BBU_")], times), band, {}),
            _series(
                "Line", _pta_points(result[_pta_column(result, "BBM_")], times),
                {"color": "rgba(33, 150, 243, 1.0)", "lineWidth": 1, "title": f"BB {length}", **_QUIET}, {},
            ),
            _series("Line", _pta_points(result[_pta_column(result, "BBL_")], times), band, {}),
        ]

    @staticmethod
    def pta_stoch(df, k=14, d=3, smooth_k=3, time_column="date", pane=1):
        """Stochastic Oscillator (%K and %D) in its own pane, with overbought (80) / oversold (20) lines.

        Returns list[dict] with 2 series configs.
        """
        pta, _, times, ohlcv = _pta_input(df, time_column)
        result = _pta_check(
            pta.stoch(ohlcv["high"], ohlcv["low"], ohlcv["close"], k=k, d=d, smooth_k=smooth_k), "Stochastic"
        )
        return [
            _series(
                "Line", _pta_points(result[_pta_column(result, "STOCHk_")], times),
                {"color": "#2962FF", "lineWidth": 2, "title": "%K", "priceLineVisible": False}, {},
                pane=pane,
                price_lines=[
                    _guide_line(80, "rgba(239,83,80,0.4)", "OB"),
                    _guide_line(20, "rgba(38,166,154,0.4)", "OS"),
                ],
            ),
            _series(
                "Line", _pta_points(result[_pta_column(result, "STOCHd_")], times),
                {"color": "#FF6D00", "lineWidth": 1, "title": "%D", **_QUIET}, {},
                pane=pane,
            ),
        ]

    @staticmethod
    def pta_atr(df, length=14, time_column="date", pane=1, **options):
        """Average True Range in its own pane."""
        pta, _, times, ohlcv = _pta_input(df, time_column)
        result = _pta_check(pta.atr(ohlcv["high"], ohlcv["low"], ohlcv["close"], length=length), "ATR")
        defaults = {"color": "#F57F17", "lineWidth": 2, "title": f"ATR {length}", "priceLineVisible": False}
        return _series("Line", _pta_points(result, times), defaults, options, pane=pane)

    @staticmethod
    def pta_adx(df, length=14, time_column="date", pane=1, **options):
        """Average Directional Index in its own pane, with a trend threshold line at 25."""
        pta, _, times, ohlcv = _pta_input(df, time_column)
        result = _pta_check(pta.adx(ohlcv["high"], ohlcv["low"], ohlcv["close"], length=length), "ADX")
        defaults = {"color": "#00BCD4", "lineWidth": 2, "title": f"ADX {length}", "priceLineVisible": False}
        return _series(
            "Line", _pta_points(result[_pta_column(result, "ADX_")], times), defaults, options,
            pane=pane,
            price_lines=[_guide_line(25, "rgba(0,188,212,0.4)", "Trend")],
        )

    @staticmethod
    def pta_obv(df, time_column="date", pane=1, **options):
        """On-Balance Volume in its own pane."""
        pta, _, times, ohlcv = _pta_input(df, time_column)
        result = _pta_check(pta.obv(ohlcv["close"], ohlcv["volume"]), "OBV")
        defaults = {
            "color": UP_COLOR, "lineWidth": 2, "title": "OBV",
            "priceFormat": {"type": "volume"}, "priceLineVisible": False,
        }
        return _series("Line", _pta_points(result, times), defaults, options, pane=pane)

    @staticmethod
    def pta_supertrend(df, length=7, multiplier=3.0, time_column="date", **options):
        """Supertrend overlaid on the price chart, green in uptrends and red in downtrends."""
        pta, _, times, ohlcv = _pta_input(df, time_column)
        result = _pta_check(
            pta.supertrend(ohlcv["high"], ohlcv["low"], ohlcv["close"], length=length, multiplier=multiplier),
            "Supertrend",
        )
        values = [_safe_float(v) for v in result[_pta_column(result, "SUPERT_")]]
        directions = [_safe_float(v) for v in result[_pta_column(result, "SUPERTd_")]]
        data = [
            {"time": t, "value": v, "color": UP_COLOR if d > 0 else DOWN_COLOR}
            for t, v, d in zip(times, values, directions)
            if t is not None and v is not None and d is not None
        ]
        defaults = {"lineWidth": 2, "title": "Supertrend", "priceLineVisible": False}
        return _series("Line", data, defaults, options)

    @staticmethod
    def pta_vwap(df, anchor="D", time_column="date", **options):
        """Volume Weighted Average Price overlaid on the price chart.

        `anchor` is the pandas period VWAP resets on: "D" (daily, for intraday data),
        "W" (weekly) or "M" (monthly, useful for daily bars - a daily VWAP on daily
        bars is just the typical price).
        """
        pta, _, times, ohlcv = _pta_input(df, time_column)
        if "volume" not in ohlcv:
            raise ValueError("VWAP requires a 'volume' column in the DataFrame.")
        result = _pta_check(
            pta.vwap(ohlcv["high"], ohlcv["low"], ohlcv["close"], ohlcv["volume"], anchor=anchor), "VWAP"
        )
        defaults = {"color": "#E91E63", "lineWidth": 2, "title": f"VWAP {anchor}", "priceLineVisible": False}
        return _series("Line", _pta_points(result, times), defaults, options)

    @staticmethod
    def pta_ichimoku(df, tenkan=9, kijun=26, senkou=52, time_column="date"):
        """Ichimoku Cloud overlaid on the price chart.

        Returns list[dict] with 5 series configs:
        Tenkan-sen, Kijun-sen, Chikou Span, Senkou Span A, Senkou Span B.
        The two Senkou spans extend `kijun` bars past the last candle.
        """
        import pandas as pd

        pta, _, times, ohlcv = _pta_input(df, time_column)
        ich_df, spans_df = _pta_check(
            pta.ichimoku(ohlcv["high"], ohlcv["low"], ohlcv["close"], tenkan=tenkan, kijun=kijun, senkou=senkou),
            "Ichimoku",
        )

        def line(series, times, color, title):
            return _series("Line", _pta_points(series, times), {"color": color, "lineWidth": 1, "title": title, **_QUIET}, {})

        # Senkou spans: in-range values followed by the forward projection
        span_a = pd.concat([ich_df[_pta_column(ich_df, "ISA_")], spans_df[_pta_column(spans_df, "ISA_")]])
        span_b = pd.concat([ich_df[_pta_column(ich_df, "ISB_")], spans_df[_pta_column(spans_df, "ISB_")]])
        span_times = _convert_times(span_a.index.to_list())

        return [
            line(ich_df[_pta_column(ich_df, "ITS_")], times, "#2962FF", "Tenkan"),
            line(ich_df[_pta_column(ich_df, "IKS_")], times, "#B71C1C", "Kijun"),
            line(ich_df[_pta_column(ich_df, "ICS_")], times, UP_COLOR, "Chikou"),
            line(span_a, span_times, "rgba(38,166,154,0.6)", "Span A"),
            line(span_b, span_times, "rgba(239,83,80,0.6)", "Span B"),
        ]

    # ------------------------------------------------------------------
    # Markers, price lines, themes
    # ------------------------------------------------------------------

    @staticmethod
    def marker(time, position="belowBar", shape="arrowUp", color="#2196F3", text="", size=1, id=None):
        """Create a single series marker dict.

        Args:
            time: Time of an existing data point in the series (e.g. "2024-01-15",
                or unix seconds for intraday data). Markers at other times are dropped.
            position: "belowBar", "aboveBar", or "inBar"
            shape: "arrowUp", "arrowDown", "circle", "square"
            color: Marker color
            text: Label text
            size: Marker size (1-4)
            id: Optional id, reported as `hovered_object_id` in crosshair/click
                events when the mouse is over the marker.
        """
        marker = {
            "time": time,
            "position": position,
            "shape": shape,
            "color": color,
            "text": text,
            "size": size,
        }
        if id is not None:
            marker["id"] = id
        return marker

    markers = marker  # backwards-compatible alias

    @staticmethod
    def price_line(price, color="#FF0000", line_width=1, line_style=2, title="", id=None):
        """Create a price line config dict.

        Args:
            price: Price value for the horizontal line
            color: Line color
            line_width: Width in pixels
            line_style: "solid", "dotted", "dashed", "large_dashed", "sparse_dotted"
                (or 0-4)
            title: Label text
            id: Optional id, reported as `hovered_object_id` in events when the
                mouse is over the line.
        """
        line = {
            "price": price,
            "color": color,
            "lineWidth": line_width,
            "lineStyle": _enum_value("lineStyle", line_style),
            "axisLabelVisible": True,
            "title": title,
        }
        if id is not None:
            line["id"] = id
        return line

    @staticmethod
    def dark_theme():
        """Return chart_options for a dark theme (TradingView's dark palette)."""
        return {
            "layout": {
                "background": {"type": "solid", "color": "#131722"},
                "textColor": "#d1d4dc",
                "panes": {"separatorColor": "#2a2e39"},
            },
            "grid": {
                "vertLines": {"color": "rgba(42, 46, 57, 0.6)"},
                "horzLines": {"color": "rgba(42, 46, 57, 0.6)"},
            },
            "rightPriceScale": {"borderColor": "#2a2e39"},
            "timeScale": {"borderColor": "#2a2e39"},
            "crosshair": {"mode": 0},
        }

    @staticmethod
    def light_theme():
        """Return chart_options for a light theme."""
        return {
            "layout": {
                "background": {"type": "solid", "color": "#ffffff"},
                "textColor": "#191919",
                "panes": {"separatorColor": "#e0e3eb"},
            },
            "grid": {
                "vertLines": {"color": "rgba(197, 203, 206, 0.5)"},
                "horzLines": {"color": "rgba(197, 203, 206, 0.5)"},
            },
            "rightPriceScale": {"borderColor": "#e0e3eb"},
            "timeScale": {"borderColor": "#e0e3eb"},
            "crosshair": {"mode": 0},
        }

    @staticmethod
    def theme(name):
        """Return dark_theme() for "dark", light_theme() otherwise.

        In marimo, follow the notebook theme with `W.theme(mo.app_meta().theme)`.
        """
        return LightweightChartWidget.dark_theme() if name == "dark" else LightweightChartWidget.light_theme()

    # ------------------------------------------------------------------
    # Scales, interaction and option merging
    # ------------------------------------------------------------------

    @staticmethod
    def time_scale(
        bar_spacing=None,
        right_offset=None,
        min_bar_spacing=None,
        time_visible=None,
        seconds_visible=None,
        fix_left_edge=None,
        fix_right_edge=None,
        visible=None,
        border_visible=None,
        **options,
    ):
        """chart_options for the horizontal time axis, as {"timeScale": {...}}.

        Args:
            bar_spacing: Pixels per bar, i.e. the initial zoom (library default 6).
            right_offset: Empty bars to leave right of the latest bar.
            min_bar_spacing: Smallest bar spacing zooming out can reach.
            time_visible: Show the time of day on the axis (on by default for intraday data).
            seconds_visible: Show seconds (on by default when the data has them).
            fix_left_edge / fix_right_edge: Stop scrolling past the first / latest bar.
            visible: Show the time axis.
            border_visible: Draw the border line above the axis.
            **options: Any other time scale option, in snake_case or camelCase.

        Options left as None keep their current value. Combine with a theme using
        W.merge_options(theme, W.time_scale(...)).
        """
        return {"timeScale": _options({
            "bar_spacing": bar_spacing,
            "right_offset": right_offset,
            "min_bar_spacing": min_bar_spacing,
            "time_visible": time_visible,
            "seconds_visible": seconds_visible,
            "fix_left_edge": fix_left_edge,
            "fix_right_edge": fix_right_edge,
            "visible": visible,
            "border_visible": border_visible,
            **options,
        })}

    @staticmethod
    def price_scale(
        mode=None,
        visible=None,
        border_visible=None,
        auto_scale=None,
        invert_scale=None,
        margins=None,
        **options,
    ):
        """Price scale options for a series' "priceScale" key (or chart_options["rightPriceScale"]).

        Args:
            mode: "normal", "log", "percentage" or "indexed" (to 100), or 0-3.
            visible: Show the axis. A series with priceScaleId="left" shows the left
                axis automatically unless this is False. Left/right axis visibility
                applies to every pane: Lightweight Charts lays the axes out chart-wide.
            border_visible: Draw the border line beside the axis.
            auto_scale: Fit the scale to the visible data.
            invert_scale: Flip the scale upside down.
            margins: (top, bottom) fractions of the pane kept empty, e.g. (0.8, 0)
                to keep a series in the bottom 20%.
            **options: Any other price scale option, in snake_case or camelCase.
        """
        if margins is not None:
            top, bottom = margins
            options["scale_margins"] = {"top": top, "bottom": bottom}
        return _options({
            "mode": mode,
            "visible": visible,
            "border_visible": border_visible,
            "auto_scale": auto_scale,
            "invert_scale": invert_scale,
            **options,
        })

    @staticmethod
    def interaction(scroll=True, zoom=True, mouse_wheel=True):
        """chart_options for how the mouse and touch move the chart.

        Args:
            scroll: Drag (and wheel) to scroll through time.
            zoom: Wheel, pinch and axis drag to zoom; double-click an axis to reset.
            mouse_wheel: Let the mouse wheel scroll/zoom the chart. False leaves the
                wheel to the page, so scrolling the notebook doesn't get stuck on the chart.
        """
        return {
            "handleScroll": {
                "mouseWheel": scroll and mouse_wheel,
                "pressedMouseMove": scroll,
                "horzTouchDrag": scroll,
                "vertTouchDrag": scroll,
            },
            "handleScale": {
                "mouseWheel": zoom and mouse_wheel,
                "pinch": zoom,
                "axisPressedMouseMove": zoom,
                "axisDoubleClickReset": zoom,
            },
        }

    @staticmethod
    def merge_options(*dicts):
        """Deep-merge chart_options dicts; later ones win, nested dicts are merged key by key.

        W.merge_options(theme, W.time_scale(bar_spacing=10)) keeps the theme's
        timeScale border color while adding the bar spacing.
        """
        merged = {}
        for d in dicts:
            for key, value in (d or {}).items():
                if isinstance(value, dict) and isinstance(merged.get(key), dict):
                    merged[key] = LightweightChartWidget.merge_options(merged[key], value)
                else:
                    merged[key] = value
        return merged

    @staticmethod
    def crosshair(mode=None, color=None, width=None, style=None, labels=None, vert_line=None, horz_line=None):
        """chart_options for the crosshair, as {"crosshair": {...}}.

        Args:
            mode: "normal" (follows the mouse), "magnet" (snaps to the close),
                "magnet_ohlc" (snaps to the nearest open/high/low/close) or "hidden".
            color, width, style: Both lines' color, width in pixels and line style
                ("solid", "dotted", "dashed", "large_dashed", "sparse_dotted").
            labels: Show the price and time labels on the axes.
            vert_line / horz_line: Options for one line only, overriding the above,
                e.g. {"visible": False} or {"label_background_color": "#333"}.
        """
        modes = {"normal": 0, "magnet": 1, "hidden": 2, "magnet_ohlc": 3}
        if isinstance(mode, str):
            if mode not in modes:
                raise ValueError(f"Unknown crosshair mode {mode!r}. Use one of {list(modes)}")
            mode = modes[mode]
        both = _options({"color": color, "width": width, "style": style, "label_visible": labels})
        if "style" in both:
            both["style"] = _enum_value("lineStyle", both["style"])
        result = _options({"mode": mode})
        for key, line in (("vertLine", vert_line), ("horzLine", horz_line)):
            line = _options(line or {})
            if "style" in line:
                line["style"] = _enum_value("lineStyle", line["style"])
            if both or line:
                result[key] = {**both, **line}
        return {"crosshair": result}

    @staticmethod
    def number_format(locale=None, min_move=None, **intl_options):
        """A price formatter built from JavaScript's Intl.NumberFormat options.

        Use as a series' price_format (W.line(df, price_format=W.number_format(...)))
        or in W.localization(price_formatter=...).

        Args:
            locale: e.g. "de-DE" (default: the chart's locale, else the browser's).
            min_move: Smallest price step of a series (default 0.01).
            **intl_options: Intl.NumberFormat options in snake_case or camelCase, e.g.
                style="currency", currency="EUR", maximum_fraction_digits=0,
                notation="compact".
        """
        spec = {"intl": "number", "options": _options(intl_options)}
        if locale:
            spec["locale"] = locale
        if min_move is not None:
            spec["minMove"] = min_move
        return spec

    @staticmethod
    def date_format(locale=None, **intl_options):
        """A date/time formatter built from JavaScript's Intl.DateTimeFormat options.

        Use in W.localization(time_formatter=..., tick_formatters=...).

        Args:
            locale: e.g. "en-GB" (default: the chart's locale, else the browser's).
            **intl_options: Intl.DateTimeFormat options in snake_case or camelCase, e.g.
                weekday="short", day="numeric", month="short", year="2-digit",
                hour="2-digit", minute="2-digit". Times are shown as given in the data
                (wall-clock time); pass time_zone="America/New_York" only if your
                times are real UTC.
        """
        spec = {"intl": "date", "options": _options(intl_options)}
        if locale:
            spec["locale"] = locale
        return spec

    @staticmethod
    def localization(locale=None, date_format=None, price_formatter=None, time_formatter=None, tick_formatters=None):
        """chart_options for number and date formatting.

        Args:
            locale: Locale for month names on the time axis and the default for
                W.number_format()/W.date_format(), e.g. "de-DE".
            date_format: Lightweight Charts date pattern for the crosshair label,
                e.g. "dd MMM 'yy" or "yyyy-MM-dd".
            price_formatter: W.number_format(...) for every price axis, in every pane
                (oscillators and volume too). For one series only, pass the format
                as that series' price_format instead.
            time_formatter: W.date_format(...) for the crosshair's time label.
            tick_formatters: W.date_format(...) per time-axis tick type, as a dict with
                keys "year", "month", "day", "time" and "time_with_seconds". Tick types
                left out use the built-in labels.
        """
        localization = _options({"locale": locale, "date_format": date_format})
        if price_formatter is not None:
            localization["priceFormatter"] = price_formatter
        if time_formatter is not None:
            localization["timeFormatter"] = time_formatter
        result = {"localization": localization} if localization else {}
        if tick_formatters:
            types = {"year", "month", "day", "time", "time_with_seconds"}
            unknown = set(tick_formatters) - types
            if unknown:
                raise ValueError(f"Unknown tick types {sorted(unknown)}. Use {sorted(types)}")
            result["timeScale"] = {"tickMarkFormatter": dict(tick_formatters)}
        return result

    @staticmethod
    def image_watermark(src, alpha=0.3, max_width=None, max_height=None, padding=0, pane=0):
        """An image watermark for the `watermark=` argument (combine several in a list).

        Args:
            src: An image URL, a data: URI, a local file path or raw image bytes.
                Local files and bytes are embedded in the notebook as a data: URI.
            alpha: Opacity from 0 to 1.
            max_width / max_height: Largest size in pixels (default: the image's own size,
                shrunk to fit the pane).
            padding: Minimum space in pixels between the image and the pane edges.
            pane: Pane to draw it in.
        """
        import base64
        import mimetypes

        if isinstance(src, (bytes, bytearray)):
            head = bytes(src[:100]).lstrip()
            mime = "image/svg+xml" if head.startswith((b"<svg", b"<?xml")) else (
                "image/jpeg" if head.startswith(b"\xff\xd8") else "image/png"
            )
            src = f"data:{mime};base64," + base64.b64encode(src).decode()
        elif not str(src).startswith(("http://", "https://", "data:", "//")):
            path = Path(src)
            if not path.is_file():
                raise FileNotFoundError(f"Image not found: {src}")
            mime = mimetypes.guess_type(path.name)[0] or "image/png"
            src = f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()
        return {
            "image": str(src),
            **_options({"alpha": alpha, "max_width": max_width, "max_height": max_height, "padding": padding}),
            "pane": pane,
        }

    @staticmethod
    def rows_in_range(df, time_range, time_column="date"):
        """Rows of `df` whose time is inside a {"from", "to"} range, e.g. the chart's visible_range.

        Works with pandas and polars. An empty range returns `df` unchanged.
        """
        if not time_range or time_range.get("from") is None or time_range.get("to") is None:
            return df
        start, end = time_range["from"], time_range["to"]
        mask = [t is not None and start <= t <= end for t in _time_values(df, time_column)]
        if hasattr(df, "filter") and not hasattr(df, "loc"):  # polars
            return df.filter(mask)
        return df[mask]
