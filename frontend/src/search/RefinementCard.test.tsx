import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, test, vi } from "vitest";

import type { RefinementProposal } from "../types";
import { RefinementCard } from "./RefinementCard";

const refinement: RefinementProposal = {
  question_id: "snow-priority",
  question: "What should break the tie?",
  reason: "One answer could reorder your top results.",
  options: [
    {
      label: "Snow reliability",
      description: "Favor high-altitude options.",
      intent_changed: true,
      group_priority_patches: [],
      factor_preference_patches: [],
      objective_patches: [
        { factor_id: "trip_window_snow_fit", importance: "high" },
      ],
      preview: {
        top_rank_changes: [
          { ski_region_id: "region-a", previous_rank: 3, preview_rank: 2 },
        ],
        eligible_candidate_count_delta: 0,
      },
    },
    {
      label: "Shorter journey",
      description: "Keep the current balance.",
      intent_changed: false,
      group_priority_patches: [],
      factor_preference_patches: [],
      objective_patches: [],
    },
  ],
};

test("previews a selected option before apply and supports clear and skip", async () => {
  const user = userEvent.setup();
  const onApply = vi.fn();
  const onSkip = vi.fn();
  render(
    <RefinementCard
      refinement={refinement}
      loading={false}
      error={null}
      onApply={onApply}
      onSkip={onSkip}
    />,
  );

  await user.click(screen.getByRole("radio", { name: /snow reliability/i }));
  expect(screen.getByText("One result would move from #3 to #2.")).toBeVisible();
  expect(onApply).not.toHaveBeenCalled();

  await user.click(screen.getByRole("button", { name: "Clear" }));
  expect(screen.getByRole("radio", { name: /snow reliability/i })).not.toBeChecked();

  await user.click(screen.getByRole("radio", { name: /shorter journey/i }));
  expect(
    screen.getByText("Keeps your current trip decisions and ranking."),
  ).toBeVisible();
  await user.click(screen.getByRole("button", { name: /keep current ranking/i }));
  expect(onApply).toHaveBeenCalledWith(refinement.question_id, refinement.options[1]);

  await user.click(screen.getByRole("button", { name: /skip for now/i }));
  expect(onSkip).toHaveBeenCalledWith(refinement.question_id);
});

test("preserves the selected option after apply failure for retry", async () => {
  const user = userEvent.setup();
  const { rerender } = render(
    <RefinementCard
      refinement={refinement}
      loading={false}
      error={null}
      onApply={vi.fn()}
      onSkip={vi.fn()}
    />,
  );
  await user.click(screen.getByRole("radio", { name: /snow reliability/i }));

  rerender(
    <RefinementCard
      refinement={refinement}
      loading={false}
      error="Could not rerank."
      onApply={vi.fn()}
      onSkip={vi.fn()}
    />,
  );

  expect(screen.getByRole("radio", { name: /snow reliability/i })).toBeChecked();
  expect(screen.getByRole("alert")).toHaveTextContent("Could not rerank.");
  expect(screen.getByRole("button", { name: /retry apply and rerank/i })).toBeEnabled();
});
