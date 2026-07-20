import {
  ArrowLeft,
  ChevronDown,
  PanelLeftClose,
  PanelLeftOpen,
} from "lucide-react";
import { useState } from "react";

import type { SearchV4RecommendationGroup } from "../types";
import { snowFitPresentation } from "./searchPresentation";
import { findSelectedCandidate, type SearchSession } from "./searchSession";

export function boundedNavigatorGroups(
  groups: SearchV4RecommendationGroup[],
  currentGroupId: string,
): SearchV4RecommendationGroup[] {
  const current = groups.find((group) => group.ski_region_id === currentGroupId);
  const topThree = groups.slice(0, 3);
  if (!current || topThree.some((group) => group.ski_region_id === currentGroupId)) {
    return topThree;
  }
  return [...groups.slice(0, 2), current];
}

export function tripOptionCountLabel(count: number): string {
  return `${count} trip ${count === 1 ? "option" : "options"}`;
}

export function RecommendationNavigator({
  session,
  currentGroup,
  onSwitch,
  onReturn,
  onToggle,
}: {
  session: SearchSession;
  currentGroup: SearchV4RecommendationGroup;
  onSwitch: (skiRegionId: string, candidateId: string) => void;
  onReturn: () => void;
  onToggle: () => void;
}) {
  const [switcherOpen, setSwitcherOpen] = useState(false);
  const groups = boundedNavigatorGroups(
    session.response.results,
    currentGroup.ski_region_id,
  );
  const collapsed = session.dossierNavigatorCollapsed;
  const tripOptionCount = session.response.results.length;
  const unscored = session.response.ranking_status === "unscored";

  return (
    <>
      <nav
        className={`dossier-navigator${collapsed ? " dossier-navigator--collapsed" : ""}`}
        aria-label="Trip option results"
        data-collapsed={collapsed || undefined}
      >
        <div className="dossier-navigator__heading">
          <div>
            <span>Search results</span>
            <strong>{tripOptionCountLabel(tripOptionCount)}</strong>
          </div>
          <button
            type="button"
            className="icon-button"
            aria-label={`${collapsed ? "Expand" : "Collapse"} trip option navigator`}
            aria-expanded={!collapsed}
            title={`${collapsed ? "Expand" : "Collapse"} trip option navigator`}
            onClick={onToggle}
          >
            {collapsed ? (
              <PanelLeftOpen aria-hidden="true" size={18} />
            ) : (
              <PanelLeftClose aria-hidden="true" size={18} />
            )}
          </button>
        </div>
        <button type="button" className="dossier-navigator__all" onClick={onReturn}>
          <ArrowLeft aria-hidden="true" size={16} />
          <span>All results</span>
        </button>
        <div className="dossier-navigator__rows">
          {groups.map((group) => {
            const selected = group.ski_region_id === currentGroup.ski_region_id;
            const configuration = findSelectedCandidate(
              group,
              session.selectedCandidateIdByGroup[group.ski_region_id],
            );
            const rowUnscored = configuration.ranking_status === "unscored";
            const snowFit = snowFitPresentation(
              configuration,
              session.response.applied_intent.constraints.travel_window,
            );
            return (
              <button
                type="button"
                className="dossier-navigator__row"
                key={group.ski_region_id}
                aria-current={selected ? "page" : undefined}
                aria-label={`${group.ski_region_name}, ${
                  rowUnscored ? "Fit comparison unavailable" : `rank ${group.rank}`
                }, ${selected ? "viewing" : "open option"}. Stay in ${
                  configuration.stay_base_name
                }. ${
                  rowUnscored
                    ? "Fit comparison unavailable"
                    : `${configuration.fit_score?.toFixed(0)} trip fit`
                }. ${snowFit.label}: ${snowFit.value}.`}
                onClick={() =>
                  onSwitch(
                    group.ski_region_id,
                    configuration.candidate_id,
                  )
                }
              >
                <span className="dossier-navigator__rank">
                  {rowUnscored ? "—" : `#${group.rank}`}
                </span>
                <span className="dossier-navigator__copy">
                  <strong>{group.ski_region_name}</strong>
                  <small>{configuration.stay_base_name}</small>
                  <small>
                    {rowUnscored
                      ? `Fit comparison unavailable · ${snowFit.label}: ${snowFit.value}`
                      : `${configuration.fit_score?.toFixed(0)} trip fit · ${snowFit.label}: ${snowFit.value}`}
                  </small>
                </span>
              </button>
            );
          })}
        </div>
        <p className="dossier-navigator__note">
          Your result order and filters stay preserved.
        </p>
      </nav>

      <section className="dossier-switcher" aria-label="Trip option switcher">
        <button
          type="button"
          className="dossier-switcher__trigger"
          aria-expanded={switcherOpen}
          aria-controls="dossier-switcher-options"
          onClick={() => setSwitcherOpen((current) => !current)}
        >
          <span>
            {unscored
              ? "Fit comparison unavailable"
              : `Trip option ${currentGroup.rank} of ${tripOptionCount}`}
            <strong>{currentGroup.ski_region_name}</strong>
          </span>
          <ChevronDown aria-hidden="true" size={19} />
        </button>
        {switcherOpen ? (
          <div id="dossier-switcher-options" className="dossier-switcher__options">
            {groups.map((group) => {
              const configuration = findSelectedCandidate(
                group,
                session.selectedCandidateIdByGroup[group.ski_region_id],
              );
              return (
                <button
                  type="button"
                  key={group.ski_region_id}
                  aria-current={
                    group.ski_region_id === currentGroup.ski_region_id
                      ? "page"
                      : undefined
                  }
                  aria-label={`Switch to ${group.ski_region_name}`}
                  onClick={() => {
                    setSwitcherOpen(false);
                    onSwitch(group.ski_region_id, configuration.candidate_id);
                  }}
                >
                  <span>{unscored ? "—" : `#${group.rank}`}</span>
                  <span className="dossier-switcher__option-copy">
                    <strong>{group.ski_region_name}</strong>
                    <small>{configuration.stay_base_name}</small>
                  </span>
                </button>
              );
            })}
            <button type="button" onClick={onReturn}>
              <ArrowLeft aria-hidden="true" size={16} />
              All results
            </button>
          </div>
        ) : null}
      </section>
    </>
  );
}
