import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createRef } from "react";
import { expect, test, vi } from "vitest";

import { defaultSearchFilters } from "./searchSession";
import { SearchFiltersDrawer } from "./SearchFiltersDrawer";

test("disables an open drawer when loading starts but keeps close available", async () => {
  const onFiltersChange = vi.fn();
  const onPreferencesChange = vi.fn();
  const onObjectivesChange = vi.fn();
  const onClose = vi.fn();
  const props = {
    open: true,
    filters: { ...defaultSearchFilters, location: "France" },
    preferences: [],
    objectives: [
      { factor_id: "pass_terrain_value", importance: "normal" as const },
    ],
    returnFocusRef: createRef<HTMLButtonElement>(),
    onFiltersChange,
    onPreferencesChange,
    onObjectivesChange,
    onClose,
  };
  const { rerender } = render(<SearchFiltersDrawer {...props} disabled={false} />);

  expect(screen.getByLabelText("Country")).toBeEnabled();
  rerender(<SearchFiltersDrawer {...props} disabled />);

  const dialog = screen.getByRole("dialog", { name: "Adjust filters" });
  const drawer = within(dialog);
  const editableControls = [
    ...drawer.getAllByRole("textbox"),
    ...drawer.getAllByRole("spinbutton"),
    ...drawer.getAllByRole("combobox"),
    ...drawer.getAllByRole("button", { pressed: false }),
  ];
  for (const control of editableControls) {
    expect(control).toBeDisabled();
  }

  fireEvent.change(drawer.getByLabelText("Country"), {
    target: { value: "Austria" },
  });
  fireEvent.click(drawer.getAllByRole("button", { pressed: false })[0]);
  expect(onFiltersChange).not.toHaveBeenCalled();
  expect(onPreferencesChange).not.toHaveBeenCalled();
  expect(onObjectivesChange).not.toHaveBeenCalled();

  const close = drawer.getByRole("button", { name: "Close filters" });
  expect(close).toBeEnabled();
  await userEvent.click(close);
  expect(onClose).toHaveBeenCalledOnce();
});

test("changes only the drawer-owned pass objective", async () => {
  const user = userEvent.setup();
  const onFiltersChange = vi.fn();
  const onObjectivesChange = vi.fn();
  const objectives = [
    { factor_id: "trip_window_snow_fit", importance: "high" as const },
    { factor_id: "pass_terrain_value", importance: "normal" as const },
  ];
  const props = {
    open: true,
    disabled: false,
    filters: { ...defaultSearchFilters },
    preferences: [],
    objectives,
    returnFocusRef: createRef<HTMLButtonElement>(),
    onFiltersChange,
    onPreferencesChange: vi.fn(),
    onObjectivesChange,
    onClose: vi.fn(),
  };
  const { rerender } = render(<SearchFiltersDrawer {...props} />);

  await user.selectOptions(
    screen.getByLabelText("Value objective"),
    "pass_price_per_day",
  );
  expect(onObjectivesChange).toHaveBeenLastCalledWith([
    { factor_id: "trip_window_snow_fit", importance: "high" },
    { factor_id: "pass_price_per_day", importance: "normal" },
  ]);

  rerender(
    <SearchFiltersDrawer
      {...props}
      filters={{ ...props.filters, valueObjective: "pass_price_per_day" }}
      objectives={[
        objectives[0],
        { factor_id: "pass_price_per_day", importance: "normal" },
      ]}
    />,
  );
  await user.selectOptions(screen.getByLabelText("Value objective"), "");
  expect(onObjectivesChange).toHaveBeenLastCalledWith([
    { factor_id: "trip_window_snow_fit", importance: "high" },
  ]);
});

