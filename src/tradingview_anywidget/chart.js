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
} from "https://esm.sh/lightweight-charts@5.2";

const SERIES_TYPES = {
  Candlestick: CandlestickSeries,
  Line: LineSeries,
  Area: AreaSeries,
  Bar: BarSeries,
  Baseline: BaselineSeries,
  Histogram: HistogramSeries,
};

// Panes below the main price pane get this share of the height relative to it
const SUB_PANE_STRETCH = 0.4;

// Limit how often mouse/scroll events are sent to Python
const CROSSHAIR_THROTTLE_MS = 100;
const RANGE_DEBOUNCE_MS = 250;

function throttle(fn, ms) {
  let last = 0;
  let timer = null;
  return (arg) => {
    clearTimeout(timer);
    const wait = last + ms - Date.now();
    if (wait <= 0) {
      last = Date.now();
      fn(arg);
    } else {
      // Trailing call so the final position is always sent
      timer = setTimeout(() => {
        last = Date.now();
        fn(arg);
      }, wait);
    }
  };
}

function debounce(fn, ms) {
  let timer = null;
  return (arg) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(arg), ms);
  };
}

function seriesColor(series) {
  const o = series.options();
  return o.color || o.lineColor || o.topLineColor || o.upColor || "";
}

function render({ model, el }) {
  const container = document.createElement("div");
  container.classList.add("lwc-container");
  el.appendChild(container);

  // The chart always auto-sizes to the container; width/height are set on the container
  function applySize() {
    const width = model.get("width");
    container.style.width = width ? `${width}px` : "100%";
    container.style.height = `${model.get("height") || 400}px`;
  }
  applySize();

  const chart = createChart(container, {
    autoSize: true,
    ...(model.get("chart_options") || {}),
  });

  // [{ series, config }] for every series currently on the chart
  let seriesList = [];
  let watermarkInstance = null;
  let legends = [];

  function applyWatermark() {
    if (watermarkInstance) {
      watermarkInstance.detach();
      watermarkInstance = null;
    }
    const wm = model.get("watermark");
    if (!wm || !wm.text) return;

    watermarkInstance = createTextWatermark(chart.panes()[0], {
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

  function applyVisibleRange() {
    const vr = model.get("visible_range");
    if (!vr || !vr.from || !vr.to) return;
    // Skip ranges that came from this chart's own scrolling, to avoid snapping the view
    const current = chart.timeScale().getVisibleRange();
    if (current && current.from === vr.from && current.to === vr.to) return;
    chart.timeScale().setVisibleRange(vr);
  }

  function renderSeries() {
    for (const { series } of seriesList) {
      chart.removeSeries(series); // also removes panes left empty
    }
    seriesList = [];

    for (const config of model.get("series_data") || []) {
      const SeriesType = SERIES_TYPES[config.type];
      if (!SeriesType) {
        console.warn(`Unknown series type: ${config.type}`);
        continue;
      }

      // A pane index past the last pane creates a new pane
      const series = chart.addSeries(SeriesType, config.options || {}, config.pane || 0);
      if (config.priceScale) {
        series.priceScale().applyOptions(config.priceScale);
      }
      if (config.data && config.data.length > 0) {
        series.setData(config.data);
      }
      if (config.markers && config.markers.length > 0) {
        const sorted = [...config.markers].sort((a, b) => (a.time < b.time ? -1 : a.time > b.time ? 1 : 0));
        createSeriesMarkers(series, sorted);
      }
      for (const pl of config.price_lines || []) {
        series.createPriceLine(pl);
      }
      seriesList.push({ series, config });
    }

    const panes = chart.panes();
    panes.forEach((pane, i) => pane.setStretchFactor(i === 0 ? 1 : SUB_PANE_STRETCH));

    if (model.get("fit_content")) {
      chart.timeScale().fitContent();
    }
    updateLegend(null);
  }

  // --- Legend: one per pane, showing hovered (or latest) values ---

  function legendItem(series, config, data, isMain) {
    const fmt = (v) => series.priceFormatter().format(v);
    const item = document.createElement("span");
    item.className = "lwc-legend-item";

    const title = series.options().title;
    if (title) {
      const label = document.createElement("span");
      label.className = "lwc-legend-title";
      label.textContent = title;
      item.appendChild(label);
    }

    if ("close" in data) {
      for (const k of ["open", "high", "low", "close"]) {
        const v = document.createElement("span");
        v.className = "lwc-val";
        v.textContent = fmt(data[k]);
        v.style.color = data.close >= data.open ? config.options?.upColor || "" : config.options?.downColor || "";
        item.append(k[0].toUpperCase(), v, " ");
      }
    } else if ("value" in data) {
      const v = document.createElement("span");
      v.className = "lwc-val";
      v.textContent = fmt(data.value);
      v.style.color = data.color || seriesColor(series);
      item.appendChild(v);
    }
    // Skip unlabeled secondary series (e.g. Bollinger outer bands) to keep the legend short
    return title || isMain ? item : null;
  }

  function updateLegend(param) {
    for (const legend of legends) legend.remove();
    legends = [];

    const byPane = new Map();
    seriesList.forEach(({ series, config }, i) => {
      let data = param && param.time !== undefined ? param.seriesData.get(series) : null;
      if (!param || param.time === undefined) {
        const all = series.data();
        data = all[all.length - 1];
      }
      if (!data) return;
      const item = legendItem(series, config, data, i === 0);
      if (!item) return;
      const pane = series.getPane();
      if (!byPane.has(pane)) byPane.set(pane, []);
      byPane.get(pane).push(item);
    });

    const top = container.getBoundingClientRect().top;
    for (const [pane, items] of byPane) {
      const paneEl = pane.getHTMLElement();
      const legend = document.createElement("div");
      legend.className = "lwc-legend";
      legend.style.color = chart.options().layout.textColor;
      legend.style.top = `${(paneEl ? paneEl.getBoundingClientRect().top - top : 0) + 6}px`;
      legend.append(...items);
      container.appendChild(legend);
      legends.push(legend);
    }
  }

  // --- Events: JS -> Python ---

  function eventPayload(param) {
    const data = { time: param.time, series_values: [] };
    for (const { series } of seriesList) {
      const values = param.seriesData.get(series);
      if (values) data.series_values.push({ ...values });
    }
    if (param.point) {
      data.x = param.point.x;
      data.y = param.point.y;
    }
    return data;
  }

  const sendCrosshair = throttle((data) => {
    model.set("crosshair_data", data);
    model.save_changes();
  }, CROSSHAIR_THROTTLE_MS);

  chart.subscribeCrosshairMove((param) => {
    updateLegend(param);
    if (param.time !== undefined) {
      sendCrosshair(eventPayload(param));
    }
  });

  chart.subscribeClick((param) => {
    if (param.time === undefined) return;
    model.set("clicked_data", eventPayload(param));
    model.save_changes();
  });

  const sendRange = debounce((range) => {
    const current = model.get("visible_range") || {};
    if (current.from === range.from && current.to === range.to) return;
    model.set("visible_range", { from: range.from, to: range.to });
    model.save_changes();
  }, RANGE_DEBOUNCE_MS);

  chart.timeScale().subscribeVisibleTimeRangeChange((range) => {
    if (range) sendRange(range);
  });

  // Pane heights change when the chart resizes or a pane separator is dragged
  const resizeObserver = new ResizeObserver(() => updateLegend(null));
  resizeObserver.observe(container);

  // --- React to Python changes ---

  const handlers = {
    "change:series_data": () => {
      renderSeries();
      applyWatermark();
    },
    "change:chart_options": () => {
      chart.applyOptions(model.get("chart_options") || {});
      updateLegend(null);
    },
    "change:width": applySize,
    "change:height": applySize,
    "change:watermark": applyWatermark,
    "change:fit_content": () => {
      if (model.get("fit_content")) chart.timeScale().fitContent();
    },
    "change:visible_range": applyVisibleRange,
  };
  for (const [event, handler] of Object.entries(handlers)) {
    model.on(event, handler);
  }

  // Initial render
  renderSeries();
  applyWatermark();
  applyVisibleRange();

  return () => {
    for (const [event, handler] of Object.entries(handlers)) {
      model.off(event, handler);
    }
    resizeObserver.disconnect();
    chart.remove();
  };
}

export default { render };
