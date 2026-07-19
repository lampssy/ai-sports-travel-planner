import { ArrowLeft } from "lucide-react";
import { useEffect, useRef, useState, type ReactNode } from "react";

import type { CurrentTrip, CurrentTripSummary } from "../types";
import { AsyncState } from "./AsyncState";
import { SnowcastLogo } from "./SnowcastLogo";

export function AppShell({
  children,
  active,
  onSearch,
  onCurrentTrip,
  header,
}: {
  children: ReactNode;
  active: "search" | "currentTrip";
  onSearch: () => void;
  onCurrentTrip: () => void;
  header?: ReactNode;
}) {
  return (
    <div className="app-shell">
      {header ?? (
        <header className="app-nav">
          <div className="app-canvas app-nav__inner">
            <button
              type="button"
              className="logo-button"
              aria-label="Go to search"
              onClick={onSearch}
            >
              <SnowcastLogo />
            </button>
            <nav aria-label="Primary navigation" className="app-nav__links">
              <button
                type="button"
                className="nav-link"
                aria-current={active === "search" ? "page" : undefined}
                onClick={onSearch}
              >
                Search
              </button>
              <button
                type="button"
                className="nav-link"
                aria-current={active === "currentTrip" ? "page" : undefined}
                onClick={onCurrentTrip}
              >
                Current trip
              </button>
            </nav>
          </div>
        </header>
      )}
      {children}
    </div>
  );
}

export function CurrentTripView({
  trip,
  summary,
  tripLoadError,
  summaryLoadError,
  tripLoading,
  summaryLoading,
  tripRecoveryRequest,
  summaryRecoveryRequest,
  clearError,
  onBack,
  onRetryTripLoad,
  onRetrySummaryLoad,
  onClear,
}: {
  trip: CurrentTrip | null;
  summary: CurrentTripSummary | null;
  tripLoadError: string | null;
  summaryLoadError: string | null;
  tripLoading: boolean;
  summaryLoading: boolean;
  tripRecoveryRequest: number;
  summaryRecoveryRequest: number;
  clearError: string | null;
  onBack: () => void;
  onRetryTripLoad: () => void;
  onRetrySummaryLoad: () => void;
  onClear: () => void;
}) {
  const tripHeadingRef = useRef<HTMLHeadingElement>(null);
  const conditionsRef = useRef<HTMLDivElement>(null);
  const handledTripRecoveryRef = useRef(tripRecoveryRequest);
  const handledSummaryRecoveryRef = useRef(summaryRecoveryRequest);
  const [tripAnnouncementRequest, setTripAnnouncementRequest] = useState<
    number | null
  >(null);
  const [summaryAnnouncementRequest, setSummaryAnnouncementRequest] = useState<
    number | null
  >(null);

  useEffect(() => {
    if (
      tripRecoveryRequest === handledTripRecoveryRef.current ||
      tripLoading ||
      tripLoadError ||
      !trip
    ) {
      return;
    }
    handledTripRecoveryRef.current = tripRecoveryRequest;
    setTripAnnouncementRequest(tripRecoveryRequest);
    tripHeadingRef.current?.focus({ preventScroll: true });
  }, [trip, tripLoadError, tripLoading, tripRecoveryRequest]);

  useEffect(() => {
    if (
      summaryRecoveryRequest === handledSummaryRecoveryRef.current ||
      summaryLoading ||
      summaryLoadError ||
      !summary
    ) {
      return;
    }
    handledSummaryRecoveryRef.current = summaryRecoveryRequest;
    setSummaryAnnouncementRequest(summaryRecoveryRequest);
    conditionsRef.current?.focus({ preventScroll: true });
  }, [summary, summaryLoadError, summaryLoading, summaryRecoveryRequest]);

  return (
    <main className="app-canvas current-trip-page">
      <button type="button" onClick={onBack} className="text-action">
        <ArrowLeft aria-hidden="true" size={17} />
        Back to search
      </button>
      <section className="current-trip-panel">
        <p className="eyebrow">Trip companion</p>
        {tripAnnouncementRequest !== null ? (
          <p
            key={`trip-recovery-${tripAnnouncementRequest}`}
            className="sr-only"
            role="status"
            aria-live="polite"
            aria-atomic="true"
          >
            Saved trip loaded.
          </p>
        ) : null}
        {summaryAnnouncementRequest !== null ? (
          <p
            key={`summary-recovery-${summaryAnnouncementRequest}`}
            className="sr-only"
            role="status"
            aria-live="polite"
            aria-atomic="true"
          >
            Current conditions updated.
          </p>
        ) : null}
        {tripLoadError ? (
          <AsyncState
            state="error"
            title={
              trip
                ? "Saved trip could not be refreshed"
                : "Saved trip could not be loaded"
            }
            message={tripLoadError}
            retryLabel="Retry saved trip"
            retrying={tripLoading}
            onRetry={onRetryTripLoad}
          />
        ) : null}
        {trip ? (
          <>
            <h1 ref={tripHeadingRef} tabIndex={-1}>{trip.ski_region_name}</h1>
            <p className="current-trip-panel__entities">
              {trip.stay_base_name} · {trip.focus_ski_area_name} ·{" "}
              {trip.lift_pass_product_name}
            </p>
            {summary ? (
              <div
                ref={conditionsRef}
                className="current-trip-summary"
                role="region"
                aria-label="Current conditions"
                tabIndex={-1}
              >
                <p className="current-trip-summary__title">Current conditions</p>
                <p>{summary.current_conditions.weather_summary}</p>
                <p className="muted-copy">{summary.delta.summary}</p>
              </div>
            ) : null}
            {summaryLoadError ? (
              <AsyncState
                state="error"
                title="Current conditions could not be updated"
                message={summaryLoadError}
                retryLabel="Retry current conditions"
                retrying={summaryLoading}
                onRetry={onRetrySummaryLoad}
              />
            ) : null}
            {clearError ? (
              <p className="error-copy" role="alert">
                {clearError}
              </p>
            ) : null}
            <button type="button" onClick={onClear} className="danger-button">
              Clear current trip
            </button>
          </>
        ) : tripLoadError ? null : (
          <p className="current-trip-panel__empty">
            Sign in to the Snowcast mobile app and save a trip option to track it.
          </p>
        )}
      </section>
    </main>
  );
}
