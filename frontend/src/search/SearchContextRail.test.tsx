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

const intentWithFivePreferences: SearchIntent = {
  ...intent,
  objectives: [
    { factor_id: "pass_terrain_value", importance: "normal" },
    { factor_id: "trip_window_snow_fit", importance: "high" },
  ],
  factor_preferences: [
    {
      factor_id: "stay_base_access",
      mode: "prefer",
      values: ["near"],
      importance: "normal",
    },
    {
      factor_id: "local_pace",
      mode: "prefer",
      values: ["quiet"],
      importance: "normal",
    },
    {
      factor_id: "glacier_terrain",
      mode: "prefer",
      values: [],
      importance: "normal",
    },
  ],
};

const refinement: RefinementProposal = {
  topic_id: "tie_break",
  target_factor_id: "stay_base_access",
  question_id: "tie-break",
  question: "What should break the tie?",
  reason: "One answer could reorder your top results.",
  options: [
    {
      label: "Lift access",
      description: "Prefer closer lifts.",
      intent_changed: true,
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
      refinementStatus="questions_available"
      loading={false}
      refinementError={null}
      refinementControlRef={createRef<HTMLInputElement>()}
      adjustFiltersRef={createRef<HTMLButtonElement>()}
      onOpenFilters={vi.fn()}
      onRemoveChip={vi.fn()}
      onApplyRefinement={vi.fn()}
      onSkipRefinement={vi.fn()}
      onRetryRefinement={vi.fn()}
      onKeepResults={vi.fn()}
    />,
  );

  const hard = screen.getByRole("group", { name: "Must-haves" });
  expect(within(hard).getByText("France")).toBeVisible();
  expect(within(hard).getByText("March window")).toBeVisible();
  expect(within(hard).getByText("Intermediate")).toBeVisible();
  expect(within(hard).getByText("Max EUR 320/night")).toBeVisible();

  const preferences = screen.getByRole("group", { name: "Preferences" });
  expect(within(preferences).getByText(/terrain for lift-pass price/i)).toBeVisible();
  expect(within(preferences).getByText(/access to the slopes/i)).toBeVisible();
  expect(screen.getByRole("button", { name: "Adjust" })).toBeVisible();
  expect(screen.getAllByText("What should break the tie?")).toHaveLength(1);
  expect(screen.getByRole("status")).toHaveTextContent(
    "A refinement question is ready. What should break the tie?",
  );
});

test("shows three preferences and a full-list count", () => {
  render(
    <SearchContextRail
      intent={intentWithFivePreferences}
      refinement={null}
      refinementStatus="idle"
      loading={false}
      refinementError={null}
      refinementControlRef={createRef<HTMLInputElement>()}
      adjustFiltersRef={createRef<HTMLButtonElement>()}
      onOpenFilters={vi.fn()}
      onRemoveChip={vi.fn()}
      onApplyRefinement={vi.fn()}
      onSkipRefinement={vi.fn()}
    />,
  );

  const preferences = screen.getByRole("group", { name: "Preferences" });
  expect(
    within(preferences).getAllByRole("button", { name: /^Remove / }),
  ).toHaveLength(3);
  expect(
    within(preferences).getByRole("button", {
      name: "View all 5 preferences",
    }),
  ).toBeVisible();
});

test("keeps required factor preferences visible with hard constraints", () => {
  render(
    <SearchContextRail
      intent={{
        ...intentWithFivePreferences,
        factor_preferences: [
          ...intentWithFivePreferences.factor_preferences,
          {
            factor_id: "snowmaking_availability",
            mode: "require",
            values: [],
            importance: "high",
          },
        ],
      }}
      refinement={null}
      refinementStatus="idle"
      loading={false}
      refinementError={null}
      refinementControlRef={createRef<HTMLInputElement>()}
      adjustFiltersRef={createRef<HTMLButtonElement>()}
      onOpenFilters={vi.fn()}
      onRemoveChip={vi.fn()}
      onApplyRefinement={vi.fn()}
      onSkipRefinement={vi.fn()}
    />,
  );

  const hard = screen.getByRole("group", { name: "Must-haves" });
  expect(
    within(hard).getByRole("button", {
      name: "Remove Require Snowmaking resilience",
    }),
  ).toBeVisible();
  expect(
    screen.getByRole("button", { name: "View all 5 preferences" }),
  ).toBeVisible();
});

