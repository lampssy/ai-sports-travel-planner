# ruff: noqa: E501

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from html import escape

from fastapi import HTTPException

from app.data.repositories import (
    ResortConditionHistoryRepository,
    ResortConditionsRepository,
    ResortRepository,
    get_condition_history_repository,
    get_raw_weather_history_repository,
    is_condition_fresh,
)
from app.domain.models import (
    Destination,
    PlanningEvidenceProfile,
    ProvenanceInfo,
    ResortConditions,
    SkiArea,
    WeatherEvidenceMetrics,
)
from app.domain.planning import (
    MONTH_NAMES,
    derive_planning_assessment,
    derive_weather_evidence_metrics,
)
from app.domain.planning_policy import DEFAULT_PLANNING_HEURISTIC_POLICY

POLICY = DEFAULT_PLANNING_HEURISTIC_POLICY


@dataclass(frozen=True)
class PublicCalendarMonth:
    month: int
    month_name: str
    summary: str
    snow_confidence_label: str
    availability_status: str
    evidence_count: int
    evidence_profile: str
    basis_summary: str
    updated_at: str | None
    score: float
    weather_metrics: WeatherEvidenceMetrics | None


@dataclass(frozen=True)
class PublicResortPage:
    resort: Destination
    primary_ski_area: SkiArea
    current_conditions: ResortConditions
    current_provenance: ProvenanceInfo
    calendar_months: tuple[PublicCalendarMonth, ...]
    canonical_url: str
    planner_url: str


def render_public_resort_page(
    *,
    resort_id: str,
    base_url: str,
) -> str:
    page = build_public_resort_page(
        resort_id=resort_id,
        base_url=base_url,
    )
    return _render_html(page)


def render_sitemap_xml(*, base_url: str) -> str:
    urls = [
        f"{_xml(base_url)}/ski-resorts/{_xml(resort.resort_id)}"
        for resort in ResortRepository().list_resorts()
    ]
    url_entries = "\n".join(f"  <url><loc>{url}</loc></url>" for url in urls)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{url_entries}\n"
        "</urlset>\n"
    )


def render_robots_txt(*, base_url: str) -> str:
    return f"User-agent: *\nAllow: /\nSitemap: {base_url}/sitemap.xml\n"


def build_public_resort_page(
    *,
    resort_id: str,
    base_url: str,
) -> PublicResortPage:
    resort_repository = ResortRepository()
    resort = resort_repository.get_resort_by_id(resort_id)
    if resort is None:
        raise HTTPException(status_code=404, detail="Unknown resort_id")
    if not resort.ski_areas:
        raise HTTPException(status_code=404, detail="Resort has no ski area metadata")

    primary_ski_area = resort.ski_areas[0]
    conditions_repository = ResortConditionsRepository()
    current_conditions = conditions_repository.get_conditions_for_ski_area(
        primary_ski_area.name
    )
    current_provenance = _conditions_provenance(current_conditions)
    active_conditions = current_conditions or _fallback_conditions(
        primary_ski_area.name
    )
    calendar_months = _build_calendar_months(
        resort=resort,
        ski_area=primary_ski_area,
    )

    return PublicResortPage(
        resort=resort,
        primary_ski_area=primary_ski_area,
        current_conditions=active_conditions,
        current_provenance=current_provenance,
        calendar_months=calendar_months,
        canonical_url=f"{base_url}/ski-resorts/{resort.resort_id}",
        planner_url=f"{base_url}/",
    )


