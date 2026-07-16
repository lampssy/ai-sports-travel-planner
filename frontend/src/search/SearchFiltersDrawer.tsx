import { X } from "lucide-react";
import { useEffect, useRef, type RefObject } from "react";

import type {
  FactorPreferencePatch,
  SearchFilters,
  SearchObjective,
  TravelMonth,
} from "../types";
import { featureOptions, monthOptions } from "./searchPresentation";
import { upsertBy } from "./searchSession";

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

export function SearchFiltersDrawer({
  open,
  filters,
  preferences,
  returnFocusRef,
  onFiltersChange,
  onPreferencesChange,
  onObjectivesChange,
  onClose,
}: {
  open: boolean;
  filters: SearchFilters;
  preferences: FactorPreferencePatch[];
  returnFocusRef: RefObject<HTMLButtonElement>;
  onFiltersChange: (filters: SearchFilters) => void;
  onPreferencesChange: (preferences: FactorPreferencePatch[]) => void;
  onObjectivesChange: (objectives: SearchObjective[]) => void;
  onClose: () => void;
}) {
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    closeRef.current?.focus();
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
        window.setTimeout(() => returnFocusRef.current?.focus(), 0);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose, open, returnFocusRef]);

  if (!open) return null;

  const closeAndReturnFocus = () => {
    onClose();
    window.setTimeout(() => returnFocusRef.current?.focus(), 0);
  };

  return (
    <div className="drawer-layer">
      <button
        type="button"
        className="drawer-backdrop"
        aria-label="Dismiss filters"
        onClick={closeAndReturnFocus}
      />
      <section
        className="filters-drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby="filters-drawer-title"
      >
        <header className="filters-drawer__header">
          <div>
            <p className="eyebrow">Exact controls</p>
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
                onChange={(event) =>
                  onFiltersChange({ ...filters, location: event.target.value })
                }
                className="control"
              />
            </Field>
            <Field label="Skill">
              <select
                value={filters.skillLevel}
                onChange={(event) =>
                  onFiltersChange({
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
                onChange={(event) =>
                  onFiltersChange({ ...filters, maxPrice: event.target.value })
                }
                className="control"
              />
            </Field>
            <Field label="Minimum stay tier">
              <select
                value={filters.stars}
                onChange={(event) =>
                  onFiltersChange({
                    ...filters,
                    stars: event.target.value as SearchFilters["stars"],
                  })
                }
                className="control"
              >
                <option value="">Any</option>
                <option value="1">Budget+</option>
                <option value="2">Standard+</option>
                <option value="3">Premium</option>
              </select>
            </Field>
          </div>

          <Field label="Travel window">
            <select
              value={filters.travelWindowMode}
              onChange={(event) =>
                onFiltersChange({
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
                onChange={(event) =>
                  onFiltersChange({
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
                  onChange={(event) =>
                    onFiltersChange({ ...filters, tripStartDate: event.target.value })
                  }
                  className="control"
                />
              </Field>
              <Field label="Trip end date">
                <input
                  type="date"
                  value={filters.tripEndDate}
                  onChange={(event) =>
                    onFiltersChange({ ...filters, tripEndDate: event.target.value })
                  }
                  className="control"
                />
              </Field>
            </div>
          ) : null}

          <div className="drawer-grid">
            <Field label="Origin">
              <input
                value={filters.originText}
                onChange={(event) =>
                  onFiltersChange({ ...filters, originText: event.target.value })
                }
                placeholder="Berlin"
                className="control"
              />
            </Field>
            <Field label="Hard drive limit">
              <input
                type="number"
                min="0.1"
                step="0.1"
                value={filters.maxDriveHours}
                onChange={(event) =>
                  onFiltersChange({ ...filters, maxDriveHours: event.target.value })
                }
                placeholder="hours"
                className="control"
              />
            </Field>
          </div>

          <Field label="Value objective">
            <select
              value={filters.valueObjective}
              onChange={(event) => {
                const factorId = event.target.value as SearchFilters["valueObjective"];
                onFiltersChange({ ...filters, valueObjective: factorId });
                onObjectivesChange(
                  factorId ? [{ factor_id: factorId, importance: "normal" }] : [],
                );
              }}
              className="control"
            >
              <option value="">No pass-value priority</option>
              <option value="pass_terrain_value">Most terrain for pass price</option>
              <option value="pass_price_per_day">Lowest pass price per day</option>
            </select>
          </Field>

          <fieldset className="preference-fieldset">
            <legend>Extra preferences</legend>
            <div className="preference-options">
              {featureOptions.map(([factorId, label]) => {
                const active = preferences.some(
                  (item) => item.factor_id === factorId && item.mode === "prefer",
                );
                return (
                  <button
                    type="button"
                    key={factorId}
                    aria-pressed={active}
                    onClick={() =>
                      onPreferencesChange(
                        active
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
                    {label}
                  </button>
                );
              })}
            </div>
          </fieldset>
        </div>
      </section>
    </div>
  );
}
