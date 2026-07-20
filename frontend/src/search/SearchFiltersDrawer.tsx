import { X } from "lucide-react";
import { useEffect, useRef, type RefObject } from "react";

import type {
  FactorPreferencePatch,
  GroupPriorityPatch,
  SearchFilters,
  SearchObjective,
  TravelMonth,
} from "../types";
import {
  factorPreferenceLabel,
  factorLabels,
  featureOptions,
  groupPriorityLabel,
  monthOptions,
} from "./searchPresentation";
import {
  isPassValueObjective,
  mergeObjectivePatches,
  upsertBy,
} from "./searchSession";

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="drawer-field">
      <span>{label}</span>
      {children}
    </label>
  );
}

const featureOptionIds = new Set<string>(
  featureOptions.map(([factorId]) => factorId),
);

export function SearchFiltersDrawer({
  open,
  disabled,
  filters,
  preferences,
  groupPriorities,
  objectives,
  returnFocusRef,
  onFiltersChange,
  onPreferencesChange,
  onGroupPrioritiesChange,
  onObjectivesChange,
  onClose,
}: {
  open: boolean;
  disabled: boolean;
  filters: SearchFilters;
  preferences: FactorPreferencePatch[];
  groupPriorities: GroupPriorityPatch[];
  objectives: SearchObjective[];
  returnFocusRef: RefObject<HTMLButtonElement>;
  onFiltersChange: (filters: SearchFilters) => void;
  onPreferencesChange: (preferences: FactorPreferencePatch[]) => void;
  onGroupPrioritiesChange: (groupPriorities: GroupPriorityPatch[]) => void;
  onObjectivesChange: (objectives: SearchObjective[]) => void;
  onClose: () => void;
}) {
  const closeRef = useRef<HTMLButtonElement>(null);
  const dialogRef = useRef<HTMLElement>(null);
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;
  const preferencesByFactor = new Map<string, FactorPreferencePatch>();
  for (const preference of preferences) {
    if (factorLabels[preference.factor_id]) {
      preferencesByFactor.set(preference.factor_id, preference);
    }
  }
  const additionalPreferences = [...preferencesByFactor.values()].filter(
    (preference) => !featureOptionIds.has(preference.factor_id),
  );
  const objectivesByFactor = new Map<string, SearchObjective>();
  for (const objective of objectives) {
    if (factorLabels[objective.factor_id]) {
      objectivesByFactor.set(objective.factor_id, objective);
    }
  }
  const additionalObjectives = [...objectivesByFactor.values()].filter(
    (objective) => !isPassValueObjective(objective.factor_id),
  );
  const visibleGroupPriorities = groupPriorities.flatMap((priority) => {
    const label = groupPriorityLabel(priority);
    return label ? [{ priority, label }] : [];
  });

  useEffect(() => {
    if (!open) return;
    const dialog = dialogRef.current;
    const layer = dialog?.closest(".drawer-layer");
    const backgroundElements = layer?.parentElement
      ? [...layer.parentElement.children].filter(
          (element): element is HTMLElement =>
            element instanceof HTMLElement && element !== layer,
        )
      : [];
    const previousBackgroundState = backgroundElements.map((element) => ({
      element,
      inert: element.inert,
      ariaHidden: element.getAttribute("aria-hidden"),
    }));
    for (const element of backgroundElements) {
      element.inert = true;
      element.setAttribute("aria-hidden", "true");
    }
    closeRef.current?.focus();
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onCloseRef.current();
        window.setTimeout(() => returnFocusRef.current?.focus(), 0);
        return;
      }
      if (event.key !== "Tab" || !dialog) return;
      const focusable = [
        ...dialog.querySelectorAll<HTMLElement>(
          'button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), a[href], [tabindex]:not([tabindex="-1"])',
        ),
      ].filter((element) => !element.hidden);
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (!first || !last) {
        event.preventDefault();
        dialog.focus();
        return;
      }
      const active = document.activeElement;
      if (event.shiftKey && (active === first || !dialog.contains(active))) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && (active === last || !dialog.contains(active))) {
        event.preventDefault();
        first.focus();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      for (const { element, inert, ariaHidden } of previousBackgroundState) {
        element.inert = inert;
        if (ariaHidden == null) element.removeAttribute("aria-hidden");
        else element.setAttribute("aria-hidden", ariaHidden);
      }
    };
  }, [open, returnFocusRef]);

  if (!open) return null;

  const closeAndReturnFocus = () => {
    onClose();
    window.setTimeout(() => returnFocusRef.current?.focus(), 0);
  };

  const changeFilters = (nextFilters: SearchFilters) => {
    if (disabled) return;
    onFiltersChange(nextFilters);
  };

  const changeValueObjective = (
    nextFilters: SearchFilters,
    nextObjectives: SearchObjective[],
  ) => {
    if (disabled) return;
    onFiltersChange(nextFilters);
    onObjectivesChange(nextObjectives);
  };

  const changePreferences = (nextPreferences: FactorPreferencePatch[]) => {
    if (disabled) return;
    onPreferencesChange(nextPreferences);
  };

  const changeObjectives = (nextObjectives: SearchObjective[]) => {
    if (disabled) return;
    onObjectivesChange(nextObjectives);
  };

  return (
    <div className="drawer-layer">
      <div
        className="drawer-backdrop"
        aria-hidden="true"
        onClick={closeAndReturnFocus}
      />
      <section
        ref={dialogRef}
        className="filters-drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby="filters-drawer-title"
        tabIndex={-1}
      >
        <header className="filters-drawer__header">
          <div>
            <p className="eyebrow">Search details</p>
            <h2 id="filters-drawer-title">Adjust filters</h2>
          </div>
          <button
            type="button"
            ref={closeRef}
            className="icon-button"
            aria-label="Close filters"
            onClick={closeAndReturnFocus}
          >
            <X aria-hidden="true" size={21} />
          </button>
        </header>

        <div className="filters-drawer__body">
          <div className="drawer-grid">
            <Field label="Country">
              <input
                value={filters.location}
                disabled={disabled}
                onChange={(event) =>
                  changeFilters({ ...filters, location: event.target.value })
                }
                className="control"
              />
            </Field>
            <Field label="Skill">
              <select
                value={filters.skillLevel}
                disabled={disabled}
                onChange={(event) =>
                  changeFilters({
                    ...filters,
                    skillLevel: event.target.value as SearchFilters["skillLevel"],
                  })
                }
                className="control"
              >
                <option value="">Not specified</option>
                <option value="beginner">Beginner</option>
                <option value="intermediate">Intermediate</option>
                <option value="advanced">Advanced</option>
              </select>
            </Field>
            <Field label="Max nightly">
              <input
                type="number"
                min="0.01"
                step="0.01"
                value={filters.maxPrice}
                disabled={disabled}
                onChange={(event) =>
                  changeFilters({ ...filters, maxPrice: event.target.value })
                }
                className="control"
              />
            </Field>
            <Field label="Minimum stay quality">
              <select
                value={filters.stars}
                disabled={disabled}
                onChange={(event) =>
                  changeFilters({
                    ...filters,
                    stars: event.target.value as SearchFilters["stars"],
                  })
                }
                className="control"
              >
                <option value="">Any</option>
                <option value="1">Basic comfort</option>
                <option value="2">Standard comfort</option>
                <option value="3">Higher comfort</option>
              </select>
            </Field>
          </div>

          <Field label="Travel window">
            <select
              value={filters.travelWindowMode}
              disabled={disabled}
              onChange={(event) =>
                changeFilters({
                  ...filters,
                  travelWindowMode: event.target.value as SearchFilters["travelWindowMode"],
                })
              }
              className="control"
            >
              <option value="any">Any time</option>
              <option value="month">Month</option>
              <option value="dates">Exact dates</option>
            </select>
          </Field>
          {filters.travelWindowMode === "month" ? (
            <Field label="Travel month">
              <select
                value={filters.travelMonth}
                disabled={disabled}
                onChange={(event) =>
                  changeFilters({
                    ...filters,
                    travelMonth: Number(event.target.value) as TravelMonth,
                  })
                }
                className="control"
              >
                {monthOptions.map((month, index) => (
                  <option key={month} value={index + 1}>
                    {month}
                  </option>
                ))}
              </select>
            </Field>
          ) : null}
          {filters.travelWindowMode === "dates" ? (
            <div className="drawer-grid">
              <Field label="Trip start date">
                <input
                  type="date"
                  value={filters.tripStartDate}
                  disabled={disabled}
                  onChange={(event) =>
                    changeFilters({ ...filters, tripStartDate: event.target.value })
                  }
                  className="control"
                />
              </Field>
              <Field label="Trip end date">
                <input
                  type="date"
                  value={filters.tripEndDate}
                  disabled={disabled}
                  onChange={(event) =>
                    changeFilters({ ...filters, tripEndDate: event.target.value })
                  }
                  className="control"
                />
              </Field>
            </div>
          ) : null}

          <div className="drawer-grid">
            <Field label="Starting location">
              <input
                value={filters.originText}
                disabled={disabled}
                onChange={(event) =>
                  changeFilters({ ...filters, originText: event.target.value })
                }
                placeholder="Berlin"
                className="control"
              />
            </Field>
            <Field label="Maximum drive time">
              <input
                type="number"
                min="0.1"
                step="0.1"
                value={filters.maxDriveHours}
                disabled={disabled}
                onChange={(event) =>
                  changeFilters({ ...filters, maxDriveHours: event.target.value })
                }
                placeholder="hours"
                className="control"
              />
            </Field>
          </div>

          <Field label="What matters most for value?">
            <select
              value={filters.valueObjective}
              disabled={disabled}
              onChange={(event) => {
                const factorId = event.target.value as SearchFilters["valueObjective"];
                changeValueObjective(
                  { ...filters, valueObjective: factorId },
                  factorId
                    ? mergeObjectivePatches(objectives, [
                        { factor_id: factorId, importance: "normal" as const },
                      ])
                    : objectives.filter(
                        (objective) =>
                          !isPassValueObjective(objective.factor_id),
                      ),
                );
              }}
              className="control"
            >
              <option value="">No pass-value priority</option>
              <option value="pass_terrain_value">Most terrain for pass price</option>
              <option value="pass_price_per_day">Lowest pass price per day</option>
            </select>
          </Field>

          {additionalObjectives.length ? (
            <fieldset className="preference-fieldset">
              <legend>Other preferences</legend>
              <div className="preference-options">
                {additionalObjectives.map((objective) => (
                  <button
                    type="button"
                    key={objective.factor_id}
                    aria-pressed="true"
                    disabled={disabled}
                    onClick={() =>
                      changeObjectives(
                        objectives.filter(
                          (item) => item.factor_id !== objective.factor_id,
                        ),
                      )
                    }
                    className="preference-option"
                  >
                    Prefer {factorLabels[objective.factor_id]}
                  </button>
                ))}
              </div>
            </fieldset>
          ) : null}

          {visibleGroupPriorities.length ? (
            <fieldset className="preference-fieldset">
              <legend>What matters most</legend>
              <div className="preference-options">
                {visibleGroupPriorities.map(({ priority, label }) => (
                  <button
                    type="button"
                    key={priority.group_id}
                    aria-pressed="true"
                    disabled={disabled}
                    onClick={() =>
                      onGroupPrioritiesChange(
                        groupPriorities.filter(
                          (item) => item.group_id !== priority.group_id,
                        ),
                      )
                    }
                    className="preference-option"
                  >
                    {label}
                  </button>
                ))}
              </div>
            </fieldset>
          ) : null}

          <fieldset className="preference-fieldset">
            <legend>Extra preferences</legend>
            <div className="preference-options">
              {featureOptions.map(([factorId, label]) => {
                const activePreference = preferencesByFactor.get(factorId);
                return (
                  <button
                    type="button"
                    key={factorId}
                    aria-pressed={Boolean(activePreference)}
                    disabled={disabled}
                    onClick={() =>
                      changePreferences(
                        activePreference
                          ? preferences.filter((item) => item.factor_id !== factorId)
                          : upsertBy(
                              preferences,
                              [
                                {
                                  factor_id: factorId,
                                  mode: "prefer",
                                  values: [],
                                  importance: "normal",
                                },
                              ],
                              (item) => item.factor_id,
                            ),
                      )
                    }
                    className="preference-option"
                  >
                    {activePreference
                      ? factorPreferenceLabel(activePreference)
                      : label}
                  </button>
                );
              })}
              {additionalPreferences.map((preference) => (
                <button
                  type="button"
                  key={`${preference.factor_id}-${preference.mode}`}
                  aria-pressed="true"
                  disabled={disabled}
                  onClick={() =>
                    changePreferences(
                      preferences.filter(
                        (item) => item.factor_id !== preference.factor_id,
                      ),
                    )
                  }
                  className="preference-option"
                >
                  {factorPreferenceLabel(preference)}
                </button>
              ))}
            </div>
          </fieldset>
        </div>
      </section>
    </div>
  );
}