def _build_calendar_months(
    *,
    resort: Destination,
    ski_area: SkiArea,
) -> tuple[PublicCalendarMonth, ...]:
    history_repository = get_condition_history_repository()
    raw_history_repository = get_raw_weather_history_repository()
    snapshots = _list_planning_snapshots(
        history_repository=history_repository,
        destination=resort,
        ski_area=ski_area,
    )
    raw_observations = _list_raw_weather_observations(
        raw_history_repository=raw_history_repository,
        destination=resort,
        ski_area=ski_area,
    )

    months: list[PublicCalendarMonth] = []
    for month in _season_months(
        resort.season_start_month,
        resort.season_end_month,
    ):
        assessment = derive_planning_assessment(
            resort=ski_area,
            travel_month=month,
            snapshots=snapshots,
            raw_weather_observations=raw_observations,
        )
        weather_metrics = derive_weather_evidence_metrics(
            raw_weather_observations=raw_observations,
            travel_month=month,
        )
        provenance = _planning_provenance(
            evidence_count=assessment.evidence_count,
            latest_snapshot_at=assessment.latest_snapshot_at,
            evidence_source=assessment.evidence_source,
            evidence_profile=assessment.evidence_profile,
        )
        months.append(
            PublicCalendarMonth(
                month=month,
                month_name=MONTH_NAMES[month],
                summary=assessment.planning_summary,
                snow_confidence_label=assessment.conditions.snow_confidence_label,
                availability_status=assessment.conditions.availability_status,
                evidence_count=assessment.evidence_count,
                evidence_profile=assessment.evidence_profile,
                basis_summary=provenance.basis_summary,
                updated_at=provenance.updated_at,
                score=assessment.conditions.snow_confidence_score,
                weather_metrics=weather_metrics,
            )
        )

    return tuple(months)


def _list_planning_snapshots(
    *,
    history_repository: ResortConditionHistoryRepository,
    destination: Destination,
    ski_area: SkiArea,
) -> tuple:
    snapshots = history_repository.list_snapshots_for_resort(ski_area.ski_area_id)
    if snapshots or ski_area.ski_area_id == destination.resort_id:
        return snapshots
    return history_repository.list_snapshots_for_resort(destination.resort_id)


def _list_raw_weather_observations(
    *,
    raw_history_repository,
    destination: Destination,
    ski_area: SkiArea,
) -> tuple:
    observations = raw_history_repository.list_observations_for_resort(
        ski_area.ski_area_id,
        elevation_band="mid",
    )
    if observations or ski_area.ski_area_id == destination.resort_id:
        return observations
    return raw_history_repository.list_observations_for_resort(
        destination.resort_id,
        elevation_band="mid",
    )


def _season_months(start_month: int, end_month: int) -> tuple[int, ...]:
    if start_month <= end_month:
        return tuple(range(start_month, end_month + 1))
    return tuple(range(start_month, 13)) + tuple(range(1, end_month + 1))


def _fallback_conditions(resort_name: str) -> ResortConditions:
    return ResortConditions(
        resort_name=resort_name,
        snow_confidence_score=0.4,
        availability_status="limited",
        weather_summary="No live conditions signal available for this ski area.",
        conditions_score=0.4,
    )


def _conditions_provenance(
    conditions: ResortConditions | None,
) -> ProvenanceInfo:
    if conditions is None or (
        conditions.updated_at is None and conditions.source is None
    ):
        return ProvenanceInfo(
            source_name=None,
            source_type="estimated",
            updated_at=None,
            freshness_status="unknown",
            basis_summary=(
                "Using an estimated fallback because no live forecast signal is "
                "available for this resort."
            ),
        )

    freshness_status = "unknown"
    if conditions.updated_at is not None:
        freshness_status = "fresh" if is_condition_fresh(conditions) else "stale"

    return ProvenanceInfo(
        source_name=conditions.source or "open-meteo",
        source_type="forecast",
        updated_at=conditions.updated_at,
        freshness_status=freshness_status,
        basis_summary=(
            "Using a current forecast-based conditions signal from the latest "
            "weather refresh."
        ),
    )


