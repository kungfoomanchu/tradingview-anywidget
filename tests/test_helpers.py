import base64
import datetime

import numpy as np
import pandas as pd
import polars as pl
import pytest

from lightweight_charts_anywidget import LightweightChartWidget as W


@pytest.fixture
def df():
    """200 business days of synthetic OHLCV data, yfinance-style capitalized columns."""
    n = 200
    rng = np.random.default_rng(0)
    close = 100 + rng.standard_normal(n).cumsum()
    return pd.DataFrame(
        {
            "Date": pd.date_range("2024-01-01", periods=n, freq="B"),
            "Open": close + rng.standard_normal(n) * 0.3,
            "High": close + 1,
            "Low": close - 1,
            "Close": close,
            "Volume": rng.integers(1_000_000, 2_000_000, n),
        }
    )


# --- Time handling ---


def test_daily_times_are_date_strings(df):
    data = W.candlestick(df)["data"]
    assert data[0]["time"] == "2024-01-01"
    assert len(data) == 200


def test_intraday_times_are_unique_unix_seconds(df):
    intraday = df.assign(Date=pd.date_range("2024-01-02 09:30", periods=200, freq="5min"))
    times = [d["time"] for d in W.candlestick(intraday)["data"]]
    assert len(set(times)) == 200
    assert times[0] == 1704187800  # 2024-01-02 09:30 as wall-clock UTC seconds
    assert all(isinstance(t, int) for t in times)


def test_intraday_series_including_midnight_uses_one_time_format(df):
    times = pd.date_range("2024-01-01 22:00", periods=200, freq="h")  # crosses midnight
    data = W.line(df.assign(Date=times))["data"]
    assert all(isinstance(d["time"], int) for d in data)


def test_tz_aware_times_keep_wall_clock(df):
    ny = pd.date_range("2024-01-02 09:30", periods=200, freq="5min", tz="America/New_York")
    data = W.line(df.assign(Date=ny))["data"]
    assert data[0]["time"] == 1704187800  # displays as 09:30, not 14:30


def test_datetime_index_is_used_when_no_time_column(df):
    data = W.candlestick(df.set_index("Date"))["data"]
    assert data[0]["time"] == "2024-01-01"


def test_polars_dataframe(df):
    data = W.candlestick(pl.from_pandas(df))["data"]
    assert data[0]["time"] == "2024-01-01"
    assert data[0]["close"] == pytest.approx(df["Close"].iloc[0])


def test_explicit_time_column(df):
    data = W.line(df.rename(columns={"Date": "ts"}), time_column="ts")["data"]
    assert data[0]["time"] == "2024-01-01"


# --- Column lookup ---


@pytest.mark.parametrize("name", ["MyCol", "mycol", "Adj Close"])
def test_any_column_name_works(df, name):
    data = W.line(df.assign(**{name: df["Close"]}), column=name)["data"]
    assert len(data) == 200


def test_missing_column_raises(df):
    with pytest.raises(KeyError, match="nope"):
        W.line(df, column="nope")


def test_nan_values_are_dropped(df):
    df.loc[5, "Close"] = np.nan
    assert len(W.line(df)["data"]) == 199
    assert len(W.candlestick(df)["data"]) == 199


# --- Helpers ---


def test_volume_is_colored_by_direction(df):
    data = W.volume(df)["data"]
    first = df.iloc[0]
    expected = "rgba(38,166,154,0.5)" if first["Close"] >= first["Open"] else "rgba(239,83,80,0.5)"
    assert data[0]["color"] == expected


def test_sma_matches_pandas(df):
    data = W.sma(df, period=20)["data"]
    expected = df["Close"].rolling(20).mean().dropna()
    assert len(data) == len(expected)
    assert data[-1]["value"] == pytest.approx(expected.iloc[-1], abs=1e-4)


def test_ema_matches_pandas_seeded_with_sma(df):
    data = W.ema(df, period=10)["data"]
    assert len(data) == 191
    assert data[0]["value"] == pytest.approx(df["Close"].iloc[:10].mean(), abs=1e-4)


