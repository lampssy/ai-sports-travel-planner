import type {
  SearchWeatherEvidenceResponse,
  WeatherEvidencePoint,
} from "../types";

type ChartMode = "historical" | "forecast";

const valueColumns = [
  ["snow_depth_cm", "Snow depth", "cm"],
  ["snow_depth_cm_p25", "Depth p25", "cm"],
  ["snow_depth_cm_p50", "Median depth", "cm"],
  ["snow_depth_cm_p75", "Depth p75", "cm"],
  ["snowfall_cm", "Fresh snow", "cm"],
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

function WeatherValuesTable({
  mode,
  points,
}: {
  mode: ChartMode;
  points: WeatherEvidencePoint[];
}) {
  const tableLabel =
    mode === "forecast" ? "Forecast weather values" : "Historical weather values";

  return (
    <div className="snow-values__scroll">
      <table aria-label={tableLabel}>
        <thead>
          <tr>
            <th scope="col">Date</th>
            {valueColumns.map(([key, label, unit]) => (
              <th key={key} scope="col">
                {label} ({unit})
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {points.map((point) => (
            <tr key={point.date_or_month_day}>
              <th scope="row">{point.date_or_month_day}</th>
              {valueColumns.map(([key, , unit]) => (
                <td key={key}>
                  {point[key] == null
                    ? "Not available"
                    : displayValue(point[key], unit)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function HistoricalTechnicalDetails({
  response,
}: {
  response: Extract<SearchWeatherEvidenceResponse, { status: "available" }>;
}) {
  const historical = response.evidence.historical;
  return (
    <section>
      <h4>Historical methods and source rows</h4>
      <p>{historical.source_label}</p>
      <p>
        {historical.baseline_start_year != null &&
        historical.baseline_end_year != null
          ? `Baseline ${historical.baseline_start_year}-${historical.baseline_end_year}.`
          : "Baseline period unavailable."}{" "}
        {historical.latest_archive_year != null
          ? `Latest archive year ${historical.latest_archive_year}.`
          : "Latest archive year unavailable."}
      </p>
      <ul>
        {historical.sources.map((source, index) => (
          <li key={`${source.source_model}-${source.baseline_period}-${index}`}>
            {source.source_model}, {source.evidence_seasons} seasons, {source.row_count} source rows
          </li>
        ))}
      </ul>
      <WeatherValuesTable mode="historical" points={historical.daily_profile} />
    </section>
  );
}

export function WeatherEvidenceTechnicalDetails({
  response,
}: {
  response: SearchWeatherEvidenceResponse;
}) {
  if (response.status === "unavailable") {
    return (
      <section>
        <h4>Weather evidence availability</h4>
        <p>No source rows or daily values are available for this trip window.</p>
      </section>
    );
  }
  const forecast = response.evidence.forecast;
  return (
    <>
      {forecast ? (
        <section>
          <h4>Forecast methods and source rows</h4>
          <p>{forecast.source_label}</p>
          <ul>
            {forecast.sources.map((source) => (
              <li key={source.forecast_run_id}>
                Run {source.forecast_run_id}, issued {source.issued_at}, {source.row_count} source rows
              </li>
            ))}
          </ul>
          <WeatherValuesTable mode="forecast" points={forecast.daily_profile} />
        </section>
      ) : null}
      <HistoricalTechnicalDetails response={response} />
    </>
  );
}
