import { RefreshCw, Snowflake } from "lucide-react";
import {
  Component,
  lazy,
  Suspense,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import { fetchSearchWeatherEvidence } from "../api";
import type {
  SearchIntent,
  SearchWeatherEvidenceRequest,
  SearchWeatherEvidenceResponse,
  WeatherEvidencePoint,
} from "../types";
import { Action } from "../ui/Action";
import { Alert } from "../ui/Alert";
import { AsyncState } from "../ui/AsyncState";
import { Badge } from "../ui/Badge";
import { MetricTile } from "../ui/MetricTile";
import { SectionHeader } from "../ui/SectionHeader";
import { SegmentedTabs } from "../ui/SegmentedTabs";
import {
  deleteWeatherEvidenceCache,
  readWeatherEvidenceCache,
  weatherEvidenceCacheKey,
  writeWeatherEvidenceCache,
} from "./weatherEvidenceCache";

type AvailableResponse = Extract<SearchWeatherEvidenceResponse, { status: "available" }>;
type EvidenceState =
  | { kind: "loading"; contextKey: string }
  | { kind: "error"; contextKey: string; message: string }
  | { kind: "ready"; contextKey: string; response: SearchWeatherEvidenceResponse };

export type WeatherEvidenceLoader = (
  request: SearchWeatherEvidenceRequest,
  signal?: AbortSignal,
) => Promise<SearchWeatherEvidenceResponse>;

const dateTimeFormatter = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
  timeZone: "UTC",
});

const LazySnowEvidenceChart = lazy(() =>
  import("./SnowEvidenceChart").then((module) => ({
    default: module.SnowEvidenceChart,
  })),
);

function formatDateTime(value: string): string {
  return dateTimeFormatter.format(new Date(value));
}