test("disables context mutations while recommendations are loading", () => {
  const onOpenFilters = vi.fn();
  const onRemoveChip = vi.fn();
  render(
    <SearchContextRail
      intent={intent}
      refinement={refinement}
      refinementStatus="questions_available"
      loading
      refinementError={null}
      refinementControlRef={createRef<HTMLInputElement>()}
      adjustFiltersRef={createRef<HTMLButtonElement>()}
      onOpenFilters={onOpenFilters}
      onRemoveChip={onRemoveChip}
      onApplyRefinement={vi.fn()}
      onSkipRefinement={vi.fn()}
    />,
  );

  expect(screen.getByRole("button", { name: "Adjust" })).toBeDisabled();
  for (const chip of screen.getAllByRole("button", { name: /^Remove / })) {
    expect(chip).toBeDisabled();
  }
  expect(onOpenFilters).not.toHaveBeenCalled();
  expect(onRemoveChip).not.toHaveBeenCalled();
});

test("announces initial and replacement refinement questions", () => {
  const sharedProps = {
    intent,
    loading: false,
    refinementError: null,
    refinementControlRef: createRef<HTMLInputElement>(),
    adjustFiltersRef: createRef<HTMLButtonElement>(),
    onOpenFilters: vi.fn(),
    onRemoveChip: vi.fn(),
    onApplyRefinement: vi.fn(),
    onSkipRefinement: vi.fn(),
  };
  const { rerender } = render(
    <SearchContextRail
      {...sharedProps}
      refinement={null}
      refinementStatus="loading"
    />,
  );

  expect(screen.getByRole("status")).toHaveTextContent(
    "Checking whether one answer could improve these trip options.",
  );

  rerender(
    <SearchContextRail
      {...sharedProps}
      refinement={refinement}
      refinementStatus="questions_available"
    />,
  );
  expect(screen.getByRole("status")).toHaveTextContent(
    "A refinement question is ready. What should break the tie?",
  );

  rerender(
    <SearchContextRail
      {...sharedProps}
      refinement={{
        ...refinement,
        question_id: "next-priority",
        question: "What should matter next?",
      }}
      refinementStatus="questions_available"
    />,
  );
  expect(screen.getByRole("status")).toHaveTextContent(
    "A refinement question is ready. What should matter next?",
  );
});

test.each([
    ["loading", "Checking whether one answer could improve these trip options."],
  [
    "slow",
      "Your trip options are ready. Snowcast is checking whether one answer could improve them.",
  ],
  [
    "retrying",
    "Snowcast is waiting a moment before checking for another useful question.",
  ],
    ["stale", "New trip options replaced this question."],
] as const)("renders the %s refinement lifecycle state", (status, copy) => {
  render(
    <SearchContextRail
      intent={intent}
      refinement={null}
      refinementStatus={status}
      loading={false}
      refinementError={null}
      refinementControlRef={createRef<HTMLInputElement>()}
      adjustFiltersRef={createRef<HTMLButtonElement>()}
      onOpenFilters={vi.fn()}
      onRemoveChip={vi.fn()}
      onApplyRefinement={vi.fn()}
      onSkipRefinement={vi.fn()}
    />,
  );

  expect(screen.getByRole("status")).toHaveTextContent(copy);
});

