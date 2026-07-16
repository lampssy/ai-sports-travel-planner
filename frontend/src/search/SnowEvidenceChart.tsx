import { useId } from "react";

import type { WeatherEvidencePoint } from "../types";

type ChartMode = "historical" | "forecast";

const valueColumns = [
  ["snow_depth_cm", "Snow depth", "cm"],
  ["snow_depth_cm_p25", "Depth p25", "cm"],
  ["snow_depth_cm_p50", "Median depth", "cm"],
  ["snow_depth_cm_p75", "Depth p75", "cm"],
  ["snowfall_cm", "Snowfall", "cm"],
  ["temperature_min_c", "Minimum temperature", "°C"],
  ["temperature_max_c", "Maximum temperature", "°C"],
  ["rain_risk", "Rain risk", "%"],
  ["thaw_risk", "Thaw risk", "%"],
  ["wind_gust_kmh", "Wind gust", "km/h"],
] as const;

function displayValue(value: number, unit: string): string {
  const normalized = unit === "%" ? value * 100 : value;
  const rendered = Number.isInteger(normalized)
    ? String(normalized)
    : normalized.toFixed(1);
  return `${rendered} ${unit}`;
}

function pointValue(point: WeatherEvidencePoint, mode: ChartMode): number | null {
  return mode === "forecast" ? point.snow_depth_cm : point.snow_depth_cm_p50;
}

function xFor(index: number, count: number): number {
  if (count <= 1) return 320;
  return 42 + (index / (count - 1)) * 556;
}

function yFor(value: number, maximum: number): number {
  return 202 - (value / maximum) * 160;
}

function linePath(
  points: WeatherEvidencePoint[],
  mode: ChartMode,
  maximum: number,
): string {
  return points
    .flatMap((point, index) => {
      const value = pointValue(point, mode);
      return value == null
        ? []
        : [{ index, value }];
    })
    .map(
      ({ index, value }, plottedIndex) =>
        `${plottedIndex === 0 ? "M" : "L"}${xFor(index, points.length)} ${yFor(
          value,
          maximum,
        )}`,
    )
    .join(" ");
}

function rangePath(points: WeatherEvidencePoint[], maximum: number): string {
  const ranged = points.flatMap((point, index) =>
    point.snow_depth_cm_p25 == null || point.snow_depth_cm_p75 == null
      ? []
      : [{ point, index }],
  );
  if (!ranged.length) return "";
  const upper = ranged.map(({ point, index }) =>
    `${xFor(index, points.length)} ${yFor(point.snow_depth_cm_p75 ?? 0, maximum)}`,
  );
  const lower = [...ranged].reverse().map(({ point, index }) =>
    `${xFor(index, points.length)} ${yFor(point.snow_depth_cm_p25 ?? 0, maximum)}`,
  );
  return `M${upper.join(" L")} L${lower.join(" L")} Z`;
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
  const titleId = useId();
  const descriptionId = useId();
  const plotted = points.flatMap((point) =>
    [
      point.snow_depth_cm,
      point.snow_depth_cm_p25,
      point.snow_depth_cm_p50,
      point.snow_depth_cm_p75,
    ].flatMap((value) => (value == null ? [] : [value])),
  );
  const maximum = Math.max(1, ...plotted) * 1.1;
  const path = linePath(points, mode, maximum);
  const range = mode === "historical" ? rangePath(points, maximum) : "";
  const tableLabel = mode === "forecast" ? "Forecast weather values" : "Historical weather values";

  return (
    <div className="snow-chart-block">
      <p className="snow-chart-block__interpretation">{interpretation}</p>
      {points.length ? (
        <div className="snow-chart-block__visual">
          <svg
            className="snow-chart"
            viewBox="0 0 640 240"
            role="img"
            aria-labelledby={`${titleId} ${descriptionId}`}
          >
            <title id={titleId}>
              {mode === "forecast" ? "Forecast snow profile" : "Historical snow-depth profile"}
            </title>
            <desc id={descriptionId}>
              {mode === "forecast"
                ? "A dashed line shows forecast snow depth; diamond markers identify days with rain, thaw, or wind risk."
                : "A solid line shows median snow depth and a shaded band shows the 25th to 75th percentile range."}
            </desc>
            <line className="snow-chart__grid" x1="42" y1="202" x2="598" y2="202" />
            <line className="snow-chart__grid" x1="42" y1="122" x2="598" y2="122" />
            <line className="snow-chart__grid" x1="42" y1="42" x2="598" y2="42" />
            {range ? <path className="snow-chart__range" d={range} /> : null}
            {path ? (
              <path
                className={`snow-chart__line snow-chart__line--${mode}`}
                d={path}
              />
            ) : null}
            {mode === "forecast"
              ? points.map((point, index) => {
                  const hasRisk =
                    (point.rain_risk ?? 0) > 0 ||
                    (point.thaw_risk ?? 0) > 0 ||
                    point.wind_gust_kmh != null;
                  const value = point.snow_depth_cm;
                  if (!hasRisk || value == null) return null;
                  const x = xFor(index, points.length);
                  const y = yFor(value, maximum);
                  return (
                    <rect
                      key={point.date_or_month_day}
                      className="snow-chart__risk"
                      x={x - 4}
                      y={y - 4}
                      width="8"
                      height="8"
                      transform={`rotate(45 ${x} ${y})`}
                    />
                  );
                })
              : null}
          </svg>
          <ul className="snow-chart-legend" aria-label="Chart symbols">
            {mode === "historical" ? (
              <>
                <li><span className="legend-line legend-line--solid" />Solid line: median</li>
                <li><span className="legend-range" />Shaded range: 25th to 75th percentile</li>
              </>
            ) : (
              <>
                <li><span className="legend-line legend-line--dashed" />Dashed line: forecast depth</li>
                <li><span className="legend-risk" />Diamond: rain, thaw, or wind risk</li>
              </>
            )}
          </ul>
        </div>
      ) : (
        <p className="snow-chart-block__empty">No daily profile values are available.</p>
      )}

      {points.length ? (
        <details className="snow-values">
          <summary>View structured weather values</summary>
          <div className="snow-values__scroll">
            <table aria-label={tableLabel}>
              <thead>
                <tr>
                  <th scope="col">Date</th>
                  {valueColumns.map(([key, label]) =>
                    points.some((point) => point[key] != null) ? (
                      <th key={key} scope="col">{label}</th>
                    ) : null,
                  )}
                </tr>
              </thead>
              <tbody>
                {points.map((point) => (
                  <tr key={point.date_or_month_day}>
                    <th scope="row">{point.date_or_month_day}</th>
                    {valueColumns.map(([key, , unit]) =>
                      points.some((candidate) => candidate[key] != null) ? (
                        <td key={key}>
                          {point[key] == null ? null : displayValue(point[key], unit)}
                        </td>
                      ) : null,
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      ) : null}
    </div>
  );
}
