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

function setNarrowViewport(matches: boolean) {
  const listeners = new Set<(event: MediaQueryListEvent) => void>();
  vi.stubGlobal(
    "matchMedia",
    vi.fn().mockImplementation((query: string) => ({
      matches,
      media: query,
      onchange: null,
      addEventListener: (_type: string, listener: (event: MediaQueryListEvent) => void) =>
        listeners.add(listener),
      removeEventListener: (
        _type: string,
        listener: (event: MediaQueryListEvent) => void,
      ) => listeners.delete(listener),
      dispatchEvent: () => true,
    })),
  );
}

test("uses the concrete question as the heading and reason as support text", () => {
  render(
    <RefinementCard
      refinement={refinement}
      loading={false}
      error={null}
      onApply={vi.fn()}
      onSkip={vi.fn()}
    />,
  );

  expect(
    screen.getByRole("heading", { level: 2, name: refinement.question }),
  ).toBeVisible();
  expect(screen.getByText(refinement.reason)).toHaveClass(
    "contextual-refinement__reason",
  );
  expect(
    screen.getByRole("group", { name: refinement.question }),
  ).toBeVisible();
});

test("supports keyboard-only radio selection, apply, and skip focus", async () => {
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

  await user.tab();
  expect(document.activeElement).toBe(
    screen.getByRole("radio", { name: /snow reliability/i }),
  );
  await user.keyboard("{ArrowDown}");
  const shorterJourney = screen.getByRole("radio", { name: /shorter journey/i });
  expect(document.activeElement).toBe(shorterJourney);
  expect(shorterJourney).toBeChecked();

  await user.tab();
  const apply = screen.getByRole("button", { name: /keep current ranking/i });
  expect(document.activeElement).toBe(apply);
  await user.keyboard("{Enter}");
  expect(onApply).toHaveBeenCalledWith(refinement.question_id, refinement.options[1]);

  await user.tab();
  expect(document.activeElement).toBe(
    screen.getByRole("button", { name: "Clear" }),
  );
  await user.tab();
  const skip = screen.getByRole("button", { name: /skip for now/i });
  expect(document.activeElement).toBe(skip);
  await user.keyboard("{Enter}");
  expect(onSkip).toHaveBeenCalledWith(refinement.question_id);
});

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

test("keeps the concrete question visible in a collapsed narrow disclosure", async () => {
  setNarrowViewport(true);
  const user = userEvent.setup();
  render(
    <RefinementCard
      refinement={refinement}
      loading={false}
      error={null}
      onApply={vi.fn()}
      onSkip={vi.fn()}
    />,
  );

  expect(screen.getByRole("heading", { name: refinement.question })).toBeVisible();
  const disclosure = screen.getByRole("button", { name: "Choose a preference" });
  expect(disclosure).toHaveAttribute("aria-expanded", "false");
  expect(disclosure).toHaveAttribute("aria-controls");
  expect(screen.getByText(refinement.reason)).not.toBeVisible();
  expect(screen.queryByRole("radio")).not.toBeInTheDocument();

  await user.click(disclosure);

  expect(disclosure).toHaveAttribute("aria-expanded", "true");
  expect(screen.getByText(refinement.reason)).toBeVisible();
  expect(screen.getAllByRole("radio")).toHaveLength(2);
  expect(document.activeElement).toBe(
    screen.getByRole("radio", { name: /snow reliability/i }),
  );
});

test("a replacement question resets the narrow disclosure to collapsed", async () => {
  setNarrowViewport(true);
  const user = userEvent.setup();
  const shared = {
    loading: false,
    error: null,
    onApply: vi.fn(),
    onSkip: vi.fn(),
  };
  const { rerender } = render(
    <RefinementCard refinement={refinement} {...shared} />,
  );
  await user.click(screen.getByRole("button", { name: "Choose a preference" }));
  expect(screen.getByRole("radio", { name: /snow reliability/i })).toBeVisible();

  rerender(
    <RefinementCard
      refinement={{
        ...refinement,
        question_id: "next-question",
        question: "What place style would you prefer?",
      }}
      {...shared}
    />,
  );

  expect(screen.getByRole("heading", { name: "What place style would you prefer?" })).toBeVisible();
  expect(screen.getByRole("button", { name: "Choose a preference" })).toHaveAttribute(
    "aria-expanded",
    "false",
  );
  expect(screen.queryByRole("radio")).not.toBeInTheDocument();
});
