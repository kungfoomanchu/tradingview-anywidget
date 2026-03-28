# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "marimo",
#     "anywidget>=0.9.0",
#     "traitlets>=5.0.0",
#     "yfinance>=0.2.0",
#     "pandas>=1.5.0",
#     "tradingview-anywidget",
# ]
# ///

import marimo

__generated_with = "0.20.4"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import yfinance as yf
    from tradingview_anywidget import LightweightChartWidget

    return LightweightChartWidget, mo, yf


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
    return chart_type, controls, period_dropdown, show_volume, theme_toggle, ticker_input


@app.cell
def _(period_dropdown, ticker_input, yf):
    df = yf.download(ticker_input.value, period=period_dropdown.value)
    # Flatten MultiIndex columns from yfinance
    if hasattr(df.columns, "levels") and len(df.columns.names) > 1:
        df.columns = df.columns.get_level_values(0)
    # Move date index to a column
    df = df.reset_index()
    return (df,)


@app.cell
def _(LightweightChartWidget, chart_type, df, mo, show_volume, theme_toggle):
    W = LightweightChartWidget

    # Build series based on selected chart type
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

    chart = mo.ui.anywidget(
        W(
            series_data=series,
            chart_options=theme,
            height=500,
        )
    )
    chart
    return (chart,)


@app.cell
def _(chart, mo):
    mo.md(
        f"""
        **Crosshair data:** `{chart.value.get("crosshair_data", {})}`
        """
    )
    return


if __name__ == "__main__":
    app.run()