test("shows and removes active factor and objective choices outside the defaults", async () => {
  const user = userEvent.setup();
  const onPreferencesChange = vi.fn();
  const onObjectivesChange = vi.fn();
  const preferences = [
    {
      factor_id: "stay_base_access",
      mode: "prefer" as const,
      values: ["near"],
      importance: "normal" as const,
    },
  ];
  const objectives = [
    { factor_id: "pass_terrain_value", importance: "normal" as const },
    { factor_id: "trip_window_snow_fit", importance: "high" as const },
  ];

  render(
    <SearchFiltersDrawer
      open
      disabled={false}
      filters={{
        ...defaultSearchFilters,
        valueObjective: "pass_terrain_value",
      }}
      preferences={preferences}
      objectives={objectives}
      returnFocusRef={createRef<HTMLButtonElement>()}
      onFiltersChange={vi.fn()}
      onPreferencesChange={onPreferencesChange}
      onObjectivesChange={onObjectivesChange}
      onClose={vi.fn()}
    />,
  );

  const factorChoice = screen.getByRole("button", {
    name: "Prefer Stay-base access",
  });
  const objectiveChoice = screen.getByRole("button", {
    name: "Optimize Trip-window snow fit",
  });
  expect(factorChoice).toHaveAttribute("aria-pressed", "true");
  expect(objectiveChoice).toHaveAttribute("aria-pressed", "true");

  await user.click(factorChoice);
  expect(onPreferencesChange).toHaveBeenCalledWith([]);

  await user.click(objectiveChoice);
  expect(onObjectivesChange).toHaveBeenCalledWith([
    { factor_id: "pass_terrain_value", importance: "normal" },
  ]);
});

test("renders one mode-aware control for each active feature factor", async () => {
  const user = userEvent.setup();
  const onPreferencesChange = vi.fn();
  const preferences = [
    {
      factor_id: "marked_freeride_routes",
      mode: "prefer" as const,
      values: [],
      importance: "normal" as const,
    },
    {
      factor_id: "glacier_terrain",
      mode: "avoid" as const,
      values: ["internal_glacier_state"],
      importance: "normal" as const,
    },
    {
      factor_id: "snow_park",
      mode: "require" as const,
      values: [],
      importance: "high" as const,
    },
  ];

  render(
    <SearchFiltersDrawer
      open
      disabled={false}
      filters={defaultSearchFilters}
      preferences={preferences}
      objectives={[]}
      returnFocusRef={createRef<HTMLButtonElement>()}
      onFiltersChange={vi.fn()}
      onPreferencesChange={onPreferencesChange}
      onObjectivesChange={vi.fn()}
      onClose={vi.fn()}
    />,
  );

  expect(
    screen.getAllByRole("button", { name: /Marked freeride routes/ }),
  ).toHaveLength(1);
  expect(
    screen.getByRole("button", { name: "Prefer Marked freeride routes" }),
  ).toHaveAttribute("aria-pressed", "true");
  expect(
    screen.getAllByRole("button", { name: /Glacier terrain/ }),
  ).toHaveLength(1);
  const avoidGlacier = screen.getByRole("button", {
    name: "Avoid Glacier terrain",
  });
  expect(avoidGlacier).toHaveAttribute("aria-pressed", "true");
  expect(
    screen.getByRole("button", { name: "Require Snow park" }),
  ).toHaveAttribute("aria-pressed", "true");
  expect(screen.queryByText("internal_glacier_state")).not.toBeInTheDocument();

  await user.click(avoidGlacier);
  expect(onPreferencesChange).toHaveBeenCalledWith([
    preferences[0],
    preferences[2],
  ]);
});

test("hides unknown factors, objectives, and raw controlled values", () => {
  render(
    <SearchFiltersDrawer
      open
      disabled={false}
      filters={defaultSearchFilters}
      preferences={[
        {
          factor_id: "local_pace",
          mode: "prefer",
          values: ["sensitive_controlled_value"],
          importance: "normal",
        },
        {
          factor_id: "secret_internal_factor",
          mode: "require",
          values: ["private_value"],
          importance: "high",
        },
      ]}
      objectives={[
        { factor_id: "trip_window_snow_fit", importance: "high" },
        { factor_id: "secret_internal_objective", importance: "normal" },
      ]}
      returnFocusRef={createRef<HTMLButtonElement>()}
      onFiltersChange={vi.fn()}
      onPreferencesChange={vi.fn()}
      onObjectivesChange={vi.fn()}
      onClose={vi.fn()}
    />,
  );

  expect(
    screen.getByRole("button", { name: "Prefer Local pace" }),
  ).toBeVisible();
  expect(
    screen.getByRole("button", { name: "Optimize Trip-window snow fit" }),
  ).toBeVisible();
  expect(document.body).not.toHaveTextContent("sensitive_controlled_value");
  expect(document.body).not.toHaveTextContent("private_value");
  expect(document.body).not.toHaveTextContent("secret internal factor");
  expect(document.body).not.toHaveTextContent("secret internal objective");
});
