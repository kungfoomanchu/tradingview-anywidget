"""TradingView Lightweight Charts anywidget for marimo notebooks."""

import datetime
import math
from pathlib import Path

import anywidget
import traitlets

_DIR = Path(__file__).parent


def _df_to_records(df):
    """Convert a pandas or polars DataFrame to a list of dicts."""
    # Polars
    if hasattr(df, "to_dicts"):
        records = df.to_dicts()
        for rec in records:
            for k, v in rec.items():
                if isinstance(v, (datetime.date, datetime.datetime)):
                    rec[k] = v.strftime("%Y-%m-%d")
        return records
    # Pandas
    if hasattr(df, "to_dict") and hasattr(df, "columns"):
        records = df.to_dict(orient="records")
        for rec in records:
            for k, v in rec.items():
                if hasattr(v, "isoformat"):
                    rec[k] = v.strftime("%Y-%m-%d")
        return records
    raise TypeError(f"Unsupported data type: {type(df)}")


def _ensure_time_key(records, time_column="date"):
    """Ensure each record has a 'time' key, renaming from time_column if needed."""
    if not records:
        return records
    if "time" in records[0]:
        return records
    # Build a priority list of candidate column names
    candidates = [time_column]
    for name in ("Date", "date", "datetime", "timestamp"):
        if name != time_column:
            candidates.append(name)
    out = []
    for rec in records:
        r = dict(rec)
        for candidate in candidates:
            if candidate in r:
                r["time"] = r.pop(candidate)
                break
        out.append(r)
    return out


def _normalize_ohlcv_keys(records):
    """Normalize OHLCV column names to lowercase (Open->open, etc.)."""
    mapping = {
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Volume": "volume",
        "Value": "value",
    }
    out = []
    for rec in records:
        r = {}
        for k, v in rec.items():
            r[mapping.get(k, k)] = v
        out.append(r)
    return out


def _safe_float(v):
    """Convert to float, returning None if NaN or Inf."""
    f = float(v)
    if math.isnan(f) or math.isinf(f):
        return None
    return f


# ---------------------------------------------------------------------------
# pandas-ta helpers (optional dependency)
# ---------------------------------------------------------------------------

def _require_pandas_ta():
    """Lazily import pandas-ta, raising a clear error if missing."""
    try:
        import pandas_ta as pta
        return pta
    except ImportError:
        raise ImportError(
            "pandas-ta is required for pta_ indicator helpers. "
            "Install it with:  pip install pandas-ta  (or uv pip install pandas-ta)"
        ) from None


def _ensure_pandas_df(df):
    """Ensure df is a pandas DataFrame (pandas-ta requires it)."""
    import pandas as pd
    if isinstance(df, pd.DataFrame):
        return df
    # Polars → pandas
    if hasattr(df, "to_pandas"):
        return df.to_pandas()
    raise TypeError(
        f"pta_ helpers require a pandas DataFrame, got {type(df).__name__}. "
        "Convert with df.to_pandas() if using polars."
    )


def _ohlcv_series(pdf):
    """Extract OHLCV pandas Series from a DataFrame (case-insensitive columns)."""
    import pandas as pd
    col_map = {}
    for c in pdf.columns:
        cl = c.lower()
        if cl in ("open", "high", "low", "close", "volume"):
            col_map[cl] = c
    return {k: pdf[v] for k, v in col_map.items()}


def _extract_times(pdf, time_column="date"):
    """Extract a list of time strings aligned to the DataFrame rows."""
    for candidate in (time_column, "Date", "date", "datetime", "timestamp", "time"):
        if candidate in pdf.columns:
            return [
                v.strftime("%Y-%m-%d") if hasattr(v, "strftime") else str(v)
                for v in pdf[candidate]
            ]
    # Fall back to index
    return [
        v.strftime("%Y-%m-%d") if hasattr(v, "strftime") else str(v)
        for v in pdf.index
    ]


def _ta_col_to_data(series_values, times):
    """Convert a pandas Series (aligned to times) to [{time, value}], dropping NaN."""
    data = []
    for i, val in enumerate(series_values):
        if i >= len(times):
            break
        v = _safe_float(val) if val is not None else None
        if v is None:
            continue
        data.append({"time": times[i], "value": v})
    return data


# Indicators whose values are NOT on the price scale (oscillators/volume indicators).
# The generic W.pta() uses this to auto-assign a separate priceScaleId.
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


