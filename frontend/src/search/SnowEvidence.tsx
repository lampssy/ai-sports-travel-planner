import { AlertTriangle, CheckCircle2, RefreshCw, Snowflake } from "lucide-react";
import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent,
} from "react";

import { fetchSearchWeatherEvidence } from "../api";
import type {
  SearchIntent,
  SearchWeatherEvidenceRequest,
  SearchWeatherEvidenceResponse,
} from "../types";
import { SnowEvidenceChart } from "./SnowEvidenceChart";
import {
  deleteWeatherEvidenceCache,
  readWeatherEvidenceCache,
  weatherEvidenceCacheKey,
  writeWeatherEvidenceCache,
} from "./weatherEvidenceCache";

type AvailableResponse = Extract<SearchWeatherEvidenceResponse, { status: "available" }>;
type EvidenceView = "forecast" | "historical";
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
    historical.snow_depth_cm_p50 == null
      ? null
      : ["Median depth", `${formatNumber(historical.snow_depth_cm_p50)} cm`],
    historical.snow_depth_cm_p25 == null || historical.snow_depth_cm_p75 == null
      ? null
      : [
          "Typical range",
          `${formatNumber(historical.snow_depth_cm_p25)}-${formatNumber(
            historical.snow_depth_cm_p75,
          )} cm`,
        ],
    historical.average_daily_snowfall_cm == null
      ? null
      : [
          "Average snowfall",
          `${formatNumber(historical.average_daily_snowfall_cm)} cm/day`,
        ],
    historical.probability_snow_depth_ge_30cm == null
      ? null
      : [
          "Depth above 30 cm",
          percentage(historical.probability_snow_depth_ge_30cm),
        ],
    historical.average_max_temperature_c == null
      ? null
      : [
          "Average max temperature",
          `${formatNumber(historical.average_max_temperature_c)} °C`,
        ],
  ].flatMap((metric) => (metric ? [metric] : [])) as Array<[string, string]>;
}

function EvidenceTabs({
  response,
}: {
  response: AvailableResponse;
}) {
  const [view, setView] = useState<EvidenceView>("forecast");
  const forecastRef = useRef<HTMLButtonElement>(null);
  const historicalRef = useRef<HTMLButtonElement>(null);
  const forecast = response.evidence.forecast;
  if (!forecast) return null;

  const selectFromKey = (event: KeyboardEvent<HTMLButtonElement>) => {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    const next: EvidenceView =
      event.key === "Home"
        ? "forecast"
        : event.key === "End"
          ? "historical"
          : event.key === "ArrowRight"
            ? view === "forecast"
              ? "historical"
              : "forecast"
            : view === "historical"
              ? "forecast"
              : "historical";
    setView(next);
    (next === "forecast" ? forecastRef : historicalRef).current?.focus();
  };

  return (
    <div className="snow-evidence__views">
      <div className="snow-tabs" role="tablist" aria-label="Snow evidence views">
        <button
          ref={forecastRef}
          type="button"
          role="tab"
          id="snow-tab-forecast"
          aria-controls="snow-panel-forecast"
          aria-selected={view === "forecast"}
          tabIndex={view === "forecast" ? 0 : -1}
          onClick={() => setView("forecast")}
          onKeyDown={selectFromKey}
        >
          Forecast
        </button>
        <button
          ref={historicalRef}
          type="button"
          role="tab"
          id="snow-tab-historical"
          aria-controls="snow-panel-historical"
          aria-selected={view === "historical"}
          tabIndex={view === "historical" ? 0 : -1}
          onClick={() => setView("historical")}
          onKeyDown={selectFromKey}
        >
          Historical context
        </button>
      </div>

      {view === "forecast" ? (
        <div
          id="snow-panel-forecast"
          role="tabpanel"
          aria-labelledby="snow-tab-forecast"
        >
          <SnowEvidenceChart
            mode="forecast"
            points={forecast.daily_profile}
            interpretation={response.evidence.interpretation}
          />
        </div>
      ) : (
        <div
          id="snow-panel-historical"
          role="tabpanel"
          aria-labelledby="snow-tab-historical"
        >
          <SnowEvidenceChart
            mode="historical"
            points={response.evidence.historical.daily_profile}
            interpretation="Historical climatology provides context for the same requested window."
          />
        </div>
      )}
    </div>
  );
}