function formatNumber(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

function percentage(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function statusAnnouncement(
  state: EvidenceState,
  skiAreaName: string,
): string {
  if (state.kind === "loading") return `Loading snow evidence for ${skiAreaName}.`;
  if (state.kind === "error") {
    return `Snow evidence for ${skiAreaName} could not be loaded. Retry is available.`;
  }
  if (state.response.status === "unavailable") {
    return `Snow evidence is unavailable for ${skiAreaName}.`;
  }
  return `Snow evidence loaded for ${skiAreaName}.`;
}

function evidenceMetrics(response: AvailableResponse) {
  const { historical } = response.evidence;
  return [
    {
      label: "Average daily median depth",
      value:
        historical.snow_depth_cm_p50 == null
          ? "Not available"
          : `${formatNumber(historical.snow_depth_cm_p50)} cm`,
      detail:
        historical.probability_snow_depth_ge_30cm == null
          ? undefined
          : `${percentage(historical.probability_snow_depth_ge_30cm)} average historical likelihood above 30 cm`,
    },
    {
      label: "Typical depth range",
      value:
        historical.snow_depth_cm_p25 == null || historical.snow_depth_cm_p75 == null
          ? "Not available"
          : `${formatNumber(historical.snow_depth_cm_p25)}-${formatNumber(
              historical.snow_depth_cm_p75,
            )} cm`,
    },
    {
      label: "Fresh snow",
      value:
        historical.average_daily_snowfall_cm == null
          ? "Not available"
          : `${formatNumber(historical.average_daily_snowfall_cm)} cm/day`,
      detail: "Historical daily average",
    },
    {
      label: "Average high",
      value:
        historical.average_max_temperature_c == null
          ? "Not available"
          : `${formatNumber(historical.average_max_temperature_c)} °C`,
    },
  ];
}

function ChartLoadingState() {
  return (
    <AsyncState
      state="loading"
      message="Preparing the weather chart..."
      className="snow-chart-loading"
    />
  );
}

function WeatherChartFallback({
  mode,
  points,
}: {
  mode: "historical" | "forecast";
  points: WeatherEvidencePoint[];
}) {
  return (
    <Alert variant="warning" live="polite" className="snow-chart-fallback">
      <div>
        <strong>Weather chart could not be displayed</strong>
        <p>The underlying values remain available below.</p>
        <div className="snow-values__scroll">
          <table
            aria-label={`${mode === "forecast" ? "Forecast" : "Historical"} weather values`}
          >
            <thead>
              <tr>
                <th scope="col">Date</th>
                <th scope="col">Snow depth (cm)</th>
                <th scope="col">Fresh snow (cm)</th>
                <th scope="col">Minimum (°C)</th>
                <th scope="col">Maximum (°C)</th>
              </tr>
            </thead>
            <tbody>
              {points.map((point) => (
                <tr key={point.date_or_month_day}>
                  <th scope="row">{point.date_or_month_day}</th>
                  <td>{point.snow_depth_cm ?? point.snow_depth_cm_p50 ?? "Not available"}</td>
                  <td>{point.snowfall_cm ?? "Not available"}</td>
                  <td>{point.temperature_min_c ?? "Not available"}</td>
                  <td>{point.temperature_max_c ?? "Not available"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </Alert>
  );
}

class WeatherChartBoundary extends Component<
  { fallback: ReactNode; children: ReactNode },
  { failed: boolean }
> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  render() {
    return this.state.failed ? this.props.fallback : this.props.children;
  }
}

function HistoricalSourceDetails({ response }: { response: AvailableResponse }) {
  const historical = response.evidence.historical;
  return (
    <div className="snow-source-details">
      <p><strong>{historical.source_label}</strong></p>
      <p>
        {historical.baseline_start_year != null && historical.baseline_end_year != null
          ? `Climatology ${historical.baseline_start_year}-${historical.baseline_end_year}`
          : "Climatology period unavailable"}
        {historical.computed_at ? ` · Computed ${formatDateTime(historical.computed_at)} UTC` : ""}
      </p>
      <ul>
        {historical.sources.map((source, index) => (
          <li key={`${source.source_model}-${source.baseline_period}-${index}`}>
            {source.source_model}, {source.evidence_seasons} seasons, {source.row_count} source rows
          </li>
        ))}
      </ul>
    </div>
  );
}

function ForecastSourceDetails({ response }: { response: AvailableResponse }) {
  const forecast = response.evidence.forecast;
  if (!forecast) return null;
  return (
    <div className="snow-source-details">
      <p><strong>{forecast.source_label}</strong></p>
      <p>{forecast.source_model ?? "Forecast model unavailable"}</p>
      <ul>
        {forecast.sources.map((source) => (
          <li key={source.forecast_run_id}>
            Run {source.forecast_run_id}, issued {formatDateTime(source.issued_at)} UTC, {source.row_count} source rows
          </li>
        ))}
      </ul>
    </div>
  );
}

function EvidenceExplorer({
  response,
  historicalSummary,
}: {
  response: AvailableResponse;
  historicalSummary: ReactNode;
}) {
  const { evidence } = response;
  const forecast = evidence.mode === "forecast_assisted" ? evidence.forecast : null;
  const historicalPanel = (
    <>
      {historicalSummary}
      <WeatherChartBoundary
        fallback={(
          <WeatherChartFallback
            mode="historical"
            points={evidence.historical.daily_profile}
          />
        )}
      >
        <Suspense fallback={<ChartLoadingState />}>
          <LazySnowEvidenceChart
            mode="historical"
            points={evidence.historical.daily_profile}
            interpretation={
              forecast
                ? "Historical climatology provides context for the same requested window."
                : evidence.interpretation
            }
            sourceDetails={<HistoricalSourceDetails response={response} />}
          />
        </Suspense>
      </WeatherChartBoundary>
    </>
  );

  if (!forecast) return historicalPanel;

  return (
    <SegmentedTabs
      ariaLabel="Weather evidence source"
      defaultValue="forecast"
      className="snow-source-tabs"
      tabs={[
        {
          id: "forecast",
          label: "Forecast",
          panel: (
            <WeatherChartBoundary
              fallback={(
                <WeatherChartFallback
                  mode="forecast"
                  points={forecast.daily_profile}
                />
              )}
            >
              <Suspense fallback={<ChartLoadingState />}>
                <LazySnowEvidenceChart
                  mode="forecast"
                  points={forecast.daily_profile}
                  interpretation={evidence.interpretation}
                  sourceDetails={<ForecastSourceDetails response={response} />}
                />
              </Suspense>
            </WeatherChartBoundary>
          ),
        },
        {
          id: "historical",
          label: "Historical context",
          panel: historicalPanel,
        },
      ]}
    />
  );
}

function AvailableEvidence({ response }: { response: AvailableResponse }) {
  const { evidence } = response;
  const isForecastAssisted = evidence.mode === "forecast_assisted";
  const forecast = isForecastAssisted ? evidence.forecast : null;
  const historical = evidence.historical;
  const metrics = evidenceMetrics(response);
  const elevation =
    evidence.elevation_status === "mixed"
      ? "Mixed source elevations across this assessment"
      : evidence.elevation_status === "unavailable" || evidence.elevation_m == null
        ? "Mid-mountain elevation unavailable"
        : `Representative mid-mountain at ${evidence.elevation_m.toLocaleString("en-GB")} m`;

  return (
    <>
      <SectionHeader
        eyebrow="Snow evidence"
        title={`Snow & weather for ${evidence.window_label}`}
        description={evidence.interpretation}
        className="snow-evidence__heading"
        action={(
          <Badge variant={isForecastAssisted ? "supported" : "info"} className="snow-mode">
          <Snowflake aria-hidden="true" size={15} />
          {isForecastAssisted ? "Forecast-assisted" : "Historical pattern"}
          </Badge>
        )}
      />

      <div className="snow-evidence__context" aria-label="Weather evidence context">
        <strong>{elevation}</strong>
        {historical.evidence_seasons != null ? (
          <span>{historical.evidence_seasons} evidence seasons</span>
        ) : null}
      </div>

      {isForecastAssisted && forecast ? (
        <div className="snow-evidence__forecast-summary" aria-label="Forecast status">
          <div><span>Issued</span><strong>{forecast.issued_at ? `${formatDateTime(forecast.issued_at)} UTC` : "Not available"}</strong></div>
          <div><span>Freshness</span><strong>{`Fresh at ${formatDateTime(response.evaluated_at)} UTC`}</strong></div>
          <div><span>Requested dates</span><strong>{forecast.usable_date_count} of {forecast.requested_date_count} covered</strong></div>
          <div><span>Forecast coverage in this assessment</span><strong>{percentage(forecast.average_forecast_share)}</strong></div>
        </div>
      ) : (
        <p className="snow-evidence__mode-note">
          This view uses climatology rather than a live forecast.
        </p>
      )}

      <EvidenceExplorer
        response={response}
        historicalSummary={<div className="snow-metrics" aria-label="Historical snow and weather summary">
        {metrics.map((metric) => (
          <MetricTile key={metric.label} {...metric} />
        ))}
        </div>}
      />

      {evidence.limitations.length ? (
        <Alert variant="warning" className="snow-evidence__limitations">
          <div>
            <strong>Evidence limitations</strong>
            <ul>
              {evidence.limitations.map((limitation) => (
                <li key={limitation}>{limitation}</li>
              ))}
            </ul>
          </div>
        </Alert>
      ) : null}
    </>
  );
}

export function SnowEvidence({
  intent,
  skiAreaId,
  skiAreaName,
  loadEvidence = fetchSearchWeatherEvidence,
}: {
  intent: SearchIntent;
  skiAreaId: string;
  skiAreaName: string;
  loadEvidence?: WeatherEvidenceLoader;
}) {
  const key = useMemo(
    () => weatherEvidenceCacheKey(skiAreaId, intent.constraints.travel_window),
    [intent.constraints.travel_window, skiAreaId],
  );
  const [state, setState] = useState<EvidenceState>({
    kind: "loading",
    contextKey: key,
  });
  const [retryRequest, setRetryRequest] = useState(0);
  const requestIdentity = useRef(0);
  const reloadButtonRef = useRef<HTMLButtonElement>(null);
  const intentRef = useRef(intent);
  intentRef.current = intent;
  const visibleState: EvidenceState =
    state.contextKey === key ? state : { kind: "loading", contextKey: key };
  const retrying = retryRequest > 0 && visibleState.kind === "loading";

  useEffect(() => {
    if (retryRequest > 0 && visibleState.kind === "ready") {
      reloadButtonRef.current?.focus({ preventScroll: true });
    }
  }, [retryRequest, visibleState.kind]);

  useEffect(() => {
    const cached = readWeatherEvidenceCache(key);
    if (cached) {
      setState({ kind: "ready", contextKey: key, response: cached });
      return;
    }

    const controller = new AbortController();
    const identity = ++requestIdentity.current;
    setState({ kind: "loading", contextKey: key });
    void loadEvidence(
      { intent: intentRef.current, ski_area_id: skiAreaId },
      controller.signal,
    )
      .then((response) => {
        if (
          controller.signal.aborted ||
          requestIdentity.current !== identity ||
          response.ski_area_id !== skiAreaId
        ) {
          return;
        }
        writeWeatherEvidenceCache(key, response);
        setState({ kind: "ready", contextKey: key, response });
      })
      .catch((caught) => {
        if (controller.signal.aborted || requestIdentity.current !== identity) return;
        setState({
          kind: "error",
          contextKey: key,
          message:
            caught instanceof Error ? caught.message : "Unable to load snow evidence.",
        });
      });

    return () => {
      controller.abort();
      if (requestIdentity.current === identity) requestIdentity.current += 1;
    };
  }, [key, loadEvidence, retryRequest, skiAreaId]);

  return (
    <section className="dossier-section snow-evidence" id="snow-evidence">
      <p className="sr-only" role="status" aria-live="polite" aria-atomic="true">
        {statusAnnouncement(visibleState, skiAreaName)}
      </p>

      {visibleState.kind === "loading" ? (
        <AsyncState
          state="loading"
          title={`Loading snow evidence for ${skiAreaName}`}
          message="The verdict and recommendation controls remain available."
          className="snow-evidence-state"
        />
      ) : null}

      {visibleState.kind === "error" ? (
        <AsyncState
          state="error"
          title="Snow evidence could not be loaded"
          message={visibleState.message}
          retryLabel="Retry snow evidence"
          onRetry={() => setRetryRequest((current) => current + 1)}
          className="snow-evidence-state"
        />
      ) : null}

      {visibleState.kind === "ready" && visibleState.response.status === "unavailable" ? (
        <AsyncState
          state="error"
          title="Snow evidence unavailable"
          retryLabel="Check again"
          onRetry={() => {
            deleteWeatherEvidenceCache(key);
            setRetryRequest((current) => current + 1);
          }}
          className="snow-evidence-state"
          message={(
            <>
              <p>
              {visibleState.response.unavailable_reason === "travel_window_missing"
                ? "No applied travel window is available for weather evidence."
                : "Historical weather evidence is unavailable for this ski area and travel window."}
              </p>
            {visibleState.response.limitations.length ? (
              <ul>
                {visibleState.response.limitations.map((limitation) => (
                  <li key={limitation}>{limitation}</li>
                ))}
              </ul>
            ) : null}
            </>
          )}
        />
      ) : null}

      {visibleState.kind === "ready" && visibleState.response.status === "available" ? (
        <AvailableEvidence response={visibleState.response} />
      ) : null}

      {visibleState.kind !== "error" && retryRequest > 0 ? (
        <Action
          ref={reloadButtonRef}
          variant="secondary"
          size="sm"
          className="snow-evidence__retry"
          aria-disabled={retrying}
          onClick={() => {
            if (retrying) return;
            if (visibleState.kind === "ready") deleteWeatherEvidenceCache(key);
            setRetryRequest((current) => current + 1);
          }}
        >
          <RefreshCw aria-hidden="true" size={17} />
          {retrying ? "Retrying snow evidence" : "Reload snow evidence"}
        </Action>
      ) : null}
    </section>
  );
}