class LightweightChartWidget(anywidget.AnyWidget):
    """TradingView Lightweight Charts widget.

    Attributes:
        series_data: List of series configs. Each is a dict with keys:
            - type: "Candlestick", "Line", "Area", "Bar", "Baseline", "Histogram"
            - data: list of data points (dicts with 'time' key)
            - options: dict of series-specific options (colors, etc.)
            - markers: optional list of markers for this series
            - price_lines: optional list of price lines for this series
        chart_options: Dict of chart-level options (layout, grid, crosshair, etc.)
        width: Chart width in pixels (0 = auto-size to container)
        height: Chart height in pixels
        watermark: Watermark configuration dict
        fit_content: Whether to auto-fit content when data changes
        visible_range: Time range to display {from, to} - bidirectional
        crosshair_data: Current crosshair position (read from JS)
        clicked_data: Last clicked data point (read from JS)
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
    watermark = traitlets.Dict({}).tag(sync=True)

    # --- Navigation ---
    fit_content = traitlets.Bool(True).tag(sync=True)
    visible_range = traitlets.Dict({}).tag(sync=True)

    # --- Events (JS -> Python) ---
    crosshair_data = traitlets.Dict({}).tag(sync=True)
    clicked_data = traitlets.Dict({}).tag(sync=True)

    # --- Helpers for building series configs ---

    @staticmethod
    def candlestick(df, time_column="date", **options):
        """Create a candlestick series config from a DataFrame.

        Expects columns: open, high, low, close (case-insensitive).
        """
        records = _df_to_records(df)
        records = _normalize_ohlcv_keys(records)
        records = _ensure_time_key(records, time_column)
        data = []
        for r in records:
            d = {"time": r["time"]}
            skip = False
            for k in ("open", "high", "low", "close"):
                if k in r:
                    v = _safe_float(r[k])
                    if v is None:
                        skip = True
                        break
                    d[k] = v
            if not skip:
                data.append(d)
        defaults = {
            "upColor": "#26a69a",
            "downColor": "#ef5350",
            "borderVisible": False,
            "wickUpColor": "#26a69a",
            "wickDownColor": "#ef5350",
        }
        defaults.update(options)
        return {"type": "Candlestick", "data": data, "options": defaults}

    @staticmethod
    def line(df, column="close", time_column="date", **options):
        """Create a line series config from a DataFrame column."""
        records = _df_to_records(df)
        records = _normalize_ohlcv_keys(records)
        records = _ensure_time_key(records, time_column)
        col = column.lower()
        data = [
            {"time": r["time"], "value": v}
            for r in records
            if col in r and (v := _safe_float(r[col])) is not None
        ]
        defaults = {"color": "#2962FF", "lineWidth": 2}
        defaults.update(options)
        return {"type": "Line", "data": data, "options": defaults}

    @staticmethod
    def area(df, column="close", time_column="date", **options):
        """Create an area series config from a DataFrame column."""
        records = _df_to_records(df)
        records = _normalize_ohlcv_keys(records)
        records = _ensure_time_key(records, time_column)
        col = column.lower()
        data = [
            {"time": r["time"], "value": v}
            for r in records
            if col in r and (v := _safe_float(r[col])) is not None
        ]
        defaults = {
            "lineColor": "#2962FF",
            "topColor": "rgba(41, 98, 255, 0.56)",
            "bottomColor": "rgba(41, 98, 255, 0.04)",
        }
        defaults.update(options)
        return {"type": "Area", "data": data, "options": defaults}

    @staticmethod
    def bar(df, time_column="date", **options):
        """Create a bar series config from a DataFrame (OHLC data)."""
        records = _df_to_records(df)
        records = _normalize_ohlcv_keys(records)
        records = _ensure_time_key(records, time_column)
        data = []
        for r in records:
            d = {"time": r["time"]}
            skip = False
            for k in ("open", "high", "low", "close"):
                if k in r:
                    v = _safe_float(r[k])
                    if v is None:
                        skip = True
                        break
                    d[k] = v
            if not skip:
                data.append(d)
        defaults = {"upColor": "#26a69a", "downColor": "#ef5350"}
        defaults.update(options)
        return {"type": "Bar", "data": data, "options": defaults}

    @staticmethod
    def baseline(df, column="close", time_column="date", base_value=0, **options):
        """Create a baseline series config from a DataFrame column."""
        records = _df_to_records(df)
        records = _normalize_ohlcv_keys(records)
        records = _ensure_time_key(records, time_column)
        col = column.lower()
        data = [
            {"time": r["time"], "value": v}
            for r in records
            if col in r and (v := _safe_float(r[col])) is not None
        ]
        defaults = {
            "baseValue": {"type": "price", "price": base_value},
            "topLineColor": "rgba(38, 166, 154, 1)",
            "topFillColor1": "rgba(38, 166, 154, 0.28)",
            "topFillColor2": "rgba(38, 166, 154, 0.05)",
            "bottomLineColor": "rgba(239, 83, 80, 1)",
            "bottomFillColor1": "rgba(239, 83, 80, 0.05)",
            "bottomFillColor2": "rgba(239, 83, 80, 0.28)",
        }
        defaults.update(options)
        return {"type": "Baseline", "data": data, "options": defaults}

    @staticmethod
    def histogram(df, column="close", time_column="date", **options):
        """Create a histogram series config from a DataFrame column."""
        records = _df_to_records(df)
        records = _normalize_ohlcv_keys(records)
        records = _ensure_time_key(records, time_column)
        col = column.lower()
        data = [
            {"time": r["time"], "value": v}
            for r in records
            if col in r and (v := _safe_float(r[col])) is not None
        ]
        defaults = {"color": "#26a69a"}
        defaults.update(options)
        return {"type": "Histogram", "data": data, "options": defaults}

    @staticmethod
    def volume(df, time_column="date", up_color="rgba(38,166,154,0.5)", down_color="rgba(239,83,80,0.5)", **options):
        """Create a volume histogram series from OHLCV DataFrame.

        Colors bars green/red based on close vs open.
        Renders on a separate overlay price scale.
        """
        records = _df_to_records(df)
        records = _normalize_ohlcv_keys(records)
        records = _ensure_time_key(records, time_column)
        data = []
        for r in records:
            if "volume" not in r:
                continue
            vol = _safe_float(r["volume"])
            if vol is None:
                continue
            color = up_color if float(r.get("close", 0)) >= float(r.get("open", 0)) else down_color
            data.append({"time": r["time"], "value": vol, "color": color})
        defaults = {
            "priceFormat": {"type": "volume"},
            "priceScaleId": "volume",
        }
        defaults.update(options)
        series_config = {"type": "Histogram", "data": data, "options": defaults}
        # Volume uses a separate price scale at the bottom
        series_config["priceScale"] = {
            "scaleMargins": {"top": 0.8, "bottom": 0},
        }
        return series_config

    @staticmethod
    def sma(df, period=20, column="close", time_column="date", **options):
        """Create a Simple Moving Average line series from a DataFrame.

        Computes SMA in pure Python - no extra dependencies needed.
        """
        records = _df_to_records(df)
        records = _normalize_ohlcv_keys(records)
        records = _ensure_time_key(records, time_column)
        col = column.lower()
        values = [_safe_float(r[col]) for r in records if col in r]
        times = [r["time"] for r in records if col in r]
        data = []
        for i in range(len(values)):
            if i < period - 1:
                continue
            window = values[i - period + 1 : i + 1]
            if any(v is None for v in window):
                continue
            avg = sum(window) / period
            data.append({"time": times[i], "value": round(avg, 4)})
        defaults = {
            "color": "#FF6D00",
            "lineWidth": 1,
            "priceLineVisible": False,
            "lastValueVisible": False,
        }
        defaults.update(options)
        return {"type": "Line", "data": data, "options": defaults}

    @staticmethod
    def ema(df, period=20, column="close", time_column="date", **options):
        """Create an Exponential Moving Average line series from a DataFrame.

        Computes EMA in pure Python - no extra dependencies needed.
        """
        records = _df_to_records(df)
        records = _normalize_ohlcv_keys(records)
        records = _ensure_time_key(records, time_column)
        col = column.lower()
        values = [_safe_float(r[col]) for r in records if col in r]
        times = [r["time"] for r in records if col in r]
        multiplier = 2 / (period + 1)
        data = []
        ema_val = None
        for i, v in enumerate(values):
            if v is None:
                continue
            if ema_val is None:
                if i >= period - 1:
                    # Seed with SMA of first `period` values
                    window = values[i - period + 1 : i + 1]
                    if any(x is None for x in window):
                        continue
                    ema_val = sum(window) / period
                    data.append({"time": times[i], "value": round(ema_val, 4)})
            else:
                ema_val = (v - ema_val) * multiplier + ema_val
                data.append({"time": times[i], "value": round(ema_val, 4)})
        defaults = {
            "color": "#2196F3",
            "lineWidth": 1,
            "priceLineVisible": False,
            "lastValueVisible": False,
        }
        defaults.update(options)
        return {"type": "Line", "data": data, "options": defaults}

    # ------------------------------------------------------------------
    # pandas-ta integration (optional dependency: pip install pandas-ta)
    # All methods prefixed with pta_ to keep autocomplete clean.
    # ------------------------------------------------------------------

    @staticmethod
    def pta(df, indicator_name, time_column="date", **kwargs):
        """Compute ANY pandas-ta indicator and return series configs.

        Works with all 200+ pandas-ta indicators. Auto-detects whether to
        overlay on the price scale or use a separate oscillator scale.

        Args:
            df:             pandas (or polars) DataFrame with OHLCV data.
            indicator_name: Any pandas-ta indicator name, e.g. "rsi", "macd",
                            "bbands", "stoch", "adx". Case-insensitive.
            time_column:    Name of the date/time column (default "date").
            **kwargs:       Passed directly to the pandas-ta function,
                            e.g. length=14, fast=12, slow=26.

        Returns:
            list[dict]: One or more series config dicts.

        Usage::

            series_data = [W.candlestick(df)] + W.pta(df, "bbands", length=20)
            series_data = [W.candlestick(df)] + W.pta(df, "rsi", length=14)
        """
        pta_mod = _require_pandas_ta()
        pdf = _ensure_pandas_df(df)
        times = _extract_times(pdf, time_column)
        ohlcv = _ohlcv_series(pdf)

        name_lower = indicator_name.lower()
        fn = getattr(pta_mod, name_lower, None)
        if fn is None:
            raise ValueError(
                f"pandas-ta has no indicator '{indicator_name}'. "
                f"Check spelling or run: import pandas_ta as pta; pta.indicators()"
            )

        # Build call kwargs with OHLCV series - pass all as keyword args
        # so that multi-input indicators (stoch, adx, etc.) get the right args
        call_kwargs = dict(kwargs)
        for arg_name in ("open", "high", "low", "close", "volume"):
            if arg_name in ohlcv and arg_name not in call_kwargs:
                call_kwargs[arg_name] = ohlcv[arg_name]

        result = fn(**call_kwargs)

        if result is None:
            raise ValueError(
                f"pandas-ta returned None for '{indicator_name}'. "
                "Check that the DataFrame has enough rows and required columns."
            )

        import pandas as pd

        is_oscillator = name_lower in _OSCILLATOR_INDICATORS
        scale_id = f"pta_{name_lower}"
        colors = ["#2962FF", "#FF6D00", "#E040FB", "#00BCD4", "#76FF03"]

        # Normalize to DataFrame
        if isinstance(result, pd.Series):
            result = result.to_frame()

        configs = []
        for i, col in enumerate(result.columns):
            data = _ta_col_to_data(result[col], times)
            if not data:
                continue

            col_lower = col.lower()
            is_hist = "hist" in col_lower or col_lower.endswith("h")

            if is_hist:
                opts = {"color": "#26a69a", "priceLineVisible": False, "lastValueVisible": False}
                config = {"type": "Histogram", "data": data, "options": opts}
            else:
                opts = {
                    "color": colors[i % len(colors)],
                    "lineWidth": 1 if len(result.columns) > 1 else 2,
                    "priceLineVisible": False,
                    "lastValueVisible": i == 0,
                }
                config = {"type": "Line", "data": data, "options": opts}

            if is_oscillator:
                config["options"]["priceScaleId"] = scale_id
                config["priceScale"] = {"scaleMargins": {"top": 0.75, "bottom": 0.0}}

            configs.append(config)

        return configs

    @staticmethod
    def pta_rsi(df, length=14, time_column="date", **options):
        """RSI (Relative Strength Index) on a separate 0-100 scale.

        Includes overbought (70) and oversold (30) reference lines.
        """
        pta_mod = _require_pandas_ta()
        pdf = _ensure_pandas_df(df)
        times = _extract_times(pdf, time_column)
        ohlcv = _ohlcv_series(pdf)

        result = pta_mod.rsi(ohlcv["close"], length=length)
        if result is None:
            raise ValueError("pandas-ta RSI returned None - check DataFrame has enough rows.")

        data = _ta_col_to_data(result, times)
        defaults = {
            "color": "#7B1FA2",
            "lineWidth": 2,
            "priceScaleId": "pta_rsi",
            "priceLineVisible": False,
            "lastValueVisible": True,
        }
        defaults.update(options)
        return {
            "type": "Line",
            "data": data,
            "options": defaults,
            "priceScale": {"scaleMargins": {"top": 0.75, "bottom": 0.0}},
            "price_lines": [
                {"price": 70, "color": "rgba(239,83,80,0.5)", "lineWidth": 1, "lineStyle": 2, "axisLabelVisible": True, "title": "OB"},
                {"price": 30, "color": "rgba(38,166,154,0.5)", "lineWidth": 1, "lineStyle": 2, "axisLabelVisible": True, "title": "OS"},
            ],
        }

    @staticmethod
    def pta_macd(df, fast=12, slow=26, signal=9, time_column="date"):
        """MACD with histogram (green/red bars) + MACD line + signal line.

        Returns list[dict] with 3 series configs.
        """
        pta_mod = _require_pandas_ta()
        pdf = _ensure_pandas_df(df)
        times = _extract_times(pdf, time_column)
        ohlcv = _ohlcv_series(pdf)

        result = pta_mod.macd(ohlcv["close"], fast=fast, slow=slow, signal=signal)
        if result is None:
            raise ValueError("pandas-ta MACD returned None - check DataFrame has enough rows.")

        # Find columns by prefix
        macd_col = next(c for c in result.columns if c.startswith("MACD_"))
        hist_col = next(c for c in result.columns if c.startswith("MACDh_"))
        signal_col = next(c for c in result.columns if c.startswith("MACDs_"))

        scale_cfg = {"scaleMargins": {"top": 0.75, "bottom": 0.0}}

        # Histogram with per-bar green/red
        hist_data = []
        for point in _ta_col_to_data(result[hist_col], times):
            point["color"] = "#26a69a" if point["value"] >= 0 else "#ef5350"
            hist_data.append(point)

        configs = [
            {
                "type": "Histogram",
                "data": hist_data,
                "options": {"priceScaleId": "pta_macd", "priceLineVisible": False, "lastValueVisible": False},
                "priceScale": scale_cfg,
            },
            {
                "type": "Line",
                "data": _ta_col_to_data(result[macd_col], times),
                "options": {"color": "#2962FF", "lineWidth": 2, "priceScaleId": "pta_macd", "priceLineVisible": False, "lastValueVisible": True},
                "priceScale": scale_cfg,
            },
            {
                "type": "Line",
                "data": _ta_col_to_data(result[signal_col], times),
                "options": {"color": "#FF6D00", "lineWidth": 1, "priceScaleId": "pta_macd", "priceLineVisible": False, "lastValueVisible": False},
                "priceScale": scale_cfg,
            },
        ]
        return configs

    @staticmethod
    def pta_bbands(df, length=20, std=2.0, column="close", time_column="date"):
        """Bollinger Bands (upper/middle/lower) overlaid on price scale.

        Returns list[dict] with 3 series configs.
        """
        pta_mod = _require_pandas_ta()
        pdf = _ensure_pandas_df(df)
        times = _extract_times(pdf, time_column)
        ohlcv = _ohlcv_series(pdf)

        col_key = column.lower()
        close_s = ohlcv.get(col_key, ohlcv.get("close"))
        result = pta_mod.bbands(close_s, length=length, std=std)
        if result is None:
            raise ValueError("pandas-ta BBands returned None - check DataFrame has enough rows.")

        # Find columns by prefix (handles float formatting of std)
        bbl_col = next(c for c in result.columns if c.startswith("BBL_"))
        bbm_col = next(c for c in result.columns if c.startswith("BBM_"))
        bbu_col = next(c for c in result.columns if c.startswith("BBU_"))

        return [
            {
                "type": "Line",
                "data": _ta_col_to_data(result[bbu_col], times),
                "options": {"color": "rgba(33, 150, 243, 0.6)", "lineWidth": 1, "lineStyle": 2, "priceLineVisible": False, "lastValueVisible": False},
            },
            {
                "type": "Line",
                "data": _ta_col_to_data(result[bbm_col], times),
                "options": {"color": "rgba(33, 150, 243, 1.0)", "lineWidth": 1, "priceLineVisible": False, "lastValueVisible": False},
            },
            {
                "type": "Line",
                "data": _ta_col_to_data(result[bbl_col], times),
                "options": {"color": "rgba(33, 150, 243, 0.6)", "lineWidth": 1, "lineStyle": 2, "priceLineVisible": False, "lastValueVisible": False},
            },
        ]

    @staticmethod
    def pta_stoch(df, k=14, d=3, smooth_k=3, time_column="date"):
        """Stochastic Oscillator (%K and %D) on a separate 0-100 scale.

        Includes overbought (80) and oversold (20) reference lines.
        Returns list[dict] with 2 series configs.
        """
        pta_mod = _require_pandas_ta()
        pdf = _ensure_pandas_df(df)
        times = _extract_times(pdf, time_column)
        ohlcv = _ohlcv_series(pdf)

        result = pta_mod.stoch(ohlcv["high"], ohlcv["low"], ohlcv["close"], k=k, d=d, smooth_k=smooth_k)
        if result is None:
            raise ValueError("pandas-ta Stochastic returned None - check DataFrame has enough rows.")

        k_col = next(c for c in result.columns if c.startswith("STOCHk_"))
        d_col = next(c for c in result.columns if c.startswith("STOCHd_"))

        scale_cfg = {"scaleMargins": {"top": 0.75, "bottom": 0.0}}
        return [
            {
                "type": "Line",
                "data": _ta_col_to_data(result[k_col], times),
                "options": {"color": "#2962FF", "lineWidth": 2, "priceScaleId": "pta_stoch", "priceLineVisible": False, "lastValueVisible": True},
                "priceScale": scale_cfg,
                "price_lines": [
                    {"price": 80, "color": "rgba(239,83,80,0.4)", "lineWidth": 1, "lineStyle": 2, "axisLabelVisible": True, "title": "OB"},
                    {"price": 20, "color": "rgba(38,166,154,0.4)", "lineWidth": 1, "lineStyle": 2, "axisLabelVisible": True, "title": "OS"},
                ],
            },
            {
                "type": "Line",
                "data": _ta_col_to_data(result[d_col], times),
                "options": {"color": "#FF6D00", "lineWidth": 1, "priceScaleId": "pta_stoch", "priceLineVisible": False, "lastValueVisible": False},
                "priceScale": scale_cfg,
            },
        ]

    @staticmethod
    def pta_atr(df, length=14, time_column="date", **options):
        """Average True Range on a separate scale."""
        pta_mod = _require_pandas_ta()
        pdf = _ensure_pandas_df(df)
        times = _extract_times(pdf, time_column)
        ohlcv = _ohlcv_series(pdf)

        result = pta_mod.atr(ohlcv["high"], ohlcv["low"], ohlcv["close"], length=length)
        if result is None:
            raise ValueError("pandas-ta ATR returned None - check DataFrame has enough rows.")

        data = _ta_col_to_data(result, times)
        defaults = {
            "color": "#F57F17",
            "lineWidth": 2,
            "priceScaleId": "pta_atr",
            "priceLineVisible": False,
            "lastValueVisible": True,
        }
        defaults.update(options)
        return {
            "type": "Line",
            "data": data,
            "options": defaults,
            "priceScale": {"scaleMargins": {"top": 0.75, "bottom": 0.0}},
        }

    @staticmethod
    def pta_adx(df, length=14, time_column="date", **options):
        """Average Directional Index on a separate 0-100 scale.

        Includes a trend threshold line at 25.
        """
        pta_mod = _require_pandas_ta()
        pdf = _ensure_pandas_df(df)
        times = _extract_times(pdf, time_column)
        ohlcv = _ohlcv_series(pdf)

        result = pta_mod.adx(ohlcv["high"], ohlcv["low"], ohlcv["close"], length=length)
        if result is None:
            raise ValueError("pandas-ta ADX returned None - check DataFrame has enough rows.")

        adx_col = next(c for c in result.columns if c.startswith("ADX_"))
        data = _ta_col_to_data(result[adx_col], times)

        defaults = {
            "color": "#00BCD4",
            "lineWidth": 2,
            "priceScaleId": "pta_adx",
            "priceLineVisible": False,
            "lastValueVisible": True,
        }
        defaults.update(options)
        return {
            "type": "Line",
            "data": data,
            "options": defaults,
            "priceScale": {"scaleMargins": {"top": 0.75, "bottom": 0.0}},
            "price_lines": [
                {"price": 25, "color": "rgba(0,188,212,0.4)", "lineWidth": 1, "lineStyle": 2, "axisLabelVisible": True, "title": "Trend"},
            ],
        }

    @staticmethod
    def pta_obv(df, time_column="date", **options):
        """On-Balance Volume on a separate scale."""
        pta_mod = _require_pandas_ta()
        pdf = _ensure_pandas_df(df)
        times = _extract_times(pdf, time_column)
        ohlcv = _ohlcv_series(pdf)

        result = pta_mod.obv(ohlcv["close"], ohlcv["volume"])
        if result is None:
            raise ValueError("pandas-ta OBV returned None - check DataFrame has enough rows.")

        data = _ta_col_to_data(result, times)
        defaults = {
            "color": "#26a69a",
            "lineWidth": 2,
            "priceScaleId": "pta_obv",
            "priceLineVisible": False,
            "lastValueVisible": True,
        }
        defaults.update(options)
        return {
            "type": "Line",
            "data": data,
            "options": defaults,
            "priceScale": {"scaleMargins": {"top": 0.75, "bottom": 0.0}},
        }

    @staticmethod
    def pta_supertrend(df, length=7, multiplier=3.0, time_column="date", **options):
        """Supertrend overlaid on the price chart with green/red coloring."""
        pta_mod = _require_pandas_ta()
        pdf = _ensure_pandas_df(df)
        times = _extract_times(pdf, time_column)
        ohlcv = _ohlcv_series(pdf)

        result = pta_mod.supertrend(ohlcv["high"], ohlcv["low"], ohlcv["close"], length=length, multiplier=multiplier)
        if result is None:
            raise ValueError("pandas-ta Supertrend returned None - check DataFrame has enough rows.")

        st_col = next(c for c in result.columns if c.startswith("SUPERT_"))
        dir_col = next(c for c in result.columns if c.startswith("SUPERTd_"))

        data = []
        for i in range(len(result)):
            if i >= len(times):
                break
            v = _safe_float(result[st_col].iloc[i])
            if v is None:
                continue
            direction = result[dir_col].iloc[i]
            if direction != direction:  # NaN check
                continue
            color = "#26a69a" if direction > 0 else "#ef5350"
            data.append({"time": times[i], "value": v, "color": color})

        defaults = {
            "lineWidth": 2,
            "priceLineVisible": False,
            "lastValueVisible": True,
        }
        defaults.update(options)
        return {"type": "Line", "data": data, "options": defaults}

    @staticmethod
    def pta_vwap(df, time_column="date", **options):
        """Volume Weighted Average Price overlaid on the price chart."""
        pta_mod = _require_pandas_ta()
        pdf = _ensure_pandas_df(df)
        times = _extract_times(pdf, time_column)
        ohlcv = _ohlcv_series(pdf)

        if "volume" not in ohlcv:
            raise ValueError("VWAP requires a 'volume' column in the DataFrame.")

        # VWAP requires a DatetimeIndex - set it if not already
        import pandas as pd
        if not isinstance(pdf.index, pd.DatetimeIndex):
            for candidate in (time_column, "Date", "date", "datetime", "timestamp", "time"):
                if candidate in pdf.columns:
                    pdf = pdf.set_index(pd.DatetimeIndex(pdf[candidate]))
                    break

        ohlcv = _ohlcv_series(pdf)
        result = pta_mod.vwap(ohlcv["high"], ohlcv["low"], ohlcv["close"], ohlcv["volume"])
        if result is None:
            raise ValueError("pandas-ta VWAP returned None - check DataFrame has enough rows.")

        data = _ta_col_to_data(result, times)
        defaults = {
            "color": "#E91E63",
            "lineWidth": 2,
            "priceLineVisible": False,
            "lastValueVisible": True,
        }
        defaults.update(options)
        return {"type": "Line", "data": data, "options": defaults}

    @staticmethod
    def pta_ichimoku(df, tenkan=9, kijun=26, senkou=52, time_column="date"):
        """Ichimoku Cloud (5 lines) overlaid on the price chart.

        Returns list[dict] with 5 series configs:
        Tenkan-sen, Kijun-sen, Chikou Span, Senkou Span A, Senkou Span B.
        """
        pta_mod = _require_pandas_ta()
        pdf = _ensure_pandas_df(df)
        times = _extract_times(pdf, time_column)
        ohlcv = _ohlcv_series(pdf)

        # ichimoku returns a tuple: (ichimoku_df, spans_df)
        result = pta_mod.ichimoku(ohlcv["high"], ohlcv["low"], ohlcv["close"], tenkan=tenkan, kijun=kijun, senkou=senkou)
        if result is None or result[0] is None:
            raise ValueError("pandas-ta Ichimoku returned None - check DataFrame has enough rows.")

        ich_df, spans_df = result

        # Find columns by prefix
        its_col = next((c for c in ich_df.columns if c.startswith("ITS_")), None)
        iks_col = next((c for c in ich_df.columns if c.startswith("IKS_")), None)
        ics_col = next((c for c in ich_df.columns if c.startswith("ICS_")), None)
        isa_col = next((c for c in spans_df.columns if c.startswith("ISA_")), None)
        isb_col = next((c for c in spans_df.columns if c.startswith("ISB_")), None)

        configs = []

        # Tenkan-sen (conversion line)
        if its_col:
            configs.append({
                "type": "Line",
                "data": _ta_col_to_data(ich_df[its_col], times),
                "options": {"color": "#2962FF", "lineWidth": 1, "priceLineVisible": False, "lastValueVisible": False},
            })

        # Kijun-sen (base line)
        if iks_col:
            configs.append({
                "type": "Line",
                "data": _ta_col_to_data(ich_df[iks_col], times),
                "options": {"color": "#B71C1C", "lineWidth": 1, "priceLineVisible": False, "lastValueVisible": False},
            })

        # Chikou Span (lagging span)
        if ics_col:
            configs.append({
                "type": "Line",
                "data": _ta_col_to_data(ich_df[ics_col], times),
                "options": {"color": "#26a69a", "lineWidth": 1, "priceLineVisible": False, "lastValueVisible": False},
            })

        # Senkou Span A & B (cloud) - these are forward-shifted, build their own times
        if spans_df is not None and (isa_col or isb_col):
            span_times = [
                v.strftime("%Y-%m-%d") if hasattr(v, "strftime") else str(v)
                for v in spans_df.index
            ]
            if isa_col:
                configs.append({
                    "type": "Line",
                    "data": _ta_col_to_data(spans_df[isa_col], span_times),
                    "options": {"color": "rgba(38,166,154,0.5)", "lineWidth": 1, "lineStyle": 1, "priceLineVisible": False, "lastValueVisible": False},
                })
            if isb_col:
                configs.append({
                    "type": "Line",
                    "data": _ta_col_to_data(spans_df[isb_col], span_times),
                    "options": {"color": "rgba(239,83,80,0.5)", "lineWidth": 1, "lineStyle": 1, "priceLineVisible": False, "lastValueVisible": False},
                })

        return configs

    # ------------------------------------------------------------------
    # Markers, price lines, themes
    # ------------------------------------------------------------------

    @staticmethod
    def markers(time, position="belowBar", shape="arrowUp", color="#2196F3", text="", size=1):
        """Create a single marker dict.

        Args:
            time: Time string (e.g. "2024-01-15") or unix timestamp
            position: "belowBar", "aboveBar", or "inBar"
            shape: "arrowUp", "arrowDown", "circle", "square"
            color: Marker color
            text: Label text
            size: Marker size (1-4)
        """
        return {
            "time": time,
            "position": position,
            "shape": shape,
            "color": color,
            "text": text,
            "size": size,
        }

    @staticmethod
    def price_line(price, color="#FF0000", line_width=1, line_style=2, title=""):
        """Create a price line config dict.

        Args:
            price: Price value for the horizontal line
            color: Line color
            line_width: Width in pixels
            line_style: 0=Solid, 1=Dotted, 2=Dashed, 3=LargeDashed, 4=SparseDotted
            title: Label text
        """
        return {
            "price": price,
            "color": color,
            "lineWidth": line_width,
            "lineStyle": line_style,
            "axisLabelVisible": True,
            "title": title,
        }

    @staticmethod
    def dark_theme():
        """Return chart_options for a dark theme."""
        return {
            "layout": {
                "background": {"type": "solid", "color": "#1a1a2e"},
                "textColor": "#d1d4dc",
            },
            "grid": {
                "vertLines": {"color": "rgba(42, 46, 57, 0.5)"},
                "horzLines": {"color": "rgba(42, 46, 57, 0.5)"},
            },
            "crosshair": {
                "mode": 0,
            },
        }

    @staticmethod
    def light_theme():
        """Return chart_options for a light theme."""
        return {
            "layout": {
                "background": {"type": "solid", "color": "#ffffff"},
                "textColor": "#191919",
            },
            "grid": {
                "vertLines": {"color": "rgba(197, 203, 206, 0.5)"},
                "horzLines": {"color": "rgba(197, 203, 206, 0.5)"},
            },
            "crosshair": {
                "mode": 0,
            },
        }
