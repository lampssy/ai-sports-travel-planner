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
import { apiErrorMessage } from "../apiErrors";
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
import { weatherEvidencePresentation } from "./searchPresentation";

type AvailableResponse = Extract<SearchWeatherEvidenceResponse, { status: "available" }>;
type EvidenceState =
  | { kind: "loading"; contextKey: string }
  | { kind: "error"; contextKey: string; message: string }
  | { kind: "ready"; contextKey: string; response: SearchWeatherEvidenceResponse };

type EvidenceRetryAttempt = {
  contextKey: string;
  requestId: number;
  pending: boolean;
};

export type WeatherEvidenceLoader = (
  request: SearchWeatherEvidenceRequest,
  signal?: AbortSignal,
) => Promise<SearchWeatherEvidenceResponse>;

const LazySnowEvidenceChart = lazy(() =>
  import("./SnowEvidenceChart").then((module) => ({
    default: module.SnowEvidenceChart,
  })),
);

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
        <div
          className="snow-values__scroll"
          role="region"
          aria-label={`${mode === "forecast" ? "Forecast" : "Historical"} weather values. Scroll horizontally to view all values.`}
          tabIndex={0}
        >
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

function WeatherEvidenceSummary({
  response,
}: {
  response: SearchWeatherEvidenceResponse;
}) {
  const presentation = weatherEvidencePresentation(response);
  return (
    <dl className="snow-evidence__summary" aria-label="Weather evidence summary">
      <div><dt>Source</dt><dd>{presentation.sourceType}</dd></div>
      <div><dt>Data dates</dt><dd>{presentation.sourceCurrency}</dd></div>
      <div><dt>Coverage</dt><dd>{presentation.coverage}</dd></div>
      <div><dt>Expected conditions</dt><dd>{presentation.expectedConditions}</dd></div>
      <div><dt>Main limitation</dt><dd>{presentation.mainLimitation}</dd></div>
    </dl>
  );
}

