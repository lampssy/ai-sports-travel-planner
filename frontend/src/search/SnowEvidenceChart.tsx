import {
  Area,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { WeatherEvidencePoint } from "../types";
import { SegmentedTabs } from "../ui/SegmentedTabs";

export type ChartMode = "historical" | "forecast";
export type WeatherMetric = "depth" | "freshSnow" | "temperature";

export const snowDepthReferenceCopy =
  "This reference helps compare modeled snow depth. It does not show snow coverage, open ski runs, comfort, or safety.";

export interface WeatherChartDatum {
  label: string;
  depthRange: [number, number] | null;
  medianDepth: number | null;
  depth: number | null;
  freshSnow: number | null;
  minimumTemperature: number | null;
  maximumTemperature: number | null;
}

export const weatherMetricDefinition = {
  depth: {
    label: "Snow depth",
    unit: "cm",
    referenceValue: 30,
  },
  freshSnow: {
    label: "Fresh snow",
    unit: "cm",
    referenceValue: null,
  },
  temperature: {
    label: "Temperature",
    unit: "°C",
    referenceValue: null,
  },
} as const satisfies Record<
  WeatherMetric,
  { label: string; unit: string; referenceValue: number | null }
>;

function displayValue(value: number, unit: string): string {
  const normalized = unit === "%" ? value * 100 : value;
  const rendered = Number.isInteger(normalized)
    ? String(normalized)
    : normalized.toFixed(1);
  return `${rendered} ${unit}`;
}

function formatTooltipValue(
  value: number | [number, number] | undefined,
  unit: string,
): string {
  if (value == null) return "Not available";
  if (Array.isArray(value)) {
    return `${displayValue(value[0], unit)} to ${displayValue(value[1], unit)}`;
  }
  return displayValue(value, unit);
}

export function buildWeatherChartData(
  _mode: ChartMode,
  _metric: WeatherMetric,
  points: WeatherEvidencePoint[],
): WeatherChartDatum[] {
  return points.map((point) => ({
    label: point.date_or_month_day,
    depthRange:
      point.snow_depth_cm_p25 == null || point.snow_depth_cm_p75 == null
        ? null
        : [point.snow_depth_cm_p25, point.snow_depth_cm_p75],
    medianDepth: point.snow_depth_cm_p50,
    depth: point.snow_depth_cm,
    freshSnow: point.snowfall_cm,
    minimumTemperature: point.temperature_min_c,
    maximumTemperature: point.temperature_max_c,
  }));
}

export function selectWeatherChartTickLabels(
  data: WeatherChartDatum[],
  maximumTicks = 3,
): string[] {
  if (!data.length) return [];

  const boundedMaximum = Math.max(1, Math.floor(maximumTicks));
  if (data.length <= boundedMaximum) {
    return data.map((point) => point.label);
  }
  if (boundedMaximum === 1) {
    return [data[0].label];
  }

  const lastIndex = data.length - 1;
  return Array.from({ length: boundedMaximum }, (_, index) =>
    data[Math.round((index * lastIndex) / (boundedMaximum - 1))].label,
  );
}

export function formatWeatherChartTickLabel(label: string): string {
  return /^\d{4}-(\d{2}-\d{2})$/.exec(label)?.[1] ?? label;
}

function hasMetricData(data: WeatherChartDatum[], metric: WeatherMetric): boolean {
  if (metric === "depth") {
    return data.some(
      (point) =>
        point.depth != null || point.medianDepth != null || point.depthRange != null,
    );
  }
  if (metric === "freshSnow") {
    return data.some((point) => point.freshSnow != null);
  }
  return data.some(
    (point) =>
      point.minimumTemperature != null || point.maximumTemperature != null,
  );
}

function numericRange(values: Array<number | null>): [number, number] | null {
  const available = values.filter((value): value is number => value != null);
  return available.length
    ? [Math.min(...available), Math.max(...available)]
    : null;
}

function rangeCopy(range: [number, number], unit: string): string {
  return range[0] === range[1]
    ? displayValue(range[0], unit)
    : `${displayValue(range[0], unit)} to ${displayValue(range[1], unit)}`;
}

export function weatherChartSummary(
  mode: ChartMode,
  metric: WeatherMetric,
  points: WeatherEvidencePoint[],
): string {
  const data = buildWeatherChartData(mode, metric, points);
  if (metric === "depth") {
    const range = numericRange(
      data.map((point) =>
        mode === "historical" ? point.medianDepth : point.depth,
      ),
    );
    return range
      ? `Chart summary: ${mode === "historical" ? "Median" : "Forecast"} snow depth is ${rangeCopy(range, "cm")} across dates with values.`
      : "Chart summary: No snow-depth values are available for this window.";
  }
  if (metric === "freshSnow") {
    const range = numericRange(data.map((point) => point.freshSnow));
    return range
      ? `Chart summary: Fresh snow is ${rangeCopy(range, "cm")} across dates with values.`
      : "Chart summary: No fresh-snow values are available for this window.";
  }
  const minimums = numericRange(data.map((point) => point.minimumTemperature));
  const maximums = numericRange(data.map((point) => point.maximumTemperature));
  const lower = minimums?.[0] ?? maximums?.[0];
  const upper = maximums?.[1] ?? minimums?.[1];
  return lower != null && upper != null
    ? `Chart summary: Temperature ranges from ${displayValue(lower, "°C")} to ${displayValue(upper, "°C")} across dates with values.`
    : "Chart summary: No temperature values are available for this window.";
}

function WeatherChart({
  mode,
  metric,
  points,
}: {
  mode: ChartMode;
  metric: WeatherMetric;
  points: WeatherEvidencePoint[];
}) {
  const definition = weatherMetricDefinition[metric];
  const data = buildWeatherChartData(mode, metric, points);
  const xAxisTicks = selectWeatherChartTickLabels(data);
  const available = hasMetricData(data, metric);
  const summary = weatherChartSummary(mode, metric, points);

  if (!available) {
    const valueKind = mode === "forecast" ? "forecast values" : "observations";
    return (
      <div className="snow-chart-empty" role="status">
        No {definition.label.toLowerCase()} {valueKind} are available for this window.
      </div>
    );
  }

  const seriesNames: Record<string, string> = {
    depthRange: `Typical range (${definition.unit})`,
    medianDepth: `Median depth (${definition.unit})`,
    depth: `Forecast depth (${definition.unit})`,
    freshSnow: `Fresh snow (${definition.unit})`,
    minimumTemperature: `Minimum (${definition.unit})`,
    maximumTemperature: `Maximum (${definition.unit})`,
  };

  return (
    <section className="snow-chart-block__metric">
      <p className="snow-chart-block__summary">{summary}</p>
      <div
        className="snow-chart-block__visual"
        role="img"
        aria-label={`${mode === "forecast" ? "Forecast" : "Historical"} ${definition.label.toLowerCase()} chart in ${definition.unit}. ${summary} Missing ${mode === "forecast" ? "forecast values" : "observations"} are shown as gaps.`}
      >
        <div className="snow-chart__unit" aria-hidden="true">
          {definition.unit}
        </div>
        <ResponsiveContainer width="100%" height={320}>
        <ComposedChart data={data} margin={{ top: 16, right: 20, bottom: 8, left: 4 }}>
          <CartesianGrid strokeDasharray="3 5" vertical={false} />
          <XAxis
            dataKey="label"
            interval={0}
            tickFormatter={formatWeatherChartTickLabel}
            ticks={xAxisTicks}
            tickMargin={10}
          />
          <YAxis
            tickFormatter={(value: number) => `${value} ${definition.unit}`}
            width={62}
          />
          <Tooltip
            formatter={(value, name) => [
              formatTooltipValue(value as number | [number, number] | undefined, definition.unit),
              seriesNames[String(name)] ?? String(name),
            ]}
          />
          <Legend formatter={(value) => seriesNames[String(value)] ?? String(value)} />

          {metric === "depth" && mode === "historical" ? (
            <>
              <Area
                type="linear"
                dataKey="depthRange"
                name="depthRange"
                connectNulls={false}
                stroke="#b84f75"
                fill="#f6dce7"
                fillOpacity={0.72}
                isAnimationActive={false}
              />
              <Line
                type="linear"
                dataKey="medianDepth"
                name="medianDepth"
                connectNulls={false}
                stroke="#1261b8"
                strokeWidth={3}
                dot={{ r: 3 }}
                isAnimationActive={false}
              />
            </>
          ) : null}
          {metric === "depth" && mode === "forecast" ? (
            <Line
              type="linear"
              dataKey="depth"
              name="depth"
              connectNulls={false}
              stroke="#087f6a"
              strokeWidth={3}
              dot={{ r: 3 }}
              isAnimationActive={false}
            />
          ) : null}
          {metric === "freshSnow" ? (
            <Line
              type="linear"
              dataKey="freshSnow"
              name="freshSnow"
              connectNulls={false}
              stroke="#1261b8"
              strokeWidth={3}
              dot={{ r: 3 }}
              isAnimationActive={false}
            />
          ) : null}
          {metric === "temperature" ? (
            <>
              <Line
                type="linear"
                dataKey="minimumTemperature"
                name="minimumTemperature"
                connectNulls={false}
                stroke="#1261b8"
                strokeWidth={3}
                dot={{ r: 3 }}
                isAnimationActive={false}
              />
              <Line
                type="linear"
                dataKey="maximumTemperature"
                name="maximumTemperature"
                connectNulls={false}
                stroke="#b84f75"
                strokeWidth={3}
                dot={{ r: 3 }}
                isAnimationActive={false}
              />
            </>
          ) : null}
          {metric === "depth" && definition.referenceValue != null ? (
            <ReferenceLine
              y={definition.referenceValue}
              stroke="#a15d00"
              strokeDasharray="5 5"
              label={{ value: "30 cm snow-depth reference", fill: "#704300", position: "insideTopRight" }}
            />
          ) : null}
        </ComposedChart>
        </ResponsiveContainer>
      </div>
      {metric === "depth" && definition.referenceValue != null ? (
        <div className="snow-depth-reference">
          <strong>30 cm snow-depth reference</strong>
          <p>{snowDepthReferenceCopy}</p>
        </div>
      ) : null}
    </section>
  );
}

export function SnowEvidenceChart({
  mode,
  points,
  interpretation,
}: {
  mode: ChartMode;
  points: WeatherEvidencePoint[];
  interpretation: string;
}) {
  const metricTabs = (Object.keys(weatherMetricDefinition) as WeatherMetric[]).map(
    (metric) => ({
      id: metric,
      label: weatherMetricDefinition[metric].label,
      panel: <WeatherChart mode={mode} metric={metric} points={points} />,
    }),
  );

  return (
    <div className="snow-chart-block">
      <p className="snow-chart-block__interpretation">{interpretation}</p>
      <SegmentedTabs
        tabs={metricTabs}
        ariaLabel={`${mode === "forecast" ? "Forecast" : "Historical"} weather metrics`}
        defaultValue="depth"
        className="snow-metric-tabs"
      />
    </div>
  );
}