test("keeps a terminal refinement failure visible with recovery actions", () => {
  const onRetryRefinement = vi.fn();
  const onKeepResults = vi.fn();
  render(
    <SearchContextRail
      intent={intent}
      refinement={null}
      refinementStatus="temporarily_unavailable"
      loading={false}
      refinementError="Snowcast could not check for another useful question. Your results are unchanged."
      refinementControlRef={createRef<HTMLInputElement>()}
      adjustFiltersRef={createRef<HTMLButtonElement>()}
      onOpenFilters={vi.fn()}
      onRemoveChip={vi.fn()}
      onApplyRefinement={vi.fn()}
      onSkipRefinement={vi.fn()}
      onRetryRefinement={onRetryRefinement}
      onKeepResults={onKeepResults}
    />,
  );

  expect(screen.getByRole("alert")).toHaveTextContent(
    "Snowcast could not check for another useful question. Your results are unchanged.",
  );
  expect(screen.queryByRole("status")).not.toBeInTheDocument();
  screen.getByRole("button", { name: "Try again" }).click();
  screen.getByRole("button", { name: "Keep these results" }).click();
  expect(onRetryRefinement).toHaveBeenCalledOnce();
  expect(onKeepResults).toHaveBeenCalledOnce();
});

test("keeps the terminal recovery card busy and guards both actions during retry", () => {
  const onRetryRefinement = vi.fn();
  const onKeepResults = vi.fn();
  render(
    <SearchContextRail
      intent={intent}
      refinement={null}
      refinementStatus="loading"
      loading={false}
      refinementRetrying
      refinementError="Snowcast could not check for another useful question. Your results are unchanged."
      refinementControlRef={createRef<HTMLButtonElement>()}
      adjustFiltersRef={createRef<HTMLButtonElement>()}
      onOpenFilters={vi.fn()}
      onRemoveChip={vi.fn()}
      onApplyRefinement={vi.fn()}
      onSkipRefinement={vi.fn()}
      onRetryRefinement={onRetryRefinement}
      onKeepResults={onKeepResults}
    />,
  );

  const recovery = screen.getByText("One more question").closest("div");
  expect(recovery).toHaveAttribute("aria-busy", "true");
  const retry = screen.getByRole("button", { name: "Try again" });
  const keep = screen.getByRole("button", { name: "Keep these results" });
  expect(retry).toHaveAttribute("aria-disabled", "true");
  expect(keep).toHaveAttribute("aria-disabled", "true");
  retry.click();
  keep.click();
  expect(onRetryRefinement).not.toHaveBeenCalled();
  expect(onKeepResults).not.toHaveBeenCalled();
});

test("keeps the idle lifecycle state compact", () => {
  render(
    <SearchContextRail
      intent={intent}
      refinement={null}
      refinementStatus="idle"
      loading={false}
      refinementError={null}
      refinementControlRef={createRef<HTMLInputElement>()}
      adjustFiltersRef={createRef<HTMLButtonElement>()}
      onOpenFilters={vi.fn()}
      onRemoveChip={vi.fn()}
      onApplyRefinement={vi.fn()}
      onSkipRefinement={vi.fn()}
    />,
  );

  expect(screen.queryByRole("status")).not.toBeInTheDocument();
});

test("shows when no useful follow-up is needed", () => {
  render(
    <SearchContextRail
      intent={intent}
      refinement={null}
      refinementStatus="not_needed"
      loading={false}
      refinementError={null}
      refinementControlRef={createRef<HTMLInputElement>()}
      adjustFiltersRef={createRef<HTMLButtonElement>()}
      onOpenFilters={vi.fn()}
      onRemoveChip={vi.fn()}
      onApplyRefinement={vi.fn()}
      onSkipRefinement={vi.fn()}
    />,
  );

  expect(screen.getByRole("status")).toHaveTextContent(
    "No more questions would materially change these results.",
  );
});

test("reports a skipped follow-up without claiming it was unnecessary", () => {
  render(
    <SearchContextRail
      intent={intent}
      refinement={null}
      refinementStatus="skipped"
      loading={false}
      refinementError={null}
      refinementControlRef={createRef<HTMLInputElement>()}
      adjustFiltersRef={createRef<HTMLButtonElement>()}
      onOpenFilters={vi.fn()}
      onRemoveChip={vi.fn()}
      onApplyRefinement={vi.fn()}
      onSkipRefinement={vi.fn()}
    />,
  );

  expect(screen.getByRole("status")).toHaveTextContent(
    "Question skipped. Results unchanged.",
  );
});
