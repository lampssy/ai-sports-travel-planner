import { createRef } from "react";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Search } from "lucide-react";

import { Action } from "./Action";
import { Alert } from "./Alert";
import { AsyncState } from "./AsyncState";
import { Badge } from "./Badge";
import { Disclosure } from "./Disclosure";
import { MetricTile } from "./MetricTile";
import { SectionHeader } from "./SectionHeader";
import { SegmentedTabs } from "./SegmentedTabs";

describe("Snowcast UI primitives", () => {
  it("exposes semantic action variants and stable sizes", () => {
    const { container } = render(
      <>
        <Action variant="primary" size="sm">Search</Action>
        <Action variant="secondary">Save</Action>
        <Action variant="ghost">Back</Action>
        <Action variant="danger">Clear</Action>
      </>,
    );

    expect(screen.getByRole("button", { name: "Search" })).toHaveClass(
      "snowcast-action--primary",
      "snowcast-action--sm",
    );
    expect(screen.getByRole("button", { name: "Save" })).toHaveClass(
      "snowcast-action--secondary",
      "snowcast-action--md",
    );
    expect(screen.getByRole("button", { name: "Back" })).toHaveClass(
      "snowcast-action--ghost",
    );
    expect(screen.getByRole("button", { name: "Clear" })).toHaveClass(
      "snowcast-action--danger",
    );
    expect(container.querySelectorAll(".snowcast-action")).toHaveLength(4);
  });

  it("requires an accessible name for icon-only actions and supports a title", () => {
    render(
      <Action iconOnly aria-label="Find resorts" title="Find resorts">
        <Search aria-hidden="true" />
      </Action>,
    );

    const action = screen.getByRole("button", { name: "Find resorts" });
    expect(action).toHaveAttribute("title", "Find resorts");
    expect(action).toHaveClass("snowcast-action--icon-only");
  });

  it("forwards a button ref for focus management", () => {
    const ref = createRef<HTMLButtonElement>();
    render(<Action ref={ref}>Reload snow evidence</Action>);

    ref.current?.focus();
    expect(screen.getByRole("button", { name: "Reload snow evidence" })).toHaveFocus();
  });

  it.each(["neutral", "info", "supported", "warning", "brand"] as const)(
    "renders the %s badge variant",
    (variant) => {
      render(<Badge variant={variant}>{variant}</Badge>);
      expect(screen.getByText(variant)).toHaveClass(
        "snowcast-badge",
        `snowcast-badge--${variant}`,
      );
    },
  );

  it.each(["info", "success", "warning", "error"] as const)(
    "keeps a static %s alert out of live regions",
    (variant) => {
      const { container } = render(
        <Alert variant={variant}>{variant} message</Alert>,
      );
      expect(container.firstElementChild).toHaveClass(
        "snowcast-alert",
        `snowcast-alert--${variant}`,
      );
      expect(container.firstElementChild).not.toHaveAttribute("role");
      expect(container.firstElementChild).not.toHaveAttribute("aria-live");
    },
  );

  it("adds live-region urgency only when the caller requests it", () => {
    render(
      <>
        <Alert variant="warning" live="polite">Delayed warning</Alert>
        <Alert variant="error" live="assertive">Immediate error</Alert>
      </>,
    );
    expect(screen.getByRole("status")).toHaveAttribute("aria-live", "polite");
    expect(screen.getByRole("alert")).toHaveAttribute("aria-live", "assertive");
  });

  it("keeps long metric values inside a stable metric footprint", () => {
    render(
      <MetricTile
        label="Snow reliability"
        value="Archive-backed evidence across thirty complete winter seasons"
        detail="High confidence"
      />,
    );

    const metric = screen.getByText("Snow reliability").closest("div");
    expect(metric).toHaveClass("snowcast-metric-tile");
    expect(screen.getByText(/Archive-backed evidence/)).toHaveClass(
      "snowcast-metric-tile__value",
    );
    expect(screen.getByText("High confidence")).toHaveClass(
      "snowcast-metric-tile__detail",
    );
  });

  it("uses native disclosure behavior with an accessible summary", async () => {
    const user = userEvent.setup();
    render(
      <Disclosure label="Snow details">
        <p>Historical snow depth</p>
      </Disclosure>,
    );

    const summary = screen.getByText("Snow details");
    const details = summary.closest("details");
    expect(details).not.toHaveAttribute("open");

    await user.tab();
    expect(summary).toHaveFocus();
    await user.click(summary);
    expect(details).toHaveAttribute("open");
    expect(screen.getByText("Historical snow depth")).toBeVisible();
  });

  it("supports roving focus and linked tab panels", async () => {
    const user = userEvent.setup();
    render(
      <SegmentedTabs
        ariaLabel="Weather metric"
        tabs={[
          { id: "depth", label: "Snow depth", panel: <p>Depth chart</p> },
          { id: "fresh", label: "Fresh snow", panel: <p>Snowfall chart</p> },
          { id: "temperature", label: "Temperature", panel: <p>Temperature chart</p> },
        ]}
      />,
    );

    const tablist = screen.getByRole("tablist", { name: "Weather metric" });
    const tabs = within(tablist).getAllByRole("tab");
    expect(tabs[0]).toHaveAttribute("aria-selected", "true");
    expect(tabs[0]).toHaveAttribute("tabindex", "0");
    expect(tabs[1]).toHaveAttribute("tabindex", "-1");

    const firstPanelId = tabs[0].getAttribute("aria-controls");
    const firstTabId = tabs[0].getAttribute("id");
    const firstPanel = screen.getByRole("tabpanel");
    expect(firstPanel).toHaveAttribute("id", firstPanelId);
    expect(firstPanel).toHaveAttribute("aria-labelledby", firstTabId);

    tabs[0].focus();
    await user.keyboard("{ArrowRight}");
    expect(tabs[1]).toHaveFocus();
    expect(tabs[1]).toHaveAttribute("aria-selected", "true");
    expect(screen.getByText("Snowfall chart")).toBeVisible();

    await user.keyboard("{End}");
    expect(tabs[2]).toHaveFocus();
    expect(screen.getByText("Temperature chart")).toBeVisible();

    await user.keyboard("{Home}");
    expect(tabs[0]).toHaveFocus();

    await user.keyboard("{ArrowLeft}");
    expect(tabs[2]).toHaveFocus();
  });

  it("announces loading politely and exposes retry for failures", async () => {
    const user = userEvent.setup();
    const onRetry = vi.fn();
    const { rerender } = render(
      <AsyncState state="loading" message="Loading snow evidence" />,
    );

    const loading = screen.getByRole("status");
    expect(loading).toHaveAttribute("aria-live", "polite");
    expect(loading).toHaveTextContent("Loading snow evidence");

    rerender(
      <AsyncState
        state="error"
        title="Snow evidence unavailable"
        message="Snow evidence could not be loaded."
        onRetry={onRetry}
      />,
    );
    expect(
      screen.getByRole("heading", { name: "Snow evidence unavailable" }),
    ).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Try again" }));
    expect(onRetry).toHaveBeenCalledOnce();
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Snow evidence could not be loaded.",
    );
  });

  it("keeps an error recovery control mounted and focusable while retrying", async () => {
    const onRetry = vi.fn();
    const user = userEvent.setup();
    render(
      <AsyncState
        state="error"
        title="Saved trip could not be loaded"
        message="Try again."
        retrying
        retryLabel="Retry saved trip"
        onRetry={onRetry}
      />,
    );

    expect(screen.getByRole("alert")).toHaveAttribute("aria-busy", "true");
    const retry = screen.getByRole("button", { name: "Retry saved trip" });
    expect(retry).toHaveAttribute("aria-disabled", "true");
    expect(retry).not.toBeDisabled();
    await user.click(retry);
    expect(onRetry).not.toHaveBeenCalled();
  });

  it("renders a labelled section heading without owning layout", () => {
    render(
      <SectionHeader
        eyebrow="Decision evidence"
        title="Why this trip"
        description="The strongest reasons and limitations."
      />,
    );

    expect(screen.getByRole("heading", { name: "Why this trip" })).toHaveAttribute(
      "id",
    );
    expect(screen.getByText("Decision evidence")).toHaveClass(
      "snowcast-section-header__eyebrow",
    );
  });
});