function AvailableEvidence({ response }: { response: AvailableResponse }) {
  const { evidence } = response;
  const isForecastAssisted = evidence.mode === "forecast_assisted";
  const historical = evidence.historical;
  const metrics = evidenceMetrics(response);
  const presentation = weatherEvidencePresentation(response);
  const additionalLimitations = evidence.limitations.filter(
    (limitation) => limitation !== presentation.mainLimitation,
  );
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
          {presentation.sourceType}
          </Badge>
        )}
      />

      <div className="snow-evidence__context" aria-label="Weather evidence elevation">
        <strong>{elevation}</strong>
      </div>

      <WeatherEvidenceSummary response={response} />

      <EvidenceExplorer
        response={response}
        historicalSummary={<div className="snow-metrics" aria-label="Historical snow and weather summary">
        {metrics.map((metric) => (
          <MetricTile key={metric.label} {...metric} />
        ))}
        </div>}
      />

      {additionalLimitations.length ? (
        <Alert variant="warning" className="snow-evidence__limitations">
          <div>
            <strong>Evidence limitations</strong>
            <ul>
              {additionalLimitations.map((limitation, index) => (
                <li key={`${limitation}-${index}`}>{limitation}</li>
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
  onResponseChange,
}: {
  intent: SearchIntent;
  skiAreaId: string;
  skiAreaName: string;
  loadEvidence?: WeatherEvidenceLoader;
  onResponseChange?: (response: SearchWeatherEvidenceResponse | null) => void;
}) {
  const key = useMemo(
    () => weatherEvidenceCacheKey(skiAreaId, intent.constraints.travel_window),
    [intent.constraints.travel_window, skiAreaId],
  );
  const [state, setState] = useState<EvidenceState>({
    kind: "loading",
    contextKey: key,
  });
  const [retryAttempt, setRetryAttempt] = useState<EvidenceRetryAttempt | null>(
    null,
  );
  const requestIdentity = useRef(0);
  const retryRequestIdentity = useRef(0);
  const retryAttemptRef = useRef<Omit<EvidenceRetryAttempt, "pending"> | null>(
    null,
  );
  const retryButtonRef = useRef<HTMLButtonElement>(null);
  const reloadButtonRef = useRef<HTMLButtonElement>(null);
  const intentRef = useRef(intent);
  intentRef.current = intent;
  const visibleState: EvidenceState =
    state.contextKey === key ? state : { kind: "loading", contextKey: key };
  const retrying =
    retryAttempt?.contextKey === key && retryAttempt.pending;
  const retryRequestId =
    retryAttempt?.contextKey === key ? retryAttempt.requestId : 0;

  useEffect(() => {
    onResponseChange?.(
      visibleState.kind === "ready" ? visibleState.response : null,
    );
  }, [onResponseChange, visibleState]);

  const retryEvidence = (clearCache: boolean) => {
    if (retryAttemptRef.current?.contextKey === key) return;
    if (clearCache) deleteWeatherEvidenceCache(key);
    const requestId = ++retryRequestIdentity.current;
    retryAttemptRef.current = { contextKey: key, requestId };
    setRetryAttempt({ contextKey: key, requestId, pending: true });
  };

  useEffect(() => {
    if (
      retryAttempt?.contextKey !== key ||
      retryAttempt.pending ||
      visibleState.kind !== "ready"
    ) {
      return;
    }
    if (visibleState.response.status === "available") {
      reloadButtonRef.current?.focus({ preventScroll: true });
    } else {
      retryButtonRef.current?.focus({ preventScroll: true });
    }
  }, [key, retryAttempt, visibleState]);

  useEffect(() => {
    const activeRetry =
      retryRequestId > 0 &&
      retryAttemptRef.current?.contextKey === key &&
      retryAttemptRef.current.requestId === retryRequestId
        ? { contextKey: key, requestId: retryRequestId }
        : null;
    const completeActiveRetry = () => {
      if (
        !activeRetry ||
        retryAttemptRef.current?.contextKey !== activeRetry.contextKey ||
        retryAttemptRef.current.requestId !== activeRetry.requestId
      ) {
        return;
      }
      retryAttemptRef.current = null;
      setRetryAttempt((current) =>
        current?.contextKey === activeRetry.contextKey &&
        current.requestId === activeRetry.requestId
          ? { ...current, pending: false }
          : current,
      );
    };
    const cached = readWeatherEvidenceCache(key);
    if (cached) {
      setState({ kind: "ready", contextKey: key, response: cached });
      return;
    }

    const controller = new AbortController();
    const identity = ++requestIdentity.current;
    if (!(activeRetry && state.contextKey === key)) {
      setState({ kind: "loading", contextKey: key });
    }
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
        completeActiveRetry();
        setState({ kind: "ready", contextKey: key, response });
      })
      .catch((caught) => {
        if (controller.signal.aborted || requestIdentity.current !== identity) return;
        completeActiveRetry();
        setState({
          kind: "error",
          contextKey: key,
          message: apiErrorMessage("weather", caught),
        });
      });

    return () => {
      controller.abort();
      if (requestIdentity.current === identity) requestIdentity.current += 1;
      if (
        activeRetry &&
        retryAttemptRef.current?.contextKey === activeRetry.contextKey &&
        retryAttemptRef.current.requestId === activeRetry.requestId
      ) {
        retryAttemptRef.current = null;
      }
      if (activeRetry) {
        setRetryAttempt((current) =>
          current?.contextKey === activeRetry.contextKey &&
          current.requestId === activeRetry.requestId
            ? null
            : current,
        );
      }
    };
  }, [key, loadEvidence, retryRequestId, skiAreaId]);

  return (
    <section className="dossier-section snow-evidence" id="snow-evidence">
      {visibleState.kind === "ready" &&
      visibleState.response.status === "available" ? (
        <p className="sr-only" role="status" aria-live="polite" aria-atomic="true">
          {statusAnnouncement(visibleState, skiAreaName)}
        </p>
      ) : null}

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
          retrying={retrying}
          retryControlRef={retryButtonRef}
          onRetry={() => retryEvidence(false)}
          className="snow-evidence-state"
        />
      ) : null}

      {visibleState.kind === "ready" && visibleState.response.status === "unavailable" ? (
        <div className="snow-evidence-state">
          {visibleState.response.unavailable_reason === "travel_window_missing" ? (
            <AsyncState
              state="empty"
              title="Add travel dates to assess weather"
              message="Choose travel dates to see weather conditions for this ski area."
            />
          ) : (
            <AsyncState
              state="error"
              title="Snow evidence unavailable"
              retryLabel="Check again"
              retrying={retrying}
              retryControlRef={retryButtonRef}
              onRetry={() => retryEvidence(true)}
              message="Snowcast could not find enough reliable historical data for this ski area and trip window."
            />
          )}
          <WeatherEvidenceSummary response={visibleState.response} />
        </div>
      ) : null}

      {visibleState.kind === "ready" && visibleState.response.status === "available" ? (
        <AvailableEvidence response={visibleState.response} />
      ) : null}

      {visibleState.kind === "ready" &&
      visibleState.response.status === "available" &&
      retryAttempt?.contextKey === key ? (
        <Action
          ref={reloadButtonRef}
          variant="secondary"
          size="sm"
          className="snow-evidence__retry"
          aria-disabled={retrying}
          onClick={() => {
            retryEvidence(true);
          }}
        >
          <RefreshCw aria-hidden="true" size={17} />
          {retrying ? "Retrying snow evidence" : "Reload snow evidence"}
        </Action>
      ) : null}
    </section>
  );
}
