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
