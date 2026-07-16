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