def test_marker_and_markers_alias():
    assert W.marker("2024-01-15", text="Buy") == W.markers("2024-01-15", text="Buy")


# --- pandas-ta ---

pta = pytest.importorskip("pandas_ta")


def test_pta_oscillators_go_in_their_own_pane(df):
    assert W.pta_rsi(df)["pane"] == 1
    assert all(s["pane"] == 1 for s in W.pta_macd(df))
    assert all(s.get("pane", 0) == 0 for s in W.pta_bbands(df))


def test_pta_generic_detects_histogram_columns(df):
    types = [s["type"] for s in W.pta(df, "macd")]
    assert types == ["Line", "Histogram", "Line"]


def test_pta_generic_overlay_stays_on_price_pane(df):
    assert all(s.get("pane", 0) == 0 for s in W.pta(df, "ema", length=10))


@pytest.mark.parametrize("name", ["bbands", "supertrend"])
def test_pta_generic_overlay_moves_non_price_columns_to_own_pane(df, name):
    # bbands includes bandwidth/%B and supertrend a +/-1 direction column;
    # on the price pane they would squash the candles flat
    low, high = df["Low"].min(), df["High"].max()
    for config in W.pta(df, name):
        values = [p["value"] for p in config["data"]]
        on_price_pane = config.get("pane", 0) == 0
        assert on_price_pane == (low * 0.5 < np.median(values) < high * 2)


def test_pta_ichimoku_times_are_dates_and_cloud_covers_history(df):
    configs = W.pta_ichimoku(df)
    for config in configs:
        for point in config["data"]:
            assert isinstance(point["time"], str) and len(point["time"]) == 10
    span_a = configs[3]["data"]
    # Cloud starts inside the data range and projects past the last bar
    assert span_a[0]["time"] < "2024-09-01"
    assert span_a[-1]["time"] > df["Date"].iloc[-1].strftime("%Y-%m-%d")


def test_pta_vwap_anchor(df):
    daily = W.pta_vwap(df, anchor="D")["data"]
    monthly = W.pta_vwap(df, anchor="M")["data"]
    assert daily != monthly


def test_pta_accepts_polars(df):
    assert len(W.pta_rsi(pl.from_pandas(df))["data"]) > 0


# --- Series options: snake_case and enum names ---


def test_snake_case_options_become_camel_case(df):
    opts = W.line(df, line_style="dashed", line_type="steps", point_markers_visible=True, visible=False)["options"]
    assert opts["lineStyle"] == 2
    assert opts["lineType"] == 1
    assert opts["pointMarkersVisible"] is True
    assert opts["visible"] is False


def test_camel_case_options_and_numbers_pass_through(df):
    opts = W.line(df, lineStyle=1, priceScaleId="left", last_price_animation="continuous")["options"]
    assert opts["lineStyle"] == 1
    assert opts["priceScaleId"] == "left"
    assert opts["lastPriceAnimation"] == 1


def test_unknown_enum_name_raises(df):
    with pytest.raises(ValueError, match="lineStyle"):
        W.line(df, line_style="wavy")


def test_price_line_accepts_style_name():
    assert W.price_line(100, line_style="dotted")["lineStyle"] == 1


# --- Scales, interaction, merging ---


def test_time_scale_skips_unset_options():
    assert W.time_scale(bar_spacing=10, fix_right_edge=True, ticks_visible=True) == {
        "timeScale": {"barSpacing": 10, "fixRightEdge": True, "ticksVisible": True}
    }


def test_price_scale_mode_name_and_margins():
    assert W.price_scale(mode="log", margins=(0.8, 0), border_visible=False) == {
        "mode": 1,
        "borderVisible": False,
        "scaleMargins": {"top": 0.8, "bottom": 0},
    }


def test_interaction_mouse_wheel_off_keeps_dragging():
    opts = W.interaction(mouse_wheel=False)
    assert opts["handleScroll"]["mouseWheel"] is False
    assert opts["handleScroll"]["pressedMouseMove"] is True
    assert opts["handleScale"]["mouseWheel"] is False
    assert opts["handleScale"]["pinch"] is True


