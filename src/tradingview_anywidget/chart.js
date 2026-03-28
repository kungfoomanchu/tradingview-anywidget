import {
  createChart,
  createTextWatermark,
  createSeriesMarkers,
  CandlestickSeries,
  LineSeries,
  AreaSeries,
  BarSeries,
  BaselineSeries,
  HistogramSeries,
} from "https://esm.sh/lightweight-charts@5.0";

const SERIES_TYPES = {
  Candlestick: CandlestickSeries,
  Line: LineSeries,
  Area: AreaSeries,
  Bar: BarSeries,
  Baseline: BaselineSeries,
  Histogram: HistogramSeries,
};

function buildChart(el, model) {
  const container = document.createElement("div");
  container.classList.add("lwc-container");
  el.appendChild(container);

  const legendEl = document.createElement("div");
  legendEl.classList.add("lwc-legend");
  container.appendChild(legendEl);

  const width = model.get("width") || undefined;
  const height = model.get("height") || 400;
  const chartOptions = model.get("chart_options") || {};

  const chart = createChart(container, {
    width,
    height,
    autoSize: !width,
    ...chartOptions,
  });

  // Track created series for teardown and updates
  let seriesInstances = [];

  // Watermark plugin instance (v5 uses createTextWatermark)
  let watermarkInstance = null;

  // Guard flag to prevent visible_range feedback loop
  let updatingRangeFromPython = false;

  function applyWatermark() {
    if (watermarkInstance) {
      watermarkInstance.detach();
      watermarkInstance = null;
    }

    const wm = model.get("watermark");
    if (!wm || !wm.text) return;

    const pane = chart.panes()[0];
    if (!pane) return;

    watermarkInstance = createTextWatermark(pane, {
      horzAlign: wm.horzAlign || "center",
      vertAlign: wm.vertAlign || "center",
      lines: [
        {
          text: wm.text,
          color: wm.color || "rgba(171, 71, 188, 0.3)",
          fontSize: wm.fontSize || 48,
          fontStyle: wm.fontStyle || "",
          fontFamily: wm.fontFamily || "",
        },
      ],
    });
  }

  function clearSeries() {
    for (const s of seriesInstances) {
      chart.removeSeries(s);
    }
    seriesInstances = [];
  }

  function renderSeries() {
    clearSeries();
    const seriesData = model.get("series_data") || [];

    for (const config of seriesData) {
      const SeriesType = SERIES_TYPES[config.type];
      if (!SeriesType) {
        console.warn(`Unknown series type: ${config.type}`);
        continue;
      }

      const options = { ...(config.options || {}) };
      const series = chart.addSeries(SeriesType, options);

      // Apply price scale options if provided (e.g. for volume overlay)
      if (config.priceScale) {
        series.priceScale().applyOptions(config.priceScale);
      }

      // Set data
      if (config.data && config.data.length > 0) {
        series.setData(config.data);
      }

      // Apply markers to this series (v5: createSeriesMarkers)
      if (config.markers && config.markers.length > 0) {
        const sorted = [...config.markers].sort((a, b) => {
          if (a.time < b.time) return -1;
          if (a.time > b.time) return 1;
          return 0;
        });
        createSeriesMarkers(series, sorted);
      }

      // Apply price lines to this series
      if (config.price_lines) {
        for (const pl of config.price_lines) {
          series.createPriceLine(pl);
        }
      }

      seriesInstances.push(series);
    }

    // Fit content if requested
    if (model.get("fit_content")) {
      chart.timeScale().fitContent();
    }

    // Apply visible range if set
    const visRange = model.get("visible_range");
    if (visRange && visRange.from && visRange.to) {
      updatingRangeFromPython = true;
      chart.timeScale().setVisibleRange(visRange);
      updatingRangeFromPython = false;
    }
  }

  function updateLegend(param) {
    if (!param || !param.seriesData) {
      legendEl.innerHTML = "";
      return;
    }

    const parts = [];
    for (const [series, data] of param.seriesData) {
      if (!data) continue;
      if ("close" in data) {
        parts.push(
          `<span class="lwc-legend-item">` +
            `O<span class="lwc-val">${data.open.toFixed(2)}</span> ` +
            `H<span class="lwc-val">${data.high.toFixed(2)}</span> ` +
            `L<span class="lwc-val">${data.low.toFixed(2)}</span> ` +
            `C<span class="lwc-val">${data.close.toFixed(2)}</span>` +
            `</span>`
        );
      } else if ("value" in data) {
        parts.push(
          `<span class="lwc-legend-item">` +
            `<span class="lwc-val">${data.value.toFixed(2)}</span>` +
            `</span>`
        );
      }
    }
    legendEl.innerHTML = parts.join(" ");
  }

  // --- Events: JS -> Python ---

  chart.subscribeCrosshairMove((param) => {
    updateLegend(param);

    if (!param || !param.time) {
      return;
    }

    const data = { time: param.time };
    const values = [];
    for (const [series, seriesData] of param.seriesData) {
      if (seriesData) {
        values.push({ ...seriesData });
      }
    }
    data.series_values = values;

    if (param.point) {
      data.x = param.point.x;
      data.y = param.point.y;
    }

    model.set("crosshair_data", data);
    model.save_changes();
  });

  chart.subscribeClick((param) => {
    if (!param || !param.time) return;

    const data = { time: param.time };
    const values = [];
    for (const [series, seriesData] of param.seriesData) {
      if (seriesData) {
        values.push({ ...seriesData });
      }
    }
    data.series_values = values;

    if (param.point) {
      data.x = param.point.x;
      data.y = param.point.y;
    }

    model.set("clicked_data", data);
    model.save_changes();
  });

  // Send visible range changes back to Python (with guard to prevent feedback loop)
  chart.timeScale().subscribeVisibleTimeRangeChange((range) => {
    if (updatingRangeFromPython) return;
    if (range) {
      model.set("visible_range", { from: range.from, to: range.to });
      model.save_changes();
    }
  });

  // --- React to Python changes ---

  model.on("change:series_data", () => {
    renderSeries();
    applyWatermark();
  });

  model.on("change:chart_options", () => {
    const opts = model.get("chart_options") || {};
    chart.applyOptions(opts);
  });

  model.on("change:width", () => {
    const w = model.get("width");
    if (w) {
      chart.applyOptions({ width: w, autoSize: false });
    } else {
      chart.applyOptions({ autoSize: true });
    }
  });

  model.on("change:height", () => {
    chart.applyOptions({ height: model.get("height") || 400 });
  });

  model.on("change:watermark", () => {
    applyWatermark();
  });

  model.on("change:fit_content", () => {
    if (model.get("fit_content")) {
      chart.timeScale().fitContent();
    }
  });

  model.on("change:visible_range", () => {
    const vr = model.get("visible_range");
    if (vr && vr.from && vr.to) {
      updatingRangeFromPython = true;
      chart.timeScale().setVisibleRange(vr);
      updatingRangeFromPython = false;
    }
  });

  // Initial render
  renderSeries();
  applyWatermark();

  return chart;
}

function render({ model, el }) {
  const chart = buildChart(el, model);

  // Return cleanup function for teardown
  return () => {
    model.off("change:series_data");
    model.off("change:chart_options");
    model.off("change:width");
    model.off("change:height");
    model.off("change:watermark");
    model.off("change:fit_content");
    model.off("change:visible_range");
    chart.remove();
  };
}

export default { render };
