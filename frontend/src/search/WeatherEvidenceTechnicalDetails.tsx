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

function sourceElevation(elevationM: number | null): string {
  return elevationM == null
    ? "Not available"
    : `${elevationM.toLocaleString("en-GB")} m`;
}

function sourceProfileDates(profileDates: string[]): string {
  return profileDates.length
    ? profileDates.join(", ")
    : "Not available";
}

type SourceDetail = { label: string; value: string };

function SourceDetails({ details }: { details: SourceDetail[] }) {
  return (
    <dl className="weather-source-details">
      {details.map((detail) => (
        <div key={detail.label}>
          <dt>{detail.label}</dt>
          <dd>{detail.value}</dd>
        </div>
      ))}
    </dl>
  );
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
    <div
      className="snow-values__scroll"
      role="region"
      aria-label={`${tableLabel}. Scroll horizontally to view all values.`}
      tabIndex={0}
    >
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
      {historical.snow_depth_cm_p50 != null ? (
        <p>
          Typical historical snow depth averages the daily median values across
          matching dates in the travel window.
        </p>
      ) : null}
      {historical.snow_depth_cm_p25 != null &&
      historical.snow_depth_cm_p75 != null ? (
        <p>
          The usual historical range averages the daily 25th- and 75th-percentile
          values across matching dates.
        </p>
      ) : null}
      {historical.probability_snow_depth_ge_30cm != null ? (
        <p>
          The 30 cm figure is the average daily historical percentage at or above
          the reference across matching dates. It is not the chance of reaching 30
          cm at least once during the trip.
        </p>
      ) : null}
      <ul className="weather-source-list">
        {historical.sources.map((source, index) => (
          <li key={`${source.source_model}-${source.baseline_period}-${index}`}>
            <SourceDetails
              details={[
                { label: "Model", value: source.source_model },
                { label: "Calculated", value: source.computed_at },
                {
                  label: "Baseline years",
                  value: `${source.baseline_start_year}-${source.baseline_end_year}`,
                },
                { label: "Evidence seasons", value: String(source.evidence_seasons) },
                {
                  label: "Latest archive year",
                  value: source.latest_archive_year == null
                    ? "Not available"
                    : String(source.latest_archive_year),
                },
                { label: "Elevation", value: sourceElevation(source.elevation_m) },
                { label: "Profile dates", value: sourceProfileDates(source.profile_dates) },
                { label: "Source rows", value: String(source.row_count) },
              ]}
            />
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
        <p>
          {response.unavailable_reason === "travel_window_missing"
            ? "Travel dates are needed before source rows or daily values can be assessed."
            : "No source rows or daily values are available for this trip window."}
        </p>
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
          <ul className="weather-source-list">
            {forecast.sources.map((source) => (
              <li key={source.forecast_run_id}>
                <SourceDetails
                  details={[
                    { label: "Source", value: source.source_label },
                    { label: "Model", value: source.source_model },
                    { label: "Source key", value: source.forecast_source_key },
                    { label: "Run ID", value: source.forecast_run_id },
                    { label: "Issued", value: source.issued_at },
                    { label: "Elevation", value: sourceElevation(source.elevation_m) },
                    { label: "Profile dates", value: sourceProfileDates(source.profile_dates) },
                    { label: "Source rows", value: String(source.row_count) },
                  ]}
                />
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
