import {
  createChart,
  createImageWatermark,
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

// Library defaults for the price scale options a series config can change
const SCALE_DEFAULTS = {
  mode: 0,
  autoScale: true,
  invertScale: false,
  borderVisible: true,
  scaleMargins: { top: 0.2, bottom: 0.1 },
};

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

// --- Formatters: Python sends Intl options ({intl: "number" | "date", ...}) since
// JSON can't carry functions; they're turned into formatter functions here ---

const TICK_TYPES = ["year", "month", "day", "time", "time_with_seconds"]; // TickMarkType order

function isFormatSpec(value) {
  return value && typeof value === "object" && (value.intl === "number" || value.intl === "date");
}

// Lightweight Charts times: "YYYY-MM-DD", {year, month, day} or unix seconds
function timeToDate(time) {
  if (typeof time === "number") return new Date(time * 1000);
  if (typeof time === "string") return new Date(`${time}T00:00:00Z`);
  return new Date(Date.UTC(time.year, time.month - 1, time.day));
}

function makeFormatter(spec, chartLocale) {
  const locale = spec.locale || chartLocale || undefined;
  if (spec.intl === "number") {
    const format = new Intl.NumberFormat(locale, spec.options || {});
    return (value) => format.format(value);
  }
  // Times are wall-clock values stored as UTC, so format in UTC unless told otherwise
  const format = new Intl.DateTimeFormat(locale, { timeZone: "UTC", ...(spec.options || {}) });
  return (time) => format.format(timeToDate(time));
}

// chart_options with format specs replaced by formatter functions
function resolveChartOptions(options) {
  const resolved = { ...options };
  const locale = options.localization?.locale;
  if (options.localization) {
    const localization = { ...options.localization };
    for (const key of ["priceFormatter", "timeFormatter"]) {
      if (isFormatSpec(localization[key])) localization[key] = makeFormatter(localization[key], locale);
    }
    resolved.localization = localization;
  }
  const ticks = options.timeScale?.tickMarkFormatter;
  if (ticks && typeof ticks === "object") {
    const byType = TICK_TYPES.map((name) => (isFormatSpec(ticks[name]) ? makeFormatter(ticks[name], locale) : null));
    // Returning null falls back to the built-in label
    const tickMarkFormatter = (time, type) => (byType[type] ? byType[type](time) : null);
    resolved.timeScale = { ...options.timeScale, tickMarkFormatter };
  }
  return resolved;
}

// Series options with a format spec as priceFormat turned into a custom price format
function resolveSeriesOptions(options, chartLocale) {
  if (!isFormatSpec(options.priceFormat)) return options;
  const spec = options.priceFormat;
  return {
    ...options,
    priceFormat: { type: "custom", minMove: spec.minMove ?? 0.01, formatter: makeFormatter(spec, chartLocale) },
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
    ...resolveChartOptions(model.get("chart_options") || {}),
  });

  // [{ series, config }] for every series currently on the chart
  let seriesList = [];
  let watermarks = [];
  let legends = [];

  // watermark is one dict or a list: {text, ...} for text, {image, ...} for an image
  function applyWatermark() {
    for (const watermark of watermarks) watermark.detach();
    watermarks = [];
    const value = model.get("watermark");
    const panes = chart.panes();
    for (const wm of Array.isArray(value) ? value : [value]) {
      if (!wm || !(wm.text || wm.image)) continue;
      const pane = panes[wm.pane || 0];
      if (!pane) continue;
      if (wm.image) {
        const { image, pane: _, ...options } = wm;
        watermarks.push(createImageWatermark(pane, image, options));
        continue;
      }
      watermarks.push(
        createTextWatermark(pane, {
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
        }),
      );
    }
  }

  // pane_heights are relative sizes; without them, panes below the main one get 40% of its height
  function applyPaneHeights() {
    const heights = model.get("pane_heights") || [];
    chart.panes().forEach((pane, i) => {
      const height = heights[i] ?? (heights.length ? 1 : i === 0 ? 1 : SUB_PANE_STRETCH);
      pane.setStretchFactor(height);
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

  // Intraday data (unix-second times) shows the time of day on the axis, and seconds
  // only when some bar has them, unless chart_options.timeScale says otherwise
  function applyAutoTimeScale() {
    const userTimeScale = (model.get("chart_options") || {}).timeScale || {};
    const times = seriesList.flatMap(({ config }) => (config.data || []).map((p) => p.time));
    const intraday = times.some((t) => typeof t === "number");
    const auto = {};
    if (userTimeScale.timeVisible === undefined) auto.timeVisible = intraday;
    if (userTimeScale.secondsVisible === undefined) {
      auto.secondsVisible = intraday && times.some((t) => typeof t === "number" && t % 60 !== 0);
    }
    chart.applyOptions({ timeScale: auto });
  }

  function applyLogicalRange() {
    const lr = model.get("logical_range");
    if (!lr || lr.from === undefined || lr.to === undefined) return;
    const current = chart.timeScale().getVisibleLogicalRange();
    if (current && current.from === lr.from && current.to === lr.to) return;
    chart.timeScale().setVisibleLogicalRange(lr);
  }

  function renderSeries() {
    for (const { series } of seriesList) {
      chart.removeSeries(series); // also removes panes left empty
    }
    seriesList = [];

    // Options applied to a series' left/right price scale are also merged into the
    // chart-wide defaults, which panes created later copy. Reset those defaults to
    // the chart_options values so a previous render can't leak into new panes.
    const chartOptions = model.get("chart_options") || {};
    chart.applyOptions({
      leftPriceScale: { ...SCALE_DEFAULTS, visible: false, ...(chartOptions.leftPriceScale || {}) },
      rightPriceScale: { ...SCALE_DEFAULTS, visible: true, ...(chartOptions.rightPriceScale || {}) },
    });

    for (const config of model.get("series_data") || []) {
      const SeriesType = SERIES_TYPES[config.type];
      if (!SeriesType) {
        console.warn(`Unknown series type: ${config.type}`);
        continue;
      }

      // A pane index past the last pane creates a new pane
      const locale = (model.get("chart_options") || {}).localization?.locale;
      const options = resolveSeriesOptions(config.options || {}, locale);
      const series = chart.addSeries(SeriesType, options, config.pane || 0);
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

    // Apply price scale options only once every pane exists, so they reach just
    // the series' own pane (see the reset above)
    // Left/right axis visibility is chart-wide: Lightweight Charts lays every pane out
    // from pane 0's setting, and a mismatch between panes breaks rendering
    const axisVisible = {};
    for (const { series, config } of seriesList) {
      const { visible, ...scale } = config.priceScale || {};
      const side = config.options?.priceScaleId ?? "right";
      if (side === "left" || side === "right") {
        if (visible !== undefined) axisVisible[side] = visible;
        // The left axis is hidden by default; show it when a series uses it
        else if (side === "left" && !("left" in axisVisible)) axisVisible.left = true;
      }
      if (Object.keys(scale).length > 0) {
        series.priceScale().applyOptions(scale);
      }
    }
    if (chartOptions.leftPriceScale?.visible !== undefined) delete axisVisible.left;
    if (chartOptions.rightPriceScale?.visible !== undefined) delete axisVisible.right;
    for (const [side, visible] of Object.entries(axisVisible)) {
      chart.applyOptions({ [`${side}PriceScale`]: { visible } });
    }
    applyAutoTimeScale();

    applyPaneHeights();

    if (model.get("fit_content")) {
      chart.timeScale().fitContent();
    }
    updateLegend(null);
    // Axis widths are only known after the chart has laid itself out
    requestAnimationFrame(() => container.isConnected && updateLegend(null));
  }

  // --- Legend: one per pane, showing hovered (or latest) values ---

  function legendItem(series, config, data, isMain) {
    // Match the price axis: a chart-wide priceFormatter replaces the default price
    // format (but not volume, percent or custom formats) on the axis, so use it here too
    const chartFormatter = chart.options().localization.priceFormatter;
    const plain = (series.options().priceFormat?.type ?? "price") === "price";
    const fmt = (v) => (chartFormatter && plain ? chartFormatter(v) : series.priceFormatter().format(v));
    const item = document.createElement("span");
    item.className = "lwc-legend-item";
    const visible = series.options().visible !== false;
    if (!visible) item.classList.add("lwc-hidden");
    item.title = visible ? "Click to hide" : "Click to show";
    item.addEventListener("click", () => {
      series.applyOptions({ visible: !visible });
      updateLegend(null);
    });

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

  function leftAxisWidth() {
    try {
      return chart.priceScale("left").width();
    } catch {
      return 0; // the axis has no width until the chart's first layout
    }
  }

  function updateLegend(param) {
    for (const legend of legends) legend.remove();
    legends = [];

    const byPane = new Map();
    seriesList.forEach(({ series, config }, i) => {
      let data = param && param.time !== undefined ? param.seriesData.get(series) : null;
      // Hidden series aren't in the crosshair data; show their latest value instead
      if (!param || param.time === undefined || (!data && series.options().visible === false)) {
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
    // Keep the legend clear of the left axis when it's shown
    const left = chart.options().leftPriceScale.visible ? leftAxisWidth() : 0;
    for (const [pane, items] of byPane) {
      const paneEl = pane.getHTMLElement();
      const legend = document.createElement("div");
      legend.className = "lwc-legend";
      legend.style.color = chart.options().layout.textColor;
      legend.style.top = `${(paneEl ? paneEl.getBoundingClientRect().top - top : 0) + 6}px`;
      legend.style.left = `${left + 12}px`;
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
    if (param.logical !== undefined) data.logical = param.logical;
    if (param.paneIndex !== undefined) data.pane = param.paneIndex;
    if (param.point) {
      data.x = param.point.x;
      data.y = param.point.y;
      // Price under the mouse, on the scale of the first series in that pane
      const first = seriesList.find(({ series }) => series.getPane().paneIndex() === (param.paneIndex ?? 0));
      const price = first ? first.series.coordinateToPrice(param.point.y) : null;
      if (price !== null) data.price = price;
    }
    // The series, marker or price line under the mouse (markers/lines report their id)
    if (param.hoveredSeries) {
      const index = seriesList.findIndex(({ series }) => series === param.hoveredSeries);
      if (index >= 0) data.hovered_series = index;
    }
    if (param.hoveredObjectId !== undefined) data.hovered_object_id = param.hoveredObjectId;
    if (param.hoveredInfo?.type) data.hovered_type = param.hoveredInfo.type;
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

  chart.subscribeDblClick((param) => {
    if (param.time === undefined) return;
    model.set("double_clicked_data", eventPayload(param));
    model.save_changes();
  });

  function sameRange(a, b) {
    return (a || {}).from === b.from && (a || {}).to === b.to;
  }

  const sendRanges = debounce(() => {
    const timeScale = chart.timeScale();
    const range = timeScale.getVisibleRange();
    const logical = timeScale.getVisibleLogicalRange();
    if (!range || !logical) return;
    let changed = false;
    if (!sameRange(model.get("visible_range"), range)) {
      model.set("visible_range", { from: range.from, to: range.to });
      changed = true;
    }
    if (!sameRange(model.get("logical_range"), logical)) {
      model.set("logical_range", { from: logical.from, to: logical.to });
      changed = true;
    }
    const bars = seriesList.length > 0 ? seriesList[0].series.barsInLogicalRange(logical) : null;
    if (bars) {
      model.set("visible_bars", {
        from: bars.from,
        to: bars.to,
        bars_before: Math.round(bars.barsBefore),
        bars_after: Math.round(bars.barsAfter),
      });
      changed = true;
    }
    if (changed) model.save_changes();
  }, RANGE_DEBOUNCE_MS);

  chart.timeScale().subscribeVisibleLogicalRangeChange((logical) => {
    if (logical) sendRanges();
  });

  // --- Commands: Python -> JS (widget.scroll_to_real_time() etc.) ---

  function onCommand(msg) {
    const timeScale = chart.timeScale();
    if (msg.command === "scrollToRealTime") timeScale.scrollToRealTime();
    else if (msg.command === "scrollToPosition") timeScale.scrollToPosition(msg.position, !!msg.animated);
    else if (msg.command === "fitContent") timeScale.fitContent();
    else if (msg.command === "update") updatePoint(msg.series, msg.point);
  }

  // Live data: add or replace the latest bar of one series without redrawing the chart
  function updatePoint(index, point) {
    const entry = seriesList[index];
    if (!entry) return;
    try {
      entry.series.update(point);
    } catch (error) {
      console.warn("Can't update the chart with an older bar", point, error);
      return;
    }
    // Keep the synced series_data in step, so a chart redrawn later still has the bar
    // (every open view runs this, so replace rather than append twice)
    const data = (model.get("series_data")[index] || {}).data;
    if (data) {
      if (data.length && data.at(-1).time === point.time) data[data.length - 1] = point;
      else if (!data.length || data.at(-1).time < point.time) data.push(point);
    }
    updateLegend(null);
  }
  model.on("msg:custom", onCommand);

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
      chart.applyOptions(resolveChartOptions(model.get("chart_options") || {}));
      applyAutoTimeScale();
      updateLegend(null);
    },
    "change:width": applySize,
    "change:height": applySize,
    "change:watermark": applyWatermark,
    "change:pane_heights": applyPaneHeights,
    "change:fit_content": () => {
      if (model.get("fit_content")) chart.timeScale().fitContent();
    },
    "change:visible_range": applyVisibleRange,
    "change:logical_range": applyLogicalRange,
  };
  for (const [event, handler] of Object.entries(handlers)) {
    model.on(event, handler);
  }

  // Initial render
  renderSeries();
  applyWatermark();
  applyVisibleRange();
  applyLogicalRange();

  return () => {
    model.off("msg:custom", onCommand);
    for (const [event, handler] of Object.entries(handlers)) {
      model.off(event, handler);
    }
    resizeObserver.disconnect();
    chart.remove();
  };
}

export default { render };