def test_merge_options_is_deep_and_does_not_mutate():
    theme = W.theme("dark")
    merged = W.merge_options(theme, W.time_scale(bar_spacing=10))
    assert merged["timeScale"] == {"borderColor": "#2a2e39", "barSpacing": 10}
    assert theme["timeScale"] == {"borderColor": "#2a2e39"}


def test_rows_in_range_pandas_and_polars(df):
    time_range = {"from": "2024-01-03", "to": "2024-01-05"}
    assert len(W.rows_in_range(df, time_range)) == 3
    assert W.rows_in_range(pl.from_pandas(df), time_range).height == 3
    assert W.rows_in_range(df, {}) is df


def test_rows_in_range_intraday(df):
    intraday = df.assign(Date=pd.date_range("2024-01-02 09:30", periods=200, freq="5min"))
    start = 1704187800  # 09:30
    assert len(W.rows_in_range(intraday, {"from": start, "to": start + 600})) == 3


# --- Navigation commands ---


def test_navigation_methods_send_commands(monkeypatch):
    chart = W()
    sent = []
    monkeypatch.setattr(chart, "send", sent.append)
    chart.scroll_to_real_time()
    chart.scroll_to_position(-20, animated=True)
    chart.show_all()
    assert sent == [
        {"command": "scrollToRealTime"},
        {"command": "scrollToPosition", "position": -20, "animated": True},
        {"command": "fitContent"},
    ]


# --- Crosshair, formatters, watermarks ---


def test_crosshair_mode_names_and_shared_line_options():
    assert W.crosshair(mode="magnet_ohlc", color="#888", style="dotted", horz_line={"visible": False}) == {
        "crosshair": {
            "mode": 3,
            "vertLine": {"color": "#888", "style": 1},
            "horzLine": {"color": "#888", "style": 1, "visible": False},
        }
    }
    with pytest.raises(ValueError):
        W.crosshair(mode="sticky")


def test_number_format_as_series_price_format(df):
    fmt = W.number_format(style="currency", currency="EUR", maximum_fraction_digits=0, locale="de-DE")
    assert fmt == {
        "intl": "number",
        "options": {"style": "currency", "currency": "EUR", "maximumFractionDigits": 0},
        "locale": "de-DE",
    }
    assert W.line(df, price_format=fmt)["options"]["priceFormat"] == fmt


def test_localization_builds_formatter_specs():
    opts = W.localization(
        locale="de-DE",
        price_formatter=W.number_format(notation="compact"),
        tick_formatters={"month": W.date_format(month="long")},
    )
    assert opts["localization"]["locale"] == "de-DE"
    assert opts["localization"]["priceFormatter"]["intl"] == "number"
    assert opts["timeScale"]["tickMarkFormatter"]["month"] == {"intl": "date", "options": {"month": "long"}}
    with pytest.raises(ValueError, match="tick types"):
        W.localization(tick_formatters={"week": W.date_format()})


def test_image_watermark_embeds_local_files(tmp_path):
    path = tmp_path / "logo.png"
    path.write_bytes(b"\x89PNG fake")
    wm = W.image_watermark(path, alpha=0.5, max_width=100)
    assert wm["image"].startswith("data:image/png;base64,")
    assert wm["alpha"] == 0.5 and wm["maxWidth"] == 100 and wm["pane"] == 0
    assert W.image_watermark("https://example.com/logo.png")["image"] == "https://example.com/logo.png"
    with pytest.raises(FileNotFoundError):
        W.image_watermark(tmp_path / "missing.png")


def test_watermark_accepts_a_list():
    chart = W(watermark=[{"text": "AAPL"}, W.image_watermark(b"png")])
    assert len(chart.watermark) == 2


def test_marker_and_price_line_ids():
    assert W.marker("2024-01-02", id="buy-1")["id"] == "buy-1"
    assert "id" not in W.marker("2024-01-02")
    assert W.price_line(100, id="stop")["id"] == "stop"


# --- Live updates ---