function AvailableEvidence({ response }: { response: AvailableResponse }) {
  const { evidence } = response;
  const isForecastAssisted = evidence.mode === "forecast_assisted";
  const forecast = isForecastAssisted ? evidence.forecast : null;
  const historical = evidence.historical;
  const metrics = evidenceMetrics(response);
  const elevation =
    evidence.elevation_m == null
      ? "Mid-mountain elevation unavailable"
      : `Representative mid-mountain at ${evidence.elevation_m.toLocaleString("en-GB")} m`;

  return (
    <>
      <div className="snow-evidence__heading">
        <div>
          <p className="section-label">Snow evidence</p>
          <h2>Snow evidence for {evidence.window_label}</h2>
        </div>
        <span className={`snow-mode snow-mode--${isForecastAssisted ? "forecast" : "historical"}`}>
          <Snowflake aria-hidden="true" size={15} />
          {isForecastAssisted ? "Forecast-assisted" : "Historical pattern"}
        </span>
      </div>

      <div className="snow-evidence__provenance">
        <strong>{elevation}</strong>
        {historical.evidence_seasons != null ? (
          <span>{historical.evidence_seasons} evidence seasons</span>
        ) : null}
        <span>{historical.source_label}</span>
        {historical.baseline_start_year != null && historical.baseline_end_year != null ? (
          <span>
            Climatology {historical.baseline_start_year}-{historical.baseline_end_year}
          </span>
        ) : null}
      </div>

      {isForecastAssisted && forecast ? (
        <div className="snow-evidence__forecast-meta">
          {forecast.issued_at ? <span>Issued {formatDateTime(forecast.issued_at)} UTC</span> : null}
          <span>Fresh at evaluation time {formatDateTime(response.evaluated_at)} UTC</span>
          <span>
            {forecast.coverage_status === "complete" ? "Complete" : "Partial"} coverage: {forecast.usable_date_count} of {forecast.requested_date_count} dates
          </span>
          <span>Forecast share {percentage(forecast.average_forecast_share)}</span>
          {forecast.sources.map((source) => (
            <span key={source.forecast_run_id}>Selected run {source.forecast_run_id}</span>
          ))}
        </div>
      ) : (
        <p className="snow-evidence__mode-note">
          This view uses climatology rather than a live forecast.
        </p>
      )}

      {isForecastAssisted && forecast ? (
        <EvidenceTabs response={response} />
      ) : (
        <div className="snow-evidence__historical-layout">
          <SnowEvidenceChart
            mode="historical"
            points={historical.daily_profile}
            interpretation={evidence.interpretation}
          />
          {metrics.length ? (
            <dl className="snow-metrics">
              {metrics.map(([label, value]) => (
                <div key={label}>
                  <dt>{label}</dt>
                  <dd>{value}</dd>
                </div>
              ))}
            </dl>
          ) : null}
        </div>
      )}

      {evidence.limitations.length ? (
        <div className="snow-evidence__limitations">
          <AlertTriangle aria-hidden="true" size={18} />
          <div>
            <strong>Evidence limitations</strong>
            <ul>
              {evidence.limitations.map((limitation) => (
                <li key={limitation}>{limitation}</li>
              ))}
            </ul>
          </div>
        </div>
      ) : (
        <div className="snow-evidence__supported">
          <CheckCircle2 aria-hidden="true" size={18} />
          <span>Typed weather evidence is available for this ski area and window.</span>
        </div>
      )}
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
  const intentRef = useRef(intent);
  intentRef.current = intent;
  const visibleState: EvidenceState =
    state.contextKey === key ? state : { kind: "loading", contextKey: key };
  const retrying = retryRequest > 0 && visibleState.kind === "loading";

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
        <div className="snow-evidence-state" aria-busy="true">
          <RefreshCw aria-hidden="true" size={20} />
          <div>
            <p className="section-label">Snow evidence</p>
            <h2>Loading snow evidence for {skiAreaName}</h2>
            <p>The verdict and recommendation controls remain available.</p>
          </div>
        </div>
      ) : null}

      {visibleState.kind === "error" ? (
        <div className="snow-evidence-state snow-evidence-state--error">
          <AlertTriangle aria-hidden="true" size={20} />
          <div>
            <p className="section-label">Snow evidence</p>
            <h2>Snow evidence could not be loaded</h2>
            <p>{visibleState.message}</p>
          </div>
        </div>
      ) : null}

      {visibleState.kind === "ready" && visibleState.response.status === "unavailable" ? (
        <div className="snow-evidence-state snow-evidence-state--unavailable">
          <AlertTriangle aria-hidden="true" size={20} />
          <div>
            <p className="section-label">Snow evidence</p>
            <h2>Snow evidence unavailable</h2>
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
          </div>
        </div>
      ) : null}

      {visibleState.kind === "ready" && visibleState.response.status === "available" ? (
        <AvailableEvidence response={visibleState.response} />
      ) : null}

      {visibleState.kind === "error" || retryRequest > 0 ? (
        <button
          type="button"
          className="secondary-card-action snow-evidence__retry"
          aria-disabled={retrying}
          onClick={() => {
            if (retrying) return;
            if (visibleState.kind === "ready") deleteWeatherEvidenceCache(key);
            setRetryRequest((current) => current + 1);
          }}
        >
          <RefreshCw aria-hidden="true" size={17} />
          {visibleState.kind === "error"
            ? "Retry snow evidence"
            : retrying
              ? "Retrying snow evidence"
              : "Reload snow evidence"}
        </button>
      ) : null}
    </section>
  );
}
