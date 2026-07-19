# ruff: noqa: E501

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from html import escape

from fastapi import HTTPException

from app.data.catalog_repository import CatalogRepository
from app.data.repositories import (
    ResortConditionHistoryRepository,
    ResortConditionsRepository,
    get_condition_history_repository,
    get_raw_weather_history_repository,
    is_condition_fresh,
)
from app.domain.catalog import RentalDisplayFact, SkiArea, StayBase, StayDestination
from app.domain.catalog_graph import CatalogGraph
from app.domain.models import (
    PlanningEvidenceProfile,
    ProvenanceInfo,
    ResortConditions,
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
class PublicSkiAreaSection:
    ski_area: SkiArea
    current_conditions: ResortConditions
    current_provenance: ProvenanceInfo
    calendar_months: tuple[PublicCalendarMonth, ...]


@dataclass(frozen=True)
class PublicStayBaseView:
    stay_base: StayBase
    ski_area_names: tuple[str, ...]


@dataclass(frozen=True)
class PublicDestinationPage:
    destination: StayDestination
    ski_region_name: str
    stay_bases: tuple[PublicStayBaseView, ...]
    ski_area_sections: tuple[PublicSkiAreaSection, ...]
    rentals: tuple[RentalDisplayFact, ...]
    canonical_url: str
    planner_url: str


def render_public_destination_page(
    *,
    stay_destination_id: str,
    base_url: str,
) -> str:
    page = build_public_destination_page(
        stay_destination_id=stay_destination_id,
        base_url=base_url,
    )
    return _render_html(page)


def render_sitemap_xml(*, base_url: str) -> str:
    urls = [
        (f"{_xml(base_url)}/ski-destinations/{_xml(destination.stay_destination_id)}")
        for destination in CatalogRepository().get_snapshot().stay_destinations
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


def build_public_destination_page(
    *,
    stay_destination_id: str,
    base_url: str,
) -> PublicDestinationPage:
    graph = CatalogGraph.from_snapshot(CatalogRepository().get_snapshot())
    destination = graph.destinations_by_id.get(stay_destination_id)
    if destination is None:
        raise HTTPException(status_code=404, detail="Unknown stay_destination_id")
    region = graph.regions_by_id[destination.trip_market_region_id]
    bases = tuple(
        sorted(
            (
                base
                for base in graph.snapshot.stay_bases
                if base.stay_destination_id == stay_destination_id
            ),
            key=lambda item: item.name,
        )
    )
    area_ids: set[str] = set()
    stay_base_views: list[PublicStayBaseView] = []
    for base in bases:
        accessible_areas = tuple(
            sorted(
                (
                    graph.areas_by_id[access.ski_area_id]
                    for access in graph.accesses_by_base_id.get(base.stay_base_id, ())
                ),
                key=lambda item: item.name,
            )
        )
        area_ids.update(area.ski_area_id for area in accessible_areas)
        stay_base_views.append(
            PublicStayBaseView(
                stay_base=base,
                ski_area_names=tuple(area.name for area in accessible_areas),
            )
        )
    if not area_ids:
        raise HTTPException(
            status_code=404,
            detail="Stay destination has no accessible ski areas",
        )

    conditions_repository = ResortConditionsRepository()
    sections = tuple(
        _build_ski_area_section(
            ski_area=graph.areas_by_id[area_id],
            conditions_repository=conditions_repository,
        )
        for area_id in sorted(area_ids, key=lambda item: graph.areas_by_id[item].name)
    )

    return PublicDestinationPage(
        destination=destination,
        ski_region_name=region.name,
        stay_bases=tuple(stay_base_views),
        ski_area_sections=sections,
        rentals=graph.rentals_by_destination_id.get(stay_destination_id, ()),
        canonical_url=f"{base_url}/ski-destinations/{stay_destination_id}",
        planner_url=f"{base_url}/",
    )


def _build_ski_area_section(
    *,
    ski_area: SkiArea,
    conditions_repository: ResortConditionsRepository,
) -> PublicSkiAreaSection:
    stored_conditions = conditions_repository.get_conditions_for_ski_area(
        ski_area.ski_area_id
    )
    return PublicSkiAreaSection(
        ski_area=ski_area,
        current_conditions=stored_conditions or _fallback_conditions(ski_area.name),
        current_provenance=_conditions_provenance(stored_conditions),
        calendar_months=_build_calendar_months(ski_area=ski_area),
    )


def _build_calendar_months(
    *,
    ski_area: SkiArea,
) -> tuple[PublicCalendarMonth, ...]:
    history_repository = get_condition_history_repository()
    raw_history_repository = get_raw_weather_history_repository()
    snapshots = _list_planning_snapshots(
        history_repository=history_repository,
        ski_area=ski_area,
    )
    raw_observations = _list_raw_weather_observations(
        raw_history_repository=raw_history_repository,
        ski_area=ski_area,
    )

    months: list[PublicCalendarMonth] = []
    for month in _season_months(
        ski_area.season_start_month,
        ski_area.season_end_month,
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
    ski_area: SkiArea,
) -> tuple:
    return history_repository.list_snapshots_for_ski_area(ski_area.ski_area_id)


def _list_raw_weather_observations(
    *,
    raw_history_repository,
    ski_area: SkiArea,
) -> tuple:
    return raw_history_repository.list_observations_for_ski_area(
        ski_area.ski_area_id,
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


def _render_html(page: PublicDestinationPage) -> str:
    destination = page.destination
    title = f"{destination.name} ski destination guide | Snowcast"
    description = (
        f"Snow-aware guide to {destination.name} in {destination.region}, "
        f"{destination.country}, with separate conditions for each accessible ski area."
    )
    first_area_id = page.ski_area_sections[0].ski_area.ski_area_id
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
      :root {{ --ink: #14202d; --slate: #526174; --frost: #e5f0f2; --alpine: #176b5b; --ember: #d6532f; --paper: #f6f8f7; }}
      * {{ box-sizing: border-box; }}
      body {{ margin: 0; color: var(--ink); font-family: Inter, ui-sans-serif, system-ui, sans-serif; background: var(--paper); }}
      a {{ color: inherit; }}
      .shell {{ max-width: 1180px; margin: 0 auto; padding: 36px 28px 64px; }}
      .nav, .hero, .grid, .metrics, .calendar {{ display: grid; gap: 18px; }}
      .nav {{ grid-template-columns: 1fr auto; align-items: center; margin-bottom: 28px; }}
      .hero {{ grid-template-columns: 1.3fr 0.7fr; margin-bottom: 22px; }}
      .grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); margin-top: 22px; }}
      .metrics {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .calendar {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
      .card {{ border: 1px solid #d8e1e4; border-radius: 8px; background: white; padding: 26px; box-shadow: 0 12px 35px rgba(20,32,45,.07); }}
      .hero-main {{ background: #102a43; color: white; }}
      .brand, .eyebrow, .label {{ color: var(--ember); font-size: 12px; font-weight: 800; letter-spacing: .14em; text-transform: uppercase; }}
      .pill, .cta-primary, .cta-secondary {{ display: inline-flex; align-items: center; padding: 11px 15px; border-radius: 6px; font-weight: 800; text-decoration: none; }}
      .pill, .cta-secondary {{ border: 1px solid #cbd5df; background: white; }}
      .cta-primary {{ background: var(--ember); color: white; }}
      .cta-row {{ display: flex; gap: 10px; flex-wrap: wrap; margin-top: 22px; }}
      h1 {{ margin: 16px 0 14px; font-size: 56px; line-height: 1; letter-spacing: 0; }}
      h2 {{ margin: 0 0 12px; font-size: 28px; letter-spacing: 0; }}
      h3 {{ margin: 8px 0; font-size: 19px; }}
      p {{ line-height: 1.6; }}
      .lede {{ color: #d9e6ee; font-size: 18px; }}
      .metric, .month, .list-item {{ border: 1px solid #dce6e8; border-radius: 7px; background: #f8fbfb; padding: 15px; }}
      .value {{ margin-top: 6px; font-size: 19px; font-weight: 800; }}
      .area-section {{ margin-top: 22px; }}
      .area-header {{ display: grid; grid-template-columns: 1fr auto; gap: 18px; align-items: start; }}
      .badge {{ display: inline-flex; background: var(--frost); color: var(--alpine); padding: 6px 9px; border-radius: 5px; font-size: 12px; font-weight: 800; text-transform: uppercase; }}
      .month-metrics {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; margin: 14px 0; }}
      .month-stat {{ background: white; border-radius: 5px; padding: 10px; }}
      .month-stat strong {{ display: block; margin-top: 4px; }}
      .list {{ display: grid; gap: 10px; }}
      .muted {{ color: var(--slate); }}
      @media (max-width: 820px) {{ .hero, .grid, .calendar, .metrics, .area-header {{ grid-template-columns: 1fr; }} .nav {{ grid-template-columns: 1fr; }} .shell {{ padding: 24px 16px 44px; }} h1 {{ font-size: 42px; }} }}
    </style>
  </head>
  <body>
    <main class="shell">
      <nav class="nav"><div class="brand">Snowcast public guide</div><a class="pill" href="{_html(page.planner_url)}">Open planner</a></nav>
      <section class="hero">
        <div class="card hero-main">
          <div class="eyebrow">Ski destination guide</div>
          <h1>{_html(destination.name)}</h1>
          <p class="lede">Stay in {_html(destination.name)}, {_html(destination.region)}, {_html(destination.country)}, with access to {_html(page.ski_region_name)}. Snow and historical evidence stay attached to each ski area below.</p>
          <div class="cta-row"><a class="cta-primary" href="{_html(page.planner_url)}">Plan with Snowcast</a><a class="cta-secondary" href="#ski-area-{_html(first_area_id)}">View calendar</a></div>
        </div>
        <aside class="card">
          <div class="eyebrow">Destination facts</div>
          <div class="metrics">
            <div class="metric"><div class="label">Recommended places to stay</div><div class="value">{len(page.stay_bases)}</div></div>
            <div class="metric"><div class="label">Accessible ski areas</div><div class="value">{len(page.ski_area_sections)}</div></div>
            <div class="metric"><div class="label">Trip market</div><div class="value">{_html(page.ski_region_name)}</div></div>
            <div class="metric"><div class="label">Price level</div><div class="value">{_html(destination.price_level.title())}</div></div>
          </div>
        </aside>
      </section>
      {_render_ski_area_sections(page.ski_area_sections)}
      <section class="grid">
        <div class="card"><div class="eyebrow">Recommended places to stay</div><h2>Recommended places to stay</h2><div class="list">{_render_stay_bases(page.stay_bases)}</div></div>
        <div class="card"><div class="eyebrow">Equipment rentals</div><h2>Equipment options</h2><div class="list">{_render_rentals(page.rentals)}</div></div>
      </section>
      <section class="card" style="margin-top: 22px;"><div class="eyebrow">Trust and provenance</div><h2>What this guide is based on</h2><p class="muted">This page combines curated destination and access details with current conditions and archive weather for each ski area. It does not blend several ski areas into one weather score.</p></section>
    </main>
  </body>
</html>
"""


def _render_ski_area_sections(
    sections: tuple[PublicSkiAreaSection, ...],
) -> str:
    rendered: list[str] = []
    for section in sections:
        area = section.ski_area
        current = section.current_conditions
        best_months = sorted(
            section.calendar_months,
            key=lambda item: item.score,
            reverse=True,
        )[:3]
        best_months_label = ", ".join(month.month_name for month in best_months)
        rendered.append(
            f"""
      <section id="ski-area-{_html(area.ski_area_id)}" class="card area-section">
        <div class="area-header">
          <div><div class="eyebrow">Current snow signal</div><h2>{_html(area.name)} ski-area conditions</h2><p>{_html(current.weather_summary)}</p></div>
          <div class="metrics">
            <div class="metric"><div class="label">Snow fit</div><div class="value">{_html(_snow_fit_label(current.snow_confidence_label))}</div></div>
            <div class="metric"><div class="label">Disruption signal</div><div class="value">{_html(_availability_label(current.availability_status))}</div></div>
            <div class="metric"><div class="label">Elevation</div><div class="value">{area.base_elevation_m}-{area.summit_elevation_m}m</div></div>
            <div class="metric"><div class="label">Season</div><div class="value">{_html(_season_label(area))}</div></div>
          </div>
        </div>
        <p class="muted">{_html(section.current_provenance.basis_summary)}</p>
        <p class="muted"><strong>Source:</strong> {_html(section.current_provenance.source_name or "Estimated")} · <strong>Freshness:</strong> {_html(str(section.current_provenance.freshness_status).replace("_", " "))} · <strong>Updated:</strong> {_html(_timestamp_label(section.current_provenance.updated_at))}</p>
        <div class="eyebrow">Conditions calendar</div>
        <p class="muted">Historically strongest months: {_html(best_months_label)}. These month cards use only {_html(area.name)} archive weather and ski-area season facts.</p>
        <div class="calendar">{_render_calendar(section.calendar_months)}</div>
      </section>
            """
        )
    return "\n".join(rendered)


def _render_calendar(months: tuple[PublicCalendarMonth, ...]) -> str:
    return "\n".join(
        f"""
          <article class="month {"good" if month.snow_confidence_label == "good" else ""}">
            <span class="badge">{_html(_snow_fit_label(month.snow_confidence_label))}</span>
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


def _render_stay_bases(stay_bases: tuple[PublicStayBaseView, ...]) -> str:
    return "\n".join(
        f"""
        <div class="list-item">
          <strong>{_html(view.stay_base.name)}</strong>
          <div class="muted">{_html(view.stay_base.price_range)} nightly stay estimate · access to {_html(", ".join(view.ski_area_names))}</div>
        </div>
        """
        for view in stay_bases
    )


def _render_rentals(rentals: tuple[RentalDisplayFact, ...]) -> str:
    if not rentals:
        return '<div class="list-item muted">No curated rental display facts.</div>'
    return "\n".join(
        f"""
        <div class="list-item">
          <strong>{_html(rental.name)}</strong>
          <div class="muted">{_html(rental.price_range)} daily rental estimate · {_html(rental.lift_distance.title())} lift access</div>
        </div>
        """
        for rental in rentals
    )


def _season_label(ski_area: SkiArea) -> str:
    return (
        f"{MONTH_NAMES[ski_area.season_start_month]}-"
        f"{MONTH_NAMES[ski_area.season_end_month]}"
    )


def _availability_label(value: str) -> str:
    return {
        "open": "Low disruption risk",
        "limited": "Some disruption risk",
        "temporarily_closed": "High disruption risk",
        "out_of_season": "Out of season",
    }.get(value, value.replace("_", " ").title())


def _snow_fit_label(value: str) -> str:
    return {
        "good": "Strong fit",
        "fair": "Some concerns",
        "poor": "Not enough evidence",
    }.get(value, "Not enough evidence")


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