def test_update_appends_and_replaces_existing_bars(df, monkeypatch):
    chart = W(series_data=[W.line(df.head(3))])
    sent = []
    monkeypatch.setattr(chart, "send", sent.append)
    data = chart.series_data[0]["data"]

    chart.update({"time": pd.Timestamp("2024-01-03"), "value": 1.0})  # replaces the latest bar
    assert data[-1] == {"time": "2024-01-03", "value": 1.0} and len(data) == 3
    chart.update({"time": datetime.date(2024, 1, 4), "value": 2.0})  # appends
    assert data[-1]["time"] == "2024-01-04" and len(data) == 4
    assert sent[1] == {
        "command": "update", "series": 0, "point": {"time": "2024-01-04", "value": 2.0}, "historical": False
    }
    chart.update({"time": "2024-01-02", "value": 3.0})  # an earlier bar: replaced
    assert data[1] == {"time": "2024-01-02", "value": 3.0} and sent[2]["historical"] is True
    chart.update({"time": "2023-12-25", "value": 4.0})  # no bar at that time: ignored
    assert len(data) == 4 and len(sent) == 3


def test_update_intraday_converts_to_unix_seconds(df):
    intraday = df.head(2).assign(Date=pd.date_range("2024-01-02 09:30", periods=2, freq="5min"))
    chart = W(series_data=[W.line(intraday)])
    chart.send = lambda msg: None
    chart.update({"time": datetime.datetime(2024, 1, 2, 9, 40), "value": 1.0})
    assert chart.series_data[0]["data"][-1]["time"] == 1704188400


def test_image_watermark_detects_svg_bytes():
    assert W.image_watermark(b'<svg width="10" height="10"></svg>')["image"].startswith("data:image/svg+xml;base64,")


# --- Gaps, crosshair commands, screenshots, horizontal axis ---


def test_gaps_keep_missing_values_as_whitespace(df):
    holes = df.head(5).copy()
    holes.loc[2, "Close"] = np.nan
    assert len(W.line(holes)["data"]) == 4
    data = W.line(holes, gaps=True)["data"]
    assert len(data) == 5 and data[2] == {"time": "2024-01-03"}
    candles = W.candlestick(holes, gaps=True)["data"]
    assert candles[2] == {"time": "2024-01-03"} and "close" in candles[1]


def test_crosshair_commands_convert_time(df, monkeypatch):
    chart = W(series_data=[W.line(df.head(3))])
    sent = []
    monkeypatch.setattr(chart, "send", sent.append)
    chart.set_crosshair(datetime.date(2024, 1, 2))
    chart.clear_crosshair()
    assert sent == [
        {"command": "setCrosshair", "series": 0, "time": "2024-01-02"},
        {"command": "clearCrosshair"},
    ]


def test_screenshot_png_and_save(tmp_path, monkeypatch):
    chart = W()
    sent = []
    monkeypatch.setattr(chart, "send", sent.append)
    assert chart.screenshot_png() is None
    chart.screenshot = "data:image/png;base64,old"
    path = tmp_path / "chart.png"
    chart.save_screenshot(path)
    assert sent == [{"command": "screenshot", "download": None}]
    assert chart.screenshot == ""  # cleared so the next one counts as a change
    png = b"\x89PNG\r\n\x1a\n"
    chart.screenshot = "data:image/png;base64," + base64.b64encode(png).decode()  # from the browser
    assert path.read_bytes() == png


def test_x_axis_is_validated():
    assert W(x_axis="number").x_axis == "number"
    with pytest.raises(Exception):
        W(x_axis="log")


# --- Up/down markers, price range, numeric spacing ---


def test_up_down_markers_options():
    assert W.up_down_markers() == {}
    assert W.up_down_markers(positive_color="#0f0", duration=2) == {
        "positiveColor": "#0f0",
        "updateVisibilityDuration": 2000,
    }


def test_price_range_passes_through_as_series_option(df):
    assert W.line(df, price_range=(0, 100))["options"]["priceRange"] == (0, 100)


def test_x_spacing_accepts_names_and_steps():
    assert W(x_spacing="even").x_spacing == "even"
    assert W(x_spacing=2.5).x_spacing == 2.5
    with pytest.raises(Exception):
        W(x_spacing="log")
