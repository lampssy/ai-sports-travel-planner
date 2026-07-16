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
