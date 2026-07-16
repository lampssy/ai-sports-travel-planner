import { render, screen, within } from "@testing-library/react";
import { createRef } from "react";
import { expect, test, vi } from "vitest";

import type { RefinementProposal, SearchIntent } from "../types";
import { SearchContextRail } from "./SearchContextRail";

const intent: SearchIntent = {
  constraints: {
    location: { country: "France" },
    travel_window: { month: 3 },
    lodging_budget: {
      mode: "lodging_nightly",
      maximum: 320,
      currency: "EUR",
      budget_flex: 0.1,
    },
  },
  party: { skill_levels: ["intermediate"] },
  travel_context: {},
  objectives: [{ factor_id: "pass_terrain_value", importance: "normal" }],
  group_priorities: [],
  factor_preferences: [
    {
      factor_id: "stay_base_access",
      mode: "prefer",
      values: ["near"],
      importance: "normal",
    },
  ],
  assumptions: [],
};

const refinement: RefinementProposal = {
  question_id: "tie-break",
  question: "What should break the tie?",
  reason: "One answer could reorder your top results.",
  options: [
    {
      label: "Lift access",
      description: "Prefer closer lifts.",
      group_priority_patches: [],
      factor_preference_patches: [],
      objective_patches: [],
    },
  ],
};

test("separates hard constraints from preferences and renders one refinement", () => {
  render(
    <SearchContextRail
      intent={intent}
      refinement={refinement}
      loading={false}
      refinementError={null}
      adjustFiltersRef={createRef<HTMLButtonElement>()}
      onOpenFilters={vi.fn()}
      onRemoveChip={vi.fn()}
      onApplyRefinement={vi.fn()}
      onSkipRefinement={vi.fn()}
    />,
  );

  const hard = screen.getByRole("group", { name: "Hard constraints" });
  expect(within(hard).getByText("France")).toBeVisible();
  expect(within(hard).getByText("March window")).toBeVisible();
  expect(within(hard).getByText("Intermediate")).toBeVisible();
  expect(within(hard).getByText("Max EUR 320/night")).toBeVisible();

  const preferences = screen.getByRole("group", { name: "Preferences" });
  expect(within(preferences).getByText(/terrain per pass price/i)).toBeVisible();
  expect(within(preferences).getByText(/stay-base access/i)).toBeVisible();
  expect(screen.getByRole("button", { name: "Adjust" })).toBeVisible();
  expect(screen.getAllByText("What should break the tie?")).toHaveLength(1);
});