def _planning_provenance(
    *,
    evidence_count: int,
    latest_snapshot_at: str | None,
    evidence_source: str,
    evidence_profile: PlanningEvidenceProfile,
) -> ProvenanceInfo:
    text_policy = POLICY.text
    if evidence_profile == "forecast_assisted":
        profile_text = text_policy.forecast_assisted
        source_name = profile_text.source_name
        basis_summary = profile_text.provenance_summary
    elif evidence_profile == "archive_backed":
        profile_text = text_policy.archive_backed
        source_name = profile_text.source_name
        basis_summary = profile_text.provenance_summary
    elif evidence_source == "snapshot_history":
        source_name = text_policy.snapshot_fallback_source_name
        basis_summary = text_policy.snapshot_fallback_provenance_summary
    else:
        profile_text = text_policy.fallback_heavy
        source_name = profile_text.source_name
        basis_summary = profile_text.provenance_summary

    return ProvenanceInfo(
        source_name=source_name,
        source_type="estimated",
        updated_at=latest_snapshot_at if evidence_count > 0 else None,
        freshness_status="historical" if evidence_count > 0 else "unknown",
        basis_summary=basis_summary,
        evidence_profile=evidence_profile,
    )


def _render_html(page: PublicResortPage) -> str:
    resort = page.resort
    current = page.current_conditions
    best_months = sorted(
        page.calendar_months,
        key=lambda item: item.score,
        reverse=True,
    )[:3]
    best_months_label = ", ".join(month.month_name for month in best_months)
    title = f"{resort.name} ski resort guide | Snowcast"
    description = (
        f"Snow-aware guide to {resort.name} in {resort.region}, {resort.country}: "
        "current snow signal, best travel months, stay bases, and weather evidence."
    )

    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{_html(title)}</title>
    <meta name="description" content="{_html(description)}" />
    <link rel="canonical" href="{_html(page.canonical_url)}" />
    <meta property="og:type" content="article" />
    <meta property="og:title" content="{_html(title)}" />
    <meta property="og:description" content="{_html(description)}" />
    <meta property="og:url" content="{_html(page.canonical_url)}" />
    <meta name="twitter:card" content="summary" />
    <meta name="twitter:title" content="{_html(title)}" />
    <meta name="twitter:description" content="{_html(description)}" />
    <style>
      :root {{
        --ink: #14202d;
        --slate: #475569;
        --frost: #e5f0f2;
        --alpine: #2f645c;
        --ember: #d6673f;
        --paper: #fbfaf7;
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        color: var(--ink);
        font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        background:
          radial-gradient(circle at top left, rgba(214, 103, 63, 0.16), transparent 28%),
          radial-gradient(circle at 85% 8%, rgba(47, 100, 92, 0.14), transparent 24%),
          linear-gradient(180deg, #f4efe7 0%, #eef5f4 58%, #f7faf9 100%);
      }}
      a {{ color: inherit; }}
      .shell {{ max-width: 1280px; margin: 0 auto; padding: 40px 32px 64px; }}
      .nav {{ display: flex; justify-content: space-between; gap: 16px; align-items: center; margin-bottom: 36px; }}
      .brand {{ color: var(--ember); font-size: 13px; font-weight: 800; letter-spacing: 0.24em; text-transform: uppercase; }}
      .pill {{ display: inline-flex; border-radius: 999px; background: rgba(255,255,255,0.78); border: 1px solid rgba(255,255,255,0.72); padding: 10px 16px; font-weight: 800; text-decoration: none; box-shadow: 0 8px 24px rgba(20,32,45,0.08); }}
      .hero {{ display: grid; grid-template-columns: 1.16fr 0.84fr; gap: 30px; align-items: stretch; }}
      .card {{ border: 1px solid rgba(255,255,255,0.76); border-radius: 34px; background: rgba(255,255,255,0.9); box-shadow: 0 24px 70px rgba(20,32,45,0.12); padding: 30px; }}
      .hero-card {{ background: linear-gradient(135deg, #18222f 0%, #263548 58%, #2f645c 100%); color: white; }}
      .eyebrow {{ color: var(--ember); font-size: 13px; font-weight: 800; letter-spacing: 0.24em; text-transform: uppercase; }}
      .hero-card .eyebrow {{ color: #fed7aa; }}
      h1 {{ margin: 18px 0 16px; font-size: clamp(46px, 8vw, 82px); line-height: 0.92; letter-spacing: -0.055em; }}
      h2 {{ margin: 0 0 14px; font-size: 30px; line-height: 1.05; letter-spacing: -0.03em; }}
      h3 {{ margin: 0 0 10px; font-size: 20px; }}
      p {{ line-height: 1.7; }}
      .lede {{ max-width: 680px; color: #dbe7ea; font-size: 18px; }}
      .summary {{ margin-top: 24px; border-radius: 24px; background: rgba(255,255,255,0.1); padding: 18px; }}
      .metrics {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }}
      .metric {{ border-radius: 22px; background: rgba(229,240,242,0.78); padding: 18px; }}
      .label {{ color: #64748b; font-size: 12px; font-weight: 800; letter-spacing: 0.14em; text-transform: uppercase; }}
      .value {{ margin-top: 7px; font-size: 20px; font-weight: 850; }}
      .grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 24px; margin-top: 24px; }}
      .calendar {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; }}
      .month {{ border: 1px solid #d8e4e8; border-radius: 24px; background: rgba(255,255,255,0.76); padding: 18px; }}
      .month.good {{ border-color: rgba(47,100,92,0.28); background: rgba(229,240,242,0.84); }}
      .month-metrics {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; margin: 16px 0; }}
      .month-stat {{ border-radius: 16px; background: rgba(255,255,255,0.68); padding: 12px; }}
      .month-stat strong {{ display: block; margin-top: 4px; font-size: 16px; }}
      .badge {{ display: inline-flex; border-radius: 999px; background: var(--frost); color: var(--alpine); padding: 7px 11px; font-size: 12px; font-weight: 850; text-transform: uppercase; letter-spacing: 0.1em; }}
      .list {{ display: grid; gap: 12px; }}
      .list-item {{ border-radius: 18px; background: rgba(229,240,242,0.62); padding: 14px 16px; }}
      .muted {{ color: var(--slate); }}
      .cta-row {{ display: flex; gap: 12px; flex-wrap: wrap; margin-top: 24px; }}
      .cta-primary {{ border-radius: 999px; background: var(--ember); color: white; padding: 14px 18px; font-weight: 850; text-decoration: none; }}
      .cta-secondary {{ border-radius: 999px; border: 1px solid #cbd5e1; background: white; color: var(--ink); padding: 14px 18px; font-weight: 850; text-decoration: none; }}
      @media (max-width: 860px) {{
        .hero, .grid, .calendar {{ grid-template-columns: 1fr; }}
        .metrics {{ grid-template-columns: 1fr; }}
        .month-metrics {{ grid-template-columns: 1fr; }}
        .nav {{ align-items: flex-start; flex-direction: column; }}
        .shell {{ padding: 28px 18px 48px; }}
      }}
    </style>
  </head>
  <body>
    <main class="shell">
      <nav class="nav">
        <div class="brand">Snowcast public guide</div>
        <a class="pill" href="{_html(page.planner_url)}">Open planner</a>
      </nav>

      <section class="hero">
        <div class="card hero-card">
          <div class="eyebrow">Ski resort guide</div>
          <h1>{_html(resort.name)}</h1>
          <p class="lede">{_html(resort.name)} is in {_html(resort.region)}, {_html(resort.country)}. Snowcast tracks current snow signals and historical travel-window evidence so you can judge when this resort is most likely to fit.</p>
          <div class="summary">
            <strong>Best current signal:</strong> {_html(current.weather_summary)}
          </div>
          <div class="cta-row">
            <a class="cta-primary" href="{_html(page.planner_url)}">Plan with Snowcast</a>
            <a class="cta-secondary" href="#conditions-calendar">View calendar</a>
          </div>
        </div>

        <aside class="card">
          <h2>Current snow signal</h2>
          <div class="metrics">
            <div class="metric">
              <div class="label">Snow confidence</div>
              <div class="value">{_html(current.snow_confidence_label.title())}</div>
            </div>
            <div class="metric">
              <div class="label">Disruption signal</div>
              <div class="value">{_html(_availability_label(current.availability_status))}</div>
            </div>
            <div class="metric">
              <div class="label">Elevation</div>
              <div class="value">{resort.base_elevation_m}-{resort.summit_elevation_m}m</div>
            </div>
            <div class="metric">
              <div class="label">Season</div>
              <div class="value">{_html(_season_label(resort))}</div>
            </div>
          </div>
          <p class="muted">{_html(page.current_provenance.basis_summary)}</p>
          <p class="muted"><strong>Source:</strong> {_html(page.current_provenance.source_name or "Estimated")} · <strong>Freshness:</strong> {_html(str(page.current_provenance.freshness_status).replace("_", " "))} · <strong>Updated:</strong> {_html(_timestamp_label(page.current_provenance.updated_at))}</p>
        </aside>
      </section>

      <section id="conditions-calendar" class="card" style="margin-top: 24px;">
        <div class="eyebrow">Conditions calendar</div>
        <h2>When {_html(resort.name)} tends to fit best</h2>
        <p class="muted">Historically strongest months: {_html(best_months_label)}. Month cards use archive weather records and seasonal resort traits, while the live forecast stays in the current snow signal above.</p>
        <div class="calendar">
          {_render_calendar(page.calendar_months)}
        </div>
      </section>

      <section class="grid">
        <div class="card">
          <div class="eyebrow">Stay bases</div>
          <h2>Where Snowcast can place you</h2>
          <div class="list">{_render_stay_bases(resort)}</div>
        </div>
        <div class="card">
          <div class="eyebrow">Ski area and rentals</div>
          <h2>Resort facts</h2>
          <div class="list">{_render_ski_areas(resort)}{_render_rentals(resort)}</div>
        </div>
      </section>

      <section class="card" style="margin-top: 24px;">
        <div class="eyebrow">Trust and provenance</div>
        <h2>What this guide is based on</h2>
        <p class="muted">This page is generated from curated resort metadata, current conditions refresh data, archive weather records, and deterministic planning assessments. It is not hand-written by an LLM and updates when the underlying resort or weather data changes.</p>
      </section>
    </main>
  </body>
</html>
"""


def _render_calendar(months: tuple[PublicCalendarMonth, ...]) -> str:
    return "\n".join(
        f"""
          <article class="month {"good" if month.snow_confidence_label == "good" else ""}">
            <span class="badge">{_html(month.snow_confidence_label)}</span>
            <h3>{_html(month.month_name)}</h3>
            <p>{_html(_calendar_summary(month))}</p>
            {_render_weather_metrics(month.weather_metrics)}
            <p class="muted">{_html(_historical_basis(month))}</p>
          </article>
        """
        for month in months
    )


def _render_weather_metrics(metrics: WeatherEvidenceMetrics | None) -> str:
    if metrics is None:
        return """
            <div class="month-metrics">
              <div class="month-stat">
                <span class="label">Mid-mountain snow</span>
                <strong>Not enough data</strong>
              </div>
              <div class="month-stat">
                <span class="label">Historical seasons</span>
                <strong>Limited</strong>
              </div>
            </div>
        """

    snow_depth = (
        f"{metrics.average_snow_depth_cm:.0f} cm"
        if metrics.average_snow_depth_cm is not None
        else "Not available"
    )
    return f"""
            <div class="month-metrics">
              <div class="month-stat">
                <span class="label">Mid-mountain snow</span>
                <strong>{_html(snow_depth)}</strong>
              </div>
              <div class="month-stat">
                <span class="label">Avg high</span>
                <strong>{metrics.average_max_temperature_c:.1f}°C</strong>
              </div>
              <div class="month-stat">
                <span class="label">Daily snowfall</span>
                <strong>{metrics.average_daily_snowfall_cm:.1f} cm</strong>
              </div>
              <div class="month-stat">
                <span class="label">Historical seasons</span>
                <strong>{metrics.evidence_years}</strong>
              </div>
            </div>
        """


def _render_stay_bases(resort: Destination) -> str:
    return "\n".join(
        f"""
        <div class="list-item">
          <strong>{_html(stay_base.name)}</strong>
          <div class="muted">{_html(stay_base.price_range)} nightly stay estimate · {_html(stay_base.quality.title())} quality tier · {_html(stay_base.lift_distance.title())} lift access · supports {_html(", ".join(stay_base.supported_skill_levels))}</div>
        </div>
        """
        for stay_base in resort.stay_bases
    )


def _render_ski_areas(resort: Destination) -> str:
    return "\n".join(
        f"""
        <div class="list-item">
          <strong>{_html(ski_area.name)}</strong>
          <div class="muted">{ski_area.base_elevation_m}-{ski_area.summit_elevation_m}m · typical season {_html(MONTH_NAMES[ski_area.season_start_month])}-{_html(MONTH_NAMES[ski_area.season_end_month])}</div>
        </div>
        """
        for ski_area in resort.ski_areas
    )


def _render_rentals(resort: Destination) -> str:
    return "\n".join(
        f"""
        <div class="list-item">
          <strong>{_html(rental.name)}</strong>
          <div class="muted">{_html(rental.price_range)} daily rental estimate · {_html(rental.quality.title())} quality tier · {_html(rental.lift_distance.title())} lift access</div>
        </div>
        """
        for rental in resort.rentals
    )


def _season_label(resort: Destination) -> str:
    return (
        f"{MONTH_NAMES[resort.season_start_month]}-"
        f"{MONTH_NAMES[resort.season_end_month]}"
    )


def _availability_label(value: str) -> str:
    return {
        "open": "Low disruption risk",
        "limited": "Some disruption risk",
        "temporarily_closed": "High disruption risk",
        "out_of_season": "Out of season",
    }.get(value, value.replace("_", " ").title())


def _calendar_summary(month: PublicCalendarMonth) -> str:
    signal = {
        "good": "Historically strong snow signal",
        "fair": "Historically mixed snow signal",
        "poor": "Historically weak snow signal",
    }.get(month.snow_confidence_label, "Historical snow signal is limited")
    if (
        month.weather_metrics
        and month.weather_metrics.average_snow_depth_cm is not None
    ):
        return (
            f"{signal} with mid-mountain typical snow depth around "
            f"{month.weather_metrics.average_snow_depth_cm:.0f} cm."
        )
    return f"{signal}; snow-depth history is limited for this month."


def _historical_basis(month: PublicCalendarMonth) -> str:
    if month.weather_metrics is None:
        return (
            "Using seasonal resort traits because archive weather coverage is limited."
        )
    return _historical_data_label(month.weather_metrics.latest_observed_on)


def _timestamp_label(value: str | None) -> str:
    if not value:
        return "not available"
    try:
        timestamp = datetime.fromisoformat(value)
    except ValueError:
        return value
    if timestamp.tzinfo is not None:
        timestamp = timestamp.astimezone(UTC)
    return (
        f"{MONTH_NAMES[timestamp.month][:3]} {timestamp.day}, "
        f"{timestamp.year}, {timestamp:%H:%M} UTC"
    )


def _historical_data_label(value: str | None) -> str:
    if not value:
        return "Historical data unavailable"
    try:
        observed_on = date.fromisoformat(value)
    except ValueError:
        return "Historical data available"
    return f"Historical data through {MONTH_NAMES[observed_on.month][:3]} {observed_on.year}"


def _html(value: object) -> str:
    return escape(str(value), quote=True)


def _xml(value: object) -> str:
    return escape(str(value), quote=True)
