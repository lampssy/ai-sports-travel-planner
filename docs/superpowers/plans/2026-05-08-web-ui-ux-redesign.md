# Snowcast Web UI/UX Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the approved Snowcast web UI direction: dark editorial planning entry, compact post-search command bar, evidence-first recommendation board, recommendation dossier, current-trip companion preview, and matching public resort guide styling.

**Architecture:** Keep backend search, parser, ranking, and current-trip contracts unchanged. Refactor the current large React `App.tsx` into focused route and component modules, then restyle each surface from shared Snowcast design tokens. Backend-rendered public resort pages stay server-rendered in FastAPI but adopt the same brand system.

**Tech Stack:** React 18, TypeScript, Vite, Tailwind CSS, Vitest/React Testing Library, Playwright, FastAPI HTML rendering, pytest.

**Implementation status:** Completed in Sprint 34. The checklist below remains the original implementation plan; the shipped implementation kept several pieces inside the existing React app module where that was the lowest-risk path, while preserving the approved UI/UX behavior and visual system.

---

## Accepted Design References

- Review-aligned search/results board concept: `docs/ui-concepts/2026-05-30-review-guidelines/01-search-results-board.png`
- Review-aligned selected-result dossier concept: `docs/ui-concepts/2026-05-30-review-guidelines/02-selected-result-dossier.png`
- Review-aligned current trip concept: `docs/ui-concepts/2026-05-30-review-guidelines/03-current-trip.png`
- Review-aligned public resort guide concept: `docs/ui-concepts/2026-05-30-review-guidelines/04-public-resort-guide.png`
- Accommodation-layer search/results concept: `docs/ui-concepts/2026-06-10-accommodation-guidelines/01-search-results-grouped-accommodation-cues.png`
- Accommodation-layer selected-result dossier concept: `docs/ui-concepts/2026-06-10-accommodation-guidelines/02-selected-dossier-suggested-stays.png`
- Accommodation-layer suggested-stays detail concept: `docs/ui-concepts/2026-06-10-accommodation-guidelines/03-suggested-stays-detail-panel.png`
- Accommodation-layer current-trip concept: `docs/ui-concepts/2026-06-10-accommodation-guidelines/04-current-trip-accommodation-context.png`
- Main-page close-out accepted concept and rendered desktop/mobile screenshots: `docs/ui-concepts/2026-06-11-main-page-closeout/`
- Written spec: `docs/superpowers/specs/2026-05-08-web-ui-ux-redesign-design.md`

The screenshots are visual references. Keep UI text and controls code-native. Use abstract alpine imagery only for brand mood; do not ship fake factual resort photos. For accommodation work, follow the 2026-06-10 concepts over the older dossier/current-trip concepts where they differ.

## Close-Out Evidence

Sprint 34 close-out verified the main page against the accepted concept at desktop `1440x1000` and mobile `390x844`, and kept the public resort guide as a separate server-rendered SEO/content surface. Final screenshot evidence is stored in `docs/ui-concepts/2026-06-11-main-page-closeout/`.

## File Structure

- Modify `frontend/tailwind.config.ts`
  - Adds the approved midnight blue, creamy alpenglow pink, alpine blue, snow, ice, pine, and warning tokens.
- Modify `frontend/src/index.css`
  - Adds page background, focus ring defaults, font smoothing, and reduced-motion baseline.
- Create `frontend/src/ui/SnowcastLogo.tsx`
  - Owns the vector mountain/snow logo mark borrowed from the approved option 3 direction.
- Create `frontend/src/ui/icons.tsx`
  - Owns small production SVG icons used in buttons, chips, result cards, and evidence rows.
- Create `frontend/src/ui/formatters.ts`
  - Moves display-only formatting helpers out of `App.tsx`.
- Create `frontend/src/ui/snowcastCopy.ts`
  - Owns stable product copy such as the April snow-risk signal and evidence-mode labels.
- Create `frontend/src/ui/EvidenceQualityBadge.tsx`
  - Owns consistent Archive-backed / Forecast-assisted / Fallback-heavy display.
- Create `frontend/src/ui/TripEntityStack.tsx`
  - Owns the repeated Destination / Ski area / Stay base hierarchy.
- Create `frontend/src/ui/AccommodationEvidenceBadge.tsx`
  - Owns provider-backed / stale / estimate-only lodging evidence labels.
- Create `frontend/src/search/searchState.ts`
  - Owns `defaultFilters`, stored search-state shape, route helpers, validation, parse-merge logic, and applied chip building.
- Create `frontend/src/search/searchState.test.ts`
  - Unit-tests the extracted search helpers before route UI changes.
- Create `frontend/src/search/SearchPage.tsx`
  - Owns the search route composition and decides initial vs post-search layout.
- Create `frontend/src/search/SearchCommand.tsx`
  - Owns the dark editorial initial command and compact post-search command bar.
- Create `frontend/src/search/FilterChips.tsx`
  - Owns visible removable trip-state chips.
- Create `frontend/src/search/ClarificationCards.tsx`
  - Owns bounded clarification cards.
- Create `frontend/src/search/RefineDrawer.tsx`
  - Owns manual filter controls in a side drawer.
- Create `frontend/src/search/RecommendationBoard.tsx`
  - Owns results heading, empty/loading states, result count, sort display, and card list.
- Create `frontend/src/search/RecommendationCard.tsx`
  - Owns evidence-first result card anatomy.
- Create `frontend/src/search/DecisionRail.tsx`
  - Owns selected-result explanation, clarification summary, evidence mode, and tradeoffs.
- Create `frontend/src/resort/SelectedResortPage.tsx`
  - Owns `/resorts/:resortId` app-state dossier route.
- Create `frontend/src/resort/ResultDossier.tsx`
  - Owns verdict hero, why-this-leads section, April/snow-risk band, trip option, evidence ledger, highlights, risks, and trip-fit explanation.
- Create `frontend/src/resort/SuggestedStays.tsx`
  - Owns optional hotel/apartment suggestions under the selected stay base.
- Modify `frontend/src/types.ts`
  - Adds optional lodging/suggested-stay types to `TripOption` without requiring all API responses to include them.
- Create `frontend/src/trip/CurrentTripView.tsx`
  - Owns `/current-trip`.
- Modify `frontend/src/App.tsx`
  - Keeps application state, API calls, navigation, and top-level route composition only.
- Modify `frontend/src/App.test.tsx`
  - Updates RTL coverage for the new layout while preserving API behavior tests.
- Modify `frontend/tests/e2e/app.spec.ts`
  - Updates Playwright smoke journeys for the new search command, refine drawer, dossier, and current-trip layout.
- Modify `app/public_pages.py`
  - Restyles server-rendered public resort guide pages using the same visual system.
- Modify `tests/test_public_pages.py`
  - Keeps metadata/SEO assertions and adds checks for the new public-page content hierarchy.
- Modify `PROJECT.md`
  - Adds the accepted UI direction and implementation-plan link to the current roadmap/status.
- Modify `docs/engineering-notes.md`
  - Adds the durable frontend design-system and route-boundary decision.

Do not modify `/api/search`, `/api/parse-query`, current-trip API shape, ranking weights, database models, package dependencies, or mobile Flutter code.

## Design System Inventory

Use these approximated implementation tokens:

```ts
const snowcastPalette = {
  midnight: "#021a35",
  midnightSoft: "#08284f",
  snow: "#f8fbff",
  ice: "#edf6fb",
  powder: "#dbeaf5",
  ink: "#07182f",
  textMuted: "#53657d",
  line: "#cbd9e8",
  alpenglow: "#ff5f8f",
  alpenglowSoft: "#ffe1eb",
  alpineBlue: "#0b5fb8",
  pine: "#087f68",
  amber: "#f59e0b",
  warning: "#f15a24",
};
```

Typography stays with the existing `Sora` display and `Manrope` body stack. Headings should be confident and tight, but not viewport-scaled. UI labels use uppercase tracking around `0.12em` to `0.18em`, not heavier letter spacing than the current app.

Semantic color usage:

- `alpenglow`: travel-window emphasis, selected date accents, brand atmosphere.
- `amber` / `warning`: risk, watchouts, disruption, clarification urgency.
- `pine`: positive status and strong fit.
- `alpineBlue`: evidence, data, archive/provenance cues.

Do not use pink as the primary risk color. Date-window risks can include an alpenglow date accent, but warning icons and risk text should use amber/orange.

Recommendation language:

- Use `Trip fit` or `Match score`, not `Confidence`, for user-facing percentage labels.
- Use `Snow reliability` for archive/history fit.
- Use `Snow outlook` for current or forecast-assisted conditions.
- Use `Evidence quality` as the umbrella trust concept.
- Use `Planning update`, not `What changed since last check`, on the current-trip surface.

Product entity hierarchy:

```text
Destination
Cervinia

Ski area
Ski Cervinia

Stay base
Breuil-Cervinia

Suggested stay
Hotel or apartment under the selected stay base
```

Render this hierarchy consistently on result cards, selected-result details, and any compact decision summary. Do not make users infer whether a name is a destination, ski area, stay base, or hotel/accommodation.

Accommodation layer rules:

- The main result list remains grouped by destination/ski area.
- Hotels and apartments appear only under the selected stay base in the detail page.
- A main result card can say `Suggested stays available` only when provider-backed accommodation data exists.
- If provider-backed data is absent, show stay-base price estimates and the existing booking handoff. Do not fake property cards.
- Suggested stays must show freshness/evidence: `Provider-backed · checked 2h ago`, `Provider-backed · stale`, or `Stay-base estimate, not live hotel inventory`.
- Hotel choice can update exact lodging price, booking CTA, and lodging-specific tradeoffs; it should not replace the mountain/snow recommendation hierarchy.

Core copy to preserve:

```ts
export const snowRiskSignal = {
  title: "April is risky below 1,800m",
  body: "Use archive snow evidence before you commit.",
};

export const initialHeroCopy = {
  heading: "Book the mountain, not the guesswork.",
  body:
    "Search by trip intent. Snowcast ranks ski resorts by snow window, stay fit, travel effort, and evidence.",
};

export const evidenceQualityCopy = {
  archiveBacked: {
    label: "Archive-backed",
    trust: "High trust",
    description: "Historical seasons support this travel window.",
  },
  forecastAssisted: {
    label: "Forecast-assisted",
    trust: "Medium trust",
    description: "Current forecast supports the recommendation.",
  },
  fallbackHeavy: {
    label: "Fallback-heavy",
    trust: "Lower trust",
    description: "Sparse data means seasonal traits carry more of the answer.",
  },
};
```

---

### Task 1: Visual Tokens, Logo, And Shared UI Primitives

**Files:**
- Modify: `frontend/tailwind.config.ts`
- Modify: `frontend/src/index.css`
- Create: `frontend/src/ui/SnowcastLogo.tsx`
- Create: `frontend/src/ui/icons.tsx`
- Create: `frontend/src/ui/snowcastCopy.ts`
- Create: `frontend/src/ui/EvidenceQualityBadge.tsx`
- Create: `frontend/src/ui/TripEntityStack.tsx`
- Modify: `frontend/src/App.test.tsx`

- [ ] **Step 1: Write the failing initial-brand test**

Add this test near the existing `"renders the structured search form"` test in `frontend/src/App.test.tsx`:

```tsx
test("renders the approved Snowcast planning entry copy", () => {
  vi.stubGlobal("fetch", mockFetchRoutes());

  render(<App />);

  expect(screen.getByText("SNOWCAST")).toBeInTheDocument();
  expect(
    screen.getByRole("heading", {
      name: /book the mountain, not the guesswork/i,
    }),
  ).toBeInTheDocument();
  expect(screen.getByText(/april is risky below 1,800m/i)).toBeInTheDocument();
  expect(
    screen.getByText(/use archive snow evidence before you commit/i),
  ).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the focused failing test**

Run:

```bash
cd frontend && npm test -- App.test.tsx -t "approved Snowcast planning entry copy"
```

Expected: fail because the current first viewport still uses the older heading and no logo component.

- [ ] **Step 3: Add Tailwind tokens**

Replace the `extend.colors` block in `frontend/tailwind.config.ts` with:

```ts
colors: {
  canvas: "#f8fbff",
  ink: "#07182f",
  midnight: "#021a35",
  midnightSoft: "#08284f",
  snow: "#f8fbff",
  ice: "#edf6fb",
  powder: "#dbeaf5",
  line: "#cbd9e8",
  muted: "#53657d",
  alpenglow: "#ff5f8f",
  alpenglowSoft: "#ffe1eb",
  alpineBlue: "#0b5fb8",
  pine: "#087f68",
  ember: "#f15a24",
  amber: "#f59e0b",
  frost: "#dbeaf5",
  alpine: "#0b5fb8",
},
```

Replace `boxShadow.panel` with:

```ts
panel: "0 24px 60px rgba(7, 24, 47, 0.14)",
soft: "0 18px 42px rgba(7, 24, 47, 0.10)",
```

- [ ] **Step 4: Update global CSS**

Replace `frontend/src/index.css` with:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  color: #07182f;
  background: #f8fbff;
}

html {
  scroll-behavior: smooth;
}

body {
  margin: 0;
  min-width: 320px;
  min-height: 100vh;
  font-family: "Manrope", ui-sans-serif, system-ui;
  -webkit-font-smoothing: antialiased;
  text-rendering: geometricPrecision;
}

button,
input,
select,
textarea {
  font: inherit;
}

button:focus-visible,
a:focus-visible,
input:focus-visible,
select:focus-visible,
textarea:focus-visible {
  outline: 3px solid rgba(255, 95, 143, 0.55);
  outline-offset: 3px;
}

@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    scroll-behavior: auto !important;
    transition-duration: 0.01ms !important;
  }
}
```

- [ ] **Step 5: Create the logo component**

Create `frontend/src/ui/SnowcastLogo.tsx`:

```tsx
export function SnowcastLogo({ compact = false }: { compact?: boolean }) {
  return (
    <div className="inline-flex items-center gap-3" aria-label="SNOWCAST">
      <svg
        aria-hidden="true"
        className={compact ? "h-9 w-9" : "h-11 w-11"}
        viewBox="0 0 64 64"
        fill="none"
      >
        <path
          d="M6 50 25 14l8 15 7-11 18 32H42l-6-10-7 10H6Z"
          fill="currentColor"
          className="text-white"
        />
        <path
          d="m25 14 8 15 7-11"
          stroke="#ff5f8f"
          strokeWidth="4"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <path
          d="M30 45v-9m0 0-6-4m6 4 6-4m-6 4-6 4m6-4 6 4"
          stroke="#0b5fb8"
          strokeWidth="3"
          strokeLinecap="round"
        />
      </svg>
      <span className="font-display text-2xl font-semibold tracking-[0.04em] text-white">
        SNOWCAST
      </span>
    </div>
  );
}
```

- [ ] **Step 6: Create shared icons**

Create `frontend/src/ui/icons.tsx`:

```tsx
import type { SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement>;

export function SearchIcon(props: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" {...props}>
      <circle cx="11" cy="11" r="7" />
      <path d="m16.5 16.5 4 4" strokeLinecap="round" />
    </svg>
  );
}

export function CalendarIcon(props: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" {...props}>
      <path d="M7 3v4M17 3v4M4 9h16M5 5h14a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1Z" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function AlertIcon(props: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" {...props}>
      <path d="M12 4 3 20h18L12 4Z" strokeLinejoin="round" />
      <path d="M12 9v5M12 17h.01" strokeLinecap="round" />
    </svg>
  );
}

export function CloseIcon(props: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" {...props}>
      <path d="m6 6 12 12M18 6 6 18" strokeLinecap="round" />
    </svg>
  );
}
```

- [ ] **Step 7: Create shared Snowcast copy**

Create `frontend/src/ui/snowcastCopy.ts`:

```ts
export const snowRiskSignal = {
  title: "April is risky below 1,800m",
  body: "Use archive snow evidence before you commit.",
};

export const initialHeroCopy = {
  heading: "Book the mountain, not the guesswork.",
  body:
    "Search by trip intent. Snowcast ranks ski resorts by snow window, stay fit, travel effort, and evidence.",
};
```

- [ ] **Step 8: Create evidence quality badge**

Create `frontend/src/ui/EvidenceQualityBadge.tsx`:

```tsx
import type { SearchResult } from "../types";

type EvidenceQuality = "archive_backed" | "forecast_assisted" | "fallback_heavy";

export function getEvidenceQuality(result: SearchResult): EvidenceQuality {
  if (
    result.planning_weather_metrics?.evidence_years &&
    result.planning_weather_metrics.evidence_years >= 3
  ) {
    return "archive_backed";
  }
  if (result.planning_evidence_count && result.planning_evidence_count >= 3) {
    return "archive_backed";
  }
  if (result.conditions_provenance.source_type === "forecast") {
    return "forecast_assisted";
  }
  return "fallback_heavy";
}

export function formatEvidenceQuality(value: EvidenceQuality) {
  if (value === "archive_backed") {
    return "Archive-backed";
  }
  if (value === "forecast_assisted") {
    return "Forecast-assisted";
  }
  return "Fallback-heavy";
}

export function EvidenceQualityBadge({ result }: { result: SearchResult }) {
  const quality = getEvidenceQuality(result);
  const tone =
    quality === "archive_backed"
      ? "border-alpineBlue/20 bg-alpineBlue/10 text-alpineBlue"
      : quality === "forecast_assisted"
        ? "border-pine/20 bg-pine/10 text-pine"
        : "border-amber/30 bg-amber/10 text-amber";

  return (
    <span className={`inline-flex rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-[0.14em] ${tone}`}>
      {formatEvidenceQuality(quality)}
    </span>
  );
}
```

- [ ] **Step 9: Create trip entity hierarchy component**

Create `frontend/src/ui/TripEntityStack.tsx`:

```tsx
interface TripEntityStackProps {
  destination: string;
  skiArea: string;
  stayBase: string;
  compact?: boolean;
}

export function TripEntityStack({
  destination,
  skiArea,
  stayBase,
  compact = false,
}: TripEntityStackProps) {
  const itemClass = compact ? "min-w-[120px]" : "min-w-[150px]";

  return (
    <dl className="grid gap-3 sm:grid-cols-3">
      <div className={itemClass}>
        <dt className="text-xs font-semibold uppercase tracking-[0.14em] text-muted">
          Destination
        </dt>
        <dd className="mt-1 font-semibold text-ink">{destination}</dd>
      </div>
      <div className={itemClass}>
        <dt className="text-xs font-semibold uppercase tracking-[0.14em] text-muted">
          Ski area
        </dt>
        <dd className="mt-1 font-semibold text-ink">{skiArea}</dd>
      </div>
      <div className={itemClass}>
        <dt className="text-xs font-semibold uppercase tracking-[0.14em] text-muted">
          Stay base
        </dt>
        <dd className="mt-1 font-semibold text-ink">{stayBase}</dd>
      </div>
    </dl>
  );
}
```

- [ ] **Step 10: Create accommodation evidence badge**

Create `frontend/src/ui/AccommodationEvidenceBadge.tsx`:

```tsx
import type { SuggestedStay } from "../types";

export function formatAccommodationEvidence(stay: SuggestedStay) {
  if (stay.evidence_status === "provider_backed" && stay.checked_at_label) {
    return `Provider-backed · ${stay.checked_at_label}`;
  }
  if (stay.evidence_status === "provider_backed_stale") {
    return "Provider-backed · stale";
  }
  return "Stay-base estimate, not live hotel inventory";
}

export function AccommodationEvidenceBadge({ stay }: { stay: SuggestedStay }) {
  const isFresh = stay.evidence_status === "provider_backed";
  const isStale = stay.evidence_status === "provider_backed_stale";
  const tone = isFresh
    ? "border-pine/20 bg-pine/10 text-pine"
    : isStale
      ? "border-amber/30 bg-amber/10 text-amber"
      : "border-line bg-ice text-muted";

  return (
    <span className={`inline-flex rounded-full border px-3 py-1 text-xs font-semibold ${tone}`}>
      {formatAccommodationEvidence(stay)}
    </span>
  );
}
```

- [ ] **Step 11: Run the focused test**

Run:

```bash
cd frontend && npm test -- App.test.tsx -t "approved Snowcast planning entry copy"
```

Expected: pass after the `App.tsx` route shell uses these primitives in Task 3.

- [ ] **Step 12: Commit**

```bash
git add frontend/tailwind.config.ts frontend/src/index.css frontend/src/ui/SnowcastLogo.tsx frontend/src/ui/icons.tsx frontend/src/ui/snowcastCopy.ts frontend/src/ui/EvidenceQualityBadge.tsx frontend/src/ui/TripEntityStack.tsx frontend/src/ui/AccommodationEvidenceBadge.tsx frontend/src/App.test.tsx
git commit -m "feat: add snowcast visual system primitives"
```

---

### Task 2: Extract Search State Helpers Before Repainting UI

**Files:**
- Modify: `frontend/src/types.ts`
- Create: `frontend/src/ui/formatters.ts`
- Create: `frontend/src/search/searchState.ts`
- Create: `frontend/src/search/searchState.test.ts`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Write helper tests**

Create `frontend/src/search/searchState.test.ts`:

```ts
import { describe, expect, test } from "vitest";

import type { ParsedQueryResponse, SearchFilters } from "../types";
import {
  buildAppliedFilterChips,
  defaultFilters,
  mergeParsedFilters,
  routeToPath,
  validateSearchFilters,
} from "./searchState";

describe("searchState", () => {
  test("builds user-facing applied filter chips", () => {
    const filters: SearchFilters = {
      ...defaultFilters,
      location: "Italy",
      minPrice: "150",
      maxPrice: "320",
      skillLevel: "intermediate",
      stars: "2",
      originText: "Warsaw",
      travelWindowMode: "dates",
      tripStartDate: "2027-04-21",
      tripEndDate: "2027-04-27",
    };

    expect(buildAppliedFilterChips(filters).map((chip) => chip.label)).toEqual([
      "Italy",
      "Intermediate",
      "EUR 150-320 nightly",
      "Standard+ quality",
      "Warsaw origin",
      "Apr 21, 2027 to Apr 27, 2027",
    ]);
  });

  test("merges exact parsed dates ahead of parsed month", () => {
    const parsed: ParsedQueryResponse = {
      filters: {
        location: "Italy",
        skill_level: "intermediate",
        travel_month: 4,
        trip_start_date: "2027-04-21",
        trip_end_date: "2027-04-27",
      },
      confidence: 0.92,
      unknown_parts: [],
    };

    const { filters, shouldOpenRefine } = mergeParsedFilters(defaultFilters, parsed);

    expect(shouldOpenRefine).toBe(false);
    expect(filters.location).toBe("Italy");
    expect(filters.travelWindowMode).toBe("dates");
    expect(filters.travelMonth).toBe("");
    expect(filters.tripStartDate).toBe("2027-04-21");
    expect(filters.tripEndDate).toBe("2027-04-27");
  });

  test("validates exact date range before search", () => {
    expect(
      validateSearchFilters({
        ...defaultFilters,
        travelWindowMode: "dates",
        tripStartDate: "2027-04-27",
        tripEndDate: "2027-04-21",
      }),
    ).toBe("Trip end date must be on or after the start date.");
  });

  test("routes current trip and selected resort paths", () => {
    expect(routeToPath({ name: "search" })).toBe("/");
    expect(routeToPath({ name: "current_trip" })).toBe("/current-trip");
    expect(routeToPath({ name: "resort", resortId: "cervinia" })).toBe(
      "/resorts/cervinia",
    );
  });
});
```

- [ ] **Step 2: Run helper tests to verify failure**

Run:

```bash
cd frontend && npm test -- searchState.test.ts
```

Expected: fail because `frontend/src/search/searchState.ts` does not exist.

- [ ] **Step 3: Add optional suggested-stay types**

Add these types to `frontend/src/types.ts` near `TripOption`:

```ts
export type SuggestedStayEvidenceStatus =
  | "provider_backed"
  | "provider_backed_stale"
  | "estimate_only";

export interface SuggestedStay {
  stay_id: string;
  name: string;
  accommodation_type: "hotel" | "apartment" | "aparthotel" | "guesthouse";
  provider_name: string;
  price_label: string;
  checked_at_label: string | null;
  evidence_status: SuggestedStayEvidenceStatus;
  access_label: string | null;
  fit_reason: string;
  booking_url: string | null;
}
```

Then add an optional field to `TripOption`:

```ts
suggested_stays?: SuggestedStay[];
```

This field is optional so current backend responses continue to parse. Suggested-stay UI must render only when this array is present and non-empty.

- [ ] **Step 4: Create `frontend/src/ui/formatters.ts`**

Move the current display helpers from the bottom of `App.tsx` into `frontend/src/ui/formatters.ts` and export these exact functions:

```ts
import type { BookingStatus, ProvenanceInfo, SearchResult, SearchFilters, TripContext } from "../types";

export function capitalize(value: string) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

export function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function formatQualityTier(value: number) {
  const labels: Record<number, string> = {
    1: "Budget",
    2: "Standard",
    3: "Premium",
  };
  return labels[value] ?? `Tier ${value}`;
}

export function formatBudgetMode(value: TripContext["budget_mode"]) {
  if (value === "lodging_nightly") {
    return "nightly lodging";
  }
  if (value === "total_trip") {
    return "total trip";
  }
  return "unspecified";
}

export function formatAvailability(value: SearchResult["availability_status"]) {
  const labels: Record<SearchResult["availability_status"], string> = {
    open: "Low disruption risk",
    limited: "Some disruption risk",
    temporarily_closed: "High disruption risk",
    out_of_season: "Out of season",
  };
  return labels[value];
}

export function formatBookingStatus(value: BookingStatus) {
  return value.replace(/_/g, " ");
}
```

Also move the remaining current helpers with their existing bodies: `formatMonth`, `formatEnumLabel`, `formatTravelTolerance`, `formatSourceType`, `formatFreshnessStatus`, `formatSnowDepth`, `formatDriveDuration`, `formatTimestamp`, `formatRelativeTime`, and `formatTrustCue`.

- [ ] **Step 5: Create `frontend/src/search/searchState.ts`**

Move the current route, storage-state, validation, parse-merge, and chip helpers into `frontend/src/search/searchState.ts`. Use this parse-merge signature:

```ts
export function mergeParsedFilters(
  currentFilters: SearchFilters,
  parsed: ParsedQueryResponse,
): { filters: SearchFilters; shouldOpenRefine: boolean } {
  const nextFilters = { ...currentFilters };
  const { filters: parsedFilters } = parsed;
  let shouldOpenRefine = false;

  if (parsedFilters.location) {
    nextFilters.location = parsedFilters.location;
  }
  if (parsedFilters.min_price !== undefined) {
    nextFilters.minPrice = String(parsedFilters.min_price);
  }
  if (parsedFilters.max_price !== undefined) {
    nextFilters.maxPrice = String(parsedFilters.max_price);
  }
  if (parsedFilters.stars !== undefined) {
    nextFilters.stars = String(parsedFilters.stars) as SearchFilters["stars"];
  }
  if (parsedFilters.skill_level) {
    nextFilters.skillLevel = parsedFilters.skill_level;
  }
  if (parsedFilters.lift_distance) {
    nextFilters.liftDistance = parsedFilters.lift_distance;
    shouldOpenRefine = true;
  }
  if (parsedFilters.budget_flex !== undefined) {
    nextFilters.budgetFlex = String(parsedFilters.budget_flex);
    shouldOpenRefine = true;
  }
  if (
    parsed.trip_context &&
    Object.prototype.hasOwnProperty.call(parsed.trip_context, "origin_text") &&
    parsed.trip_context.origin_text !== undefined
  ) {
    nextFilters.originText = parsed.trip_context.origin_text ?? "";
    shouldOpenRefine = true;
  }
  if (parsedFilters.trip_start_date && parsedFilters.trip_end_date) {
    nextFilters.travelWindowMode = "dates";
    nextFilters.tripStartDate = parsedFilters.trip_start_date;
    nextFilters.tripEndDate = parsedFilters.trip_end_date;
    nextFilters.travelMonth = "";
  } else if (parsedFilters.travel_month !== undefined) {
    nextFilters.travelWindowMode = "month";
    nextFilters.travelMonth = parsedFilters.travel_month;
    nextFilters.tripStartDate = "";
    nextFilters.tripEndDate = "";
  }

  return { filters: nextFilters, shouldOpenRefine };
}
```

Use this chip wording change in `buildAppliedFilterChips`:

```ts
if (filters.minPrice || filters.maxPrice) {
  chips.push({
    key: "budget",
    label: `EUR ${filters.minPrice || "?"}-${filters.maxPrice || "?"} nightly`,
  });
}
if (filters.originText.trim()) {
  chips.push({
    key: "origin",
    label: `${filters.originText.trim()} origin`,
  });
}
```

- [ ] **Step 6: Update `App.tsx` imports and call sites**

Import helpers from the new modules:

```tsx
import {
  defaultFilters,
  emptyStoredSearchState,
  emptyTripContext,
  buildAppliedFilterChips,
  readCurrentRoute,
  readStoredSearchState,
  routeToPath,
  validateSearchFilters,
  writeStoredSearchState,
} from "./search/searchState";
```

In `handleSubmit`, replace the local parse-merge call with:

```tsx
const merged = mergeParsedFilters(defaultFilters, parsed);
nextFilters = merged.filters;
setFilters(nextFilters);
if (merged.shouldOpenRefine) {
  setIsAdvancedOpen(true);
}
```

Remove duplicate helper definitions from `App.tsx`.

- [ ] **Step 7: Run helper and app tests**

Run:

```bash
cd frontend && npm test -- searchState.test.ts App.test.tsx
```

Expected: pass with no behavior change except approved chip wording updates.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/types.ts frontend/src/ui/formatters.ts frontend/src/search/searchState.ts frontend/src/search/searchState.test.ts frontend/src/App.tsx frontend/src/App.test.tsx
git commit -m "refactor: extract frontend search state helpers"
```

---

### Task 3: Search Command, Chips, Clarifications, And Refine Drawer

**Files:**
- Create: `frontend/src/search/SearchCommand.tsx`
- Create: `frontend/src/search/FilterChips.tsx`
- Create: `frontend/src/search/ClarificationCards.tsx`
- Create: `frontend/src/search/RefineDrawer.tsx`
- Create: `frontend/src/search/SearchPage.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.test.tsx`
- Modify: `frontend/tests/e2e/app.spec.ts`

- [ ] **Step 1: Write failing RTL tests for initial and post-search layout**

Replace the first render test expectations in `frontend/src/App.test.tsx` with:

```tsx
test("renders the initial editorial search command without the refine drawer", () => {
  vi.stubGlobal("fetch", mockFetchRoutes());

  render(<App />);

  expect(screen.getByText("SNOWCAST")).toBeInTheDocument();
  expect(
    screen.getByRole("heading", {
      name: /book the mountain, not the guesswork/i,
    }),
  ).toBeInTheDocument();
  expect(screen.getByLabelText(/what are you looking for/i)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /find resorts/i })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /show refine filters/i })).toBeInTheDocument();
  expect(screen.queryByRole("dialog", { name: /refine trip state/i })).not.toBeInTheDocument();
  expect(
    screen.queryByRole("heading", { name: /recommended resorts/i }),
  ).not.toBeInTheDocument();
});

test("opens the refine drawer from the search command", async () => {
  vi.stubGlobal("fetch", mockFetchRoutes());

  const user = userEvent.setup();
  render(<App />);

  await user.click(screen.getByRole("button", { name: /show refine filters/i }));

  expect(
    screen.getByRole("dialog", { name: /refine trip state/i }),
  ).toBeInTheDocument();
  expect(screen.getByLabelText(/location/i)).toHaveValue("France");
  expect(screen.getByLabelText(/travel origin/i)).toBeInTheDocument();
});

test("shows parse certainty and high-impact clarifications above rankings", async () => {
  const fetchMock = mockFetchRoutes({
    parseResponse: clarificationParseResponse,
    searchResponses: [emptyResponse],
  });
  vi.stubGlobal("fetch", fetchMock);

  const user = userEvent.setup();
  render(<App />);

  await user.type(
    screen.getByLabelText(/what are you looking for/i),
    "France ski trip with EUR 1500 budget",
  );
  await user.click(screen.getByRole("button", { name: /find resorts/i }));

  expect(await screen.findByText(/search parsed/i)).toBeInTheDocument();
  expect(screen.getByText(/parsed confidently/i)).toBeInTheDocument();
  expect(screen.getByText(/clarification needed/i)).toBeInTheDocument();
  expect(
    screen.getByText(/results shown using nightly lodging budget/i),
  ).toBeInTheDocument();
  expect(
    screen.getByText(/is this budget for nightly lodging or the whole trip/i),
  ).toBeInTheDocument();
});
```

- [ ] **Step 2: Run focused tests to verify failure**

Run:

```bash
cd frontend && npm test -- App.test.tsx -t "initial editorial search command|refine drawer"
```

Expected: fail because the old form renders inline filters and the new drawer components do not exist.

- [ ] **Step 3: Create `SearchCommand.tsx`**

Create a component with this public prop contract:

```tsx
import type { FormEvent } from "react";

import { AlertIcon, CalendarIcon, SearchIcon } from "../ui/icons";
import { SnowcastLogo } from "../ui/SnowcastLogo";
import { initialHeroCopy, snowRiskSignal } from "../ui/snowcastCopy";

interface SearchCommandProps {
  compact: boolean;
  tripBrief: string;
  isLoading: boolean;
  isParsing: boolean;
  onTripBriefChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onOpenRefine: () => void;
  onNavigateSearch: () => void;
  onNavigateCurrentTrip: () => void;
  currentRouteName: "search" | "resort" | "current_trip";
}
```

The initial state should render:

- `SnowcastLogo`
- nav buttons for `Search` and `Current trip`
- H1 `Book the mountain, not the guesswork.`
- snow-risk callout with `AlertIcon`
- one large input row with label `What are you looking for?`
- visible example text `Ski in Italy from Warsaw, 21-27 Apr 2027`
- primary button accessible name `Find resorts`
- secondary button accessible name `Show refine filters`
- example chips `late April snow`, `near lifts`, `drive from Warsaw`, `intermediate`

The compact state should render:

- dark horizontal command bar
- `SnowcastLogo compact`
- same input label and value
- snow-risk callout
- `Search` and `Current trip` segmented navigation
- accessible `Find resorts` submit button
- accessible `Show refine filters` button

- [ ] **Step 4: Create `FilterChips.tsx`**

Use this prop contract:

```tsx
import type { AppliedFilterKey } from "./searchState";

interface FilterChip {
  key: AppliedFilterKey;
  label: string;
}

interface FilterChipsProps {
  chips: FilterChip[];
  onRemove: (key: AppliedFilterKey) => void;
  onOpenRefine: () => void;
}
```

Each chip button must keep the accessible name `Remove ${chip.label}` so existing tests can query removals.

- [ ] **Step 5: Create `ClarificationCards.tsx`**

Use this prop contract:

```tsx
import type { TripClarification, TripClarificationOption } from "../types";

interface ClarificationCardsProps {
  clarifications: TripClarification[];
  onApply: (clarificationId: string, option: TripClarificationOption) => void;
}
```

Render each clarification as a compact card with question, reason, and option buttons. Preserve option labels exactly from the API.

- [ ] **Step 6: Create `RefineDrawer.tsx`**

Use this prop contract:

```tsx
import type { SearchFilters, TravelMonth, TravelWindowMode } from "../types";

interface RefineDrawerProps {
  open: boolean;
  filters: SearchFilters;
  onClose: () => void;
  onFiltersChange: (filters: SearchFilters) => void;
  onTravelWindowModeChange: (mode: TravelWindowMode) => void;
}
```

The drawer root should be:

```tsx
<aside
  role="dialog"
  aria-label="Refine trip state"
  className="fixed inset-y-0 right-0 z-40 w-full max-w-[440px] overflow-y-auto border-l border-line bg-white p-6 shadow-panel"
>
```

Group visible controls in this order:

1. Trip: location, skill level, quality tier.
2. Snow window: any time, month, exact dates.
3. Stay budget: min per night, max per night, budget mode display when `tripContext` is present in Task 4.
4. Travel effort: origin, max drive, tolerance.

Preserve labels used by current tests: `Location`, `Skill level`, `Min price`, `Max price`, `Travel origin`, `Max drive hours`, `Travel tolerance`, `Travel month`, `Trip start date`, `Trip end date`, `Minimum quality`, `Lift distance`, and `Budget flex`.

- [ ] **Step 7: Create `SearchPage.tsx` and wire `App.tsx`**

`SearchPage` should receive state and callbacks from `App.tsx`. Keep API calls and route navigation in `App.tsx`.

Compute three search-state groups before rendering chips and recommendations:

```tsx
const parsedConfidently = buildAppliedFilterChips(filters).filter(
  (chip) => chip.key !== "stars",
);
const assumed = filters.stars ? [`${formatQualityTier(Number(filters.stars))}+ quality`] : [];
const hasHighImpactClarifications = clarifications.length > 0;
```

Use these groups to render a compact `Search parsed` panel above the recommendation board when `parsedQuery` exists. High-impact clarification cards should appear directly below that panel and above ranking results, not only inside the decision rail.

Use this high-level render structure:

```tsx
<div className="min-h-screen bg-snow text-ink">
  <SearchCommand
    compact={showRecommendationsPanel}
    tripBrief={tripBrief}
    isLoading={isLoading}
    isParsing={isParsing}
    onTripBriefChange={onTripBriefChange}
    onSubmit={onSubmit}
    onOpenRefine={onOpenRefine}
    onNavigateSearch={onNavigateSearch}
    onNavigateCurrentTrip={onNavigateCurrentTrip}
    currentRouteName={currentRouteName}
  />
  {showRecommendationsPanel ? (
    <main className="mx-auto grid w-full max-w-[1500px] gap-6 px-6 py-6 xl:grid-cols-[1fr_360px]">
      <section className="min-w-0">
        <FilterChips
          chips={appliedFilterChips}
          onRemove={onRemoveAppliedFilter}
          onOpenRefine={onOpenRefine}
        />
        <ClarificationCards
          clarifications={clarifications}
          onApply={onApplyClarification}
        />
        <RecommendationBoard
          filters={filters}
          results={results}
          selectedResult={selectedResult}
          error={error}
          isLoading={isLoading}
          hasSearched={hasSearched}
          onSelectResult={onSelectResult}
        />
      </section>
      <DecisionRail
        selectedResult={selectedResult}
        clarifications={clarifications}
        onApplyClarification={onApplyClarification}
      />
    </main>
  ) : (
    <section className="mx-auto max-w-[1500px] px-6 py-10">
      <FilterChips
        chips={appliedFilterChips}
        onRemove={onRemoveAppliedFilter}
        onOpenRefine={onOpenRefine}
      />
      <ClarificationCards
        clarifications={clarifications}
        onApply={onApplyClarification}
      />
    </section>
  )}
  <RefineDrawer
    open={isRefineOpen}
    filters={filters}
    onClose={onCloseRefine}
    onFiltersChange={onFiltersChange}
    onTravelWindowModeChange={onTravelWindowModeChange}
  />
</div>
```

- [ ] **Step 8: Update tests that open filters**

Replace test clicks on:

```tsx
screen.getByRole("button", { name: /show/i })
```

with:

```tsx
screen.getByRole("button", { name: /show refine filters/i })
```

Keep assertions around search URL parameters unchanged.

- [ ] **Step 9: Run app and e2e tests**

Run:

```bash
cd frontend && npm test -- App.test.tsx
cd frontend && npm run test:e2e
```

Expected: pass. The Playwright snapshots may change but user journeys remain the same.

- [ ] **Step 10: Commit**

```bash
git add frontend/src/search/SearchCommand.tsx frontend/src/search/FilterChips.tsx frontend/src/search/ClarificationCards.tsx frontend/src/search/RefineDrawer.tsx frontend/src/search/SearchPage.tsx frontend/src/App.tsx frontend/src/App.test.tsx frontend/tests/e2e/app.spec.ts
git commit -m "feat: rebuild search command and refine drawer"
```

---

### Task 4: Recommendation Board, Evidence Cards, And Decision Rail

**Files:**
- Create: `frontend/src/search/RecommendationBoard.tsx`
- Create: `frontend/src/search/RecommendationCard.tsx`
- Create: `frontend/src/search/DecisionRail.tsx`
- Modify: `frontend/src/search/SearchPage.tsx`
- Modify: `frontend/src/App.test.tsx`

- [ ] **Step 1: Write failing board/card tests**

Add:

```tsx
test("post-search results render as an evidence-first recommendation board", async () => {
  vi.stubGlobal("fetch", mockFetchRoutes({ searchResponses: [travelEffortResponse] }));

  const user = userEvent.setup();
  render(<App />);

  await user.click(screen.getByRole("button", { name: /find resorts/i }));

  expect(
    await screen.findByRole("heading", { name: /ranked resorts for your trip/i }),
  ).toBeInTheDocument();
  expect(screen.getByText(/best matches for/i)).toBeInTheDocument();
  expect(screen.getByText(/#1/i)).toBeInTheDocument();
  expect(screen.getByText(/Best late-season reliability/i)).toBeInTheDocument();
  expect(screen.getByText(/Destination/i)).toBeInTheDocument();
  expect(screen.getByText(/Ski area/i)).toBeInTheDocument();
  expect(screen.getByText(/Stay base/i)).toBeInTheDocument();
  expect(screen.getByText(/Trip fit/i)).toBeInTheDocument();
  expect(screen.queryByText(/^Confidence$/i)).not.toBeInTheDocument();
  expect(screen.getByText(/Archive-backed|Forecast-assisted|Fallback-heavy/i)).toBeInTheDocument();
  expect(screen.getByText(/Snow reliability|Snow outlook/i)).toBeInTheDocument();
  expect(screen.getByText(/Suggested stays available|Stay-base estimate/i)).toBeInTheDocument();
  expect(screen.getByText(/Approx\. 2h 30m drive from Munich/i)).toBeInTheDocument();
  expect(screen.getByText(/Why Alpine Horizon leads/i)).toBeInTheDocument();
});
```

- [ ] **Step 2: Run focused board test**

Run:

```bash
cd frontend && npm test -- App.test.tsx -t "evidence-first recommendation board"
```

Expected: fail because the board title, role labels, and decision rail do not exist.

- [ ] **Step 3: Create `RecommendationCard.tsx`**

Use this prop contract:

```tsx
interface RecommendationCardProps {
  result: SearchResult;
  rank: number;
  selected: boolean;
  onSelect: () => void;
}
```

Rank role copy:

```ts
function getRankRole(rank: number, result: SearchResult) {
  if (rank === 1) {
    return result.planning_summary ? "Best late-season reliability" : "Best match";
  }
  if (result.travel_effort && result.travel_effort.effort_label !== "very_long") {
    return "Better travel";
  }
  return "Balanced stay fit";
}
```

Card anatomy:

- left rank rail: `#1`, role label
- non-factual abstract mountain panel only when no licensed resort image exists
- leading verdict such as `Best late-April snow reliability`
- resort name and region
- explicit `Destination`, `Ski area`, and `Stay base` labels using `TripEntityStack`
- one-line explanation from `recommendation_narrative`, `planning_summary`, or `conditions_summary`
- `EvidenceQualityBadge`, e.g. `Archive-backed`
- `Snow reliability` for archive-backed/history context, or `Snow outlook` for current/forecast context
- evidence count or provenance badge
- selected stay base and an alternatives count only when the API/data supports alternatives
- accommodation cue:
  - `Suggested stays available` when `top_option.suggested_stays` is present and non-empty
  - `Stay-base estimate` when no provider-backed accommodation options exist
- mid-mountain snow
- travel watchout row when `travel_effort.summary` exists
- `Trip fit` percentage with a horizontal meter as a secondary metric
- primary action text `View details`

Do not render hotel cards on the main result list. Do not render a primary label named `Confidence` on result cards.

- [ ] **Step 4: Create `RecommendationBoard.tsx`**

Use this prop contract:

```tsx
interface RecommendationBoardProps {
  filters: SearchFilters;
  results: SearchResult[];
  selectedResult: SearchResult | null;
  error: string | null;
  isLoading: boolean;
  hasSearched: boolean;
  onSelectResult: (resultId: string) => void;
}
```

Heading copy:

- H2: `Ranked resorts for your trip`
- date subcopy when exact dates exist: `Best matches for Apr 21, 2027 to Apr 27, 2027 based on snow evidence, travel effort and fit.`
- month subcopy: `Best matches for February based on snow evidence, travel effort and fit.`
- fallback: `Results are ranked by trip fit, snow reliability, stay-base match, travel effort, and evidence quality.`

- [ ] **Step 5: Create `DecisionRail.tsx`**

Use this prop contract:

```tsx
interface DecisionRailProps {
  selectedResult: SearchResult | null;
  clarifications: TripClarification[];
  onApplyClarification: (clarificationId: string, option: TripClarificationOption) => void;
}
```

Sections:

- `Why {resort_name} leads`
- `Evidence mode`
- `Tradeoffs`
- `Clarify` only when clarifications exist

The rail should deepen the reasoning already visible on the selected card. It must not be the only place where "why this leads" appears. Keep this rail hidden below the results on narrow screens using responsive Tailwind classes, not by removing it from the DOM.

- [ ] **Step 6: Run board tests and existing route tests**

Run:

```bash
cd frontend && npm test -- App.test.tsx
```

Expected: pass. Existing assertions for result selection and detail route still pass.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/search/RecommendationBoard.tsx frontend/src/search/RecommendationCard.tsx frontend/src/search/DecisionRail.tsx frontend/src/search/SearchPage.tsx frontend/src/App.test.tsx
git commit -m "feat: add evidence-first recommendation board"
```

---

### Task 5: Selected Resort Recommendation Dossier

**Files:**
- Create: `frontend/src/resort/SelectedResortPage.tsx`
- Create: `frontend/src/resort/ResultDossier.tsx`
- Create: `frontend/src/resort/SuggestedStays.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.test.tsx`
- Modify: `frontend/tests/e2e/app.spec.ts`

- [ ] **Step 1: Write failing selected-detail tests**

Add:

```tsx
test("selected result detail renders the recommendation dossier hierarchy", async () => {
  vi.stubGlobal("fetch", mockFetchRoutes({ searchResponses: [travelEffortResponse] }));

  const user = userEvent.setup();
  render(<App />);

  await user.click(screen.getByRole("button", { name: /find resorts/i }));
  await user.click(await screen.findByRole("button", { name: /alpine horizon/i }));

  expect(screen.getByTestId("result-details")).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Alpine Horizon" })).toBeInTheDocument();
  expect(screen.getByText(/why this result leads/i)).toBeInTheDocument();
  expect(screen.getByText(/Destination/i)).toBeInTheDocument();
  expect(screen.getByText(/Ski area/i)).toBeInTheDocument();
  expect(screen.getByText(/Stay base/i)).toBeInTheDocument();
  expect(screen.getByText(/selected trip option/i)).toBeInTheDocument();
  expect(screen.getByText(/stay base options/i)).toBeInTheDocument();
  expect(screen.getByText(/suggested stays/i)).toBeInTheDocument();
  expect(screen.getByText(/provider-backed|stay-base estimate/i)).toBeInTheDocument();
  expect(screen.getByText(/evidence ledger/i)).toBeInTheDocument();
  expect(screen.getByText(/evidence quality/i)).toBeInTheDocument();
  expect(screen.getByText(/trip fit/i)).toBeInTheDocument();
  expect(screen.queryByText(/^Confidence$/i)).not.toBeInTheDocument();
  expect(screen.getByText(/Approx\. 2h 30m drive from Munich/i)).toBeInTheDocument();
});
```

For the exact-date fixture, add:

```tsx
expect(screen.getByText(/april fit/i)).toBeInTheDocument();
expect(screen.getByText(/snow-risk threshold/i)).toBeInTheDocument();
```

- [ ] **Step 2: Run focused selected-detail test**

Run:

```bash
cd frontend && npm test -- App.test.tsx -t "recommendation dossier hierarchy"
```

Expected: fail because the current detail page has the older panel sequence.

- [ ] **Step 3: Create selected-detail route shell**

`SelectedResortPage.tsx` should keep the existing graceful fallback for direct routes without cached search state:

```tsx
if (!result) {
  return (
    <section className="mx-auto w-full max-w-3xl rounded-3xl border border-line bg-white p-8 shadow-soft">
      <div data-testid="detail-route-fallback" className="rounded-3xl border border-dashed border-line bg-ice p-8 text-center">
        <h2 className="font-display text-3xl font-semibold text-ink">Run a search first</h2>
        <p className="mt-4 text-sm leading-6 text-muted">
          This detail page uses your latest search context: travel window, stay base, ranking evidence, and recommendation explanation.
        </p>
        <button type="button" className="mt-6 rounded-full bg-midnight px-5 py-3 text-sm font-semibold text-white" onClick={onBackToSearch}>
          Go to search
        </button>
      </div>
    </section>
  );
}
```

- [ ] **Step 4: Create `ResultDossier.tsx`**

Use this prop contract:

```tsx
interface ResultDossierProps {
  result: SearchResult;
  travelMonth: SearchFilters["travelMonth"];
  tripStartDate: string;
  tripEndDate: string;
  tripBookingStatus: BookingStatus;
  onTripBookingStatusChange: (status: BookingStatus) => void;
  onSaveCurrentTrip: () => Promise<void>;
  onClearCurrentTrip: () => Promise<void>;
  currentTrip: CurrentTrip | null;
  currentTripError: string | null;
  isSavingTrip: boolean;
}
```

Render hierarchy:

1. Dark verdict hero with destination, ski area, stay base, main tradeoff, secondary `Trip fit`, `Book accommodation`, and `Save trip`.
2. `Why this result leads` directly below the hero, before detailed weather metrics.
3. Snow-risk band:
   - exact April dates: `April fit: good above the snow-risk threshold`
   - month April: `April fit: review lower-elevation snow risk`
   - other windows: `Snow window fit`
4. `Selected trip option` strip with stay base, lift access, rental, nightly stay base, rental, travel effort.
5. `Stay base options` comparison. Render the selected stay base as the only option when alternatives are not available; do not invent alternatives.
6. `Suggested stays` under the selected stay base. Render property cards only when `activeOption.suggested_stays` exists and is non-empty; otherwise render `Stay-base estimate, not live hotel inventory`.
7. `Evidence ledger` with evidence quality, current conditions, travel-window evidence, lodging evidence, coverage, freshness, mid-mountain snow, and latest weather record in user language.
8. Highlights and risks side-by-side.
9. `Trip fit` contributors.
10. Current-trip save controls.

The evidence ledger should expose conclusions first. Avoid raw weather-model terminology, provider implementation details, and confidence calculations in the default view.

- [ ] **Step 5: Create `SuggestedStays.tsx`**

Use this prop contract:

```tsx
interface SuggestedStaysProps {
  option: TripOption;
  selectedStayId: string | null;
  onSelectedStayChange: (stayId: string | null) => void;
}
```

Render rules:

- Section title: `Suggested stays`
- Subtitle: `Hotels and apartments sit under the selected stay base.`
- If `option.suggested_stays` is missing or empty, render:
  - `Stay-base estimate, not live hotel inventory`
  - `Snowcast can still hand off to accommodation search for {option.stay_base_name}.`
- If suggested stays exist, render compact property cards with:
  - accommodation name
  - accommodation type
  - provider name
  - price label
  - `AccommodationEvidenceBadge`
  - access label when known
  - fit reason
  - `Select stay` button
  - `Book this stay` link only when `booking_url` is non-null
- Do not render amenities, cancellation policy, exact availability, star ratings, or review scores unless those fields are later added with provider-backed freshness metadata.

- [ ] **Step 6: Preserve booking href behavior**

Keep:

```tsx
const bookingHref = buildAccommodationBookingRedirectUrl(
  result,
  "selected_result_details",
);
```

The top-level `Book accommodation` anchor must keep:

```tsx
target="_blank"
rel="noreferrer"
```

When a suggested stay is selected and has `booking_url`, the property-level CTA should use that URL. When no suggested stay URL exists, keep using the backend accommodation redirect so the source-surface event is still recorded.

- [ ] **Step 7: Run selected-detail and full frontend tests**

Run:

```bash
cd frontend && npm test -- App.test.tsx
cd frontend && npm run test:e2e
```

Expected: pass with updated detail hierarchy.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/resort/SelectedResortPage.tsx frontend/src/resort/ResultDossier.tsx frontend/src/resort/SuggestedStays.tsx frontend/src/App.tsx frontend/src/App.test.tsx frontend/tests/e2e/app.spec.ts
git commit -m "feat: redesign selected resort dossier"
```

---

### Task 6: Current Trip Companion Preview

**Files:**
- Create: `frontend/src/trip/CurrentTripView.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.test.tsx`
- Modify: `frontend/tests/e2e/app.spec.ts`

- [ ] **Step 1: Write failing current-trip layout test**

Replace the current-trip summary assertions with:

```tsx
test("current trip view shows companion preview sections", async () => {
  const currentTrip = currentTripSummaryResponse.trip;
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockImplementationOnce(() => Promise.resolve(jsonResponse({ trip: currentTrip })))
      .mockImplementationOnce(() => Promise.resolve(jsonResponse(currentTripSummaryResponse)))
      .mockImplementationOnce(() => Promise.resolve(jsonResponse(currentTripEventsResponse))),
  );

  const user = userEvent.setup();
  render(<App />);

  await user.click(screen.getByRole("button", { name: /current trip/i }));

  expect(await screen.findByRole("heading", { name: /alpine horizon/i })).toBeInTheDocument();
  expect(screen.getByText(/today's conditions/i)).toBeInTheDocument();
  expect(screen.getByText(/planning update/i)).toBeInTheDocument();
  expect(screen.queryByText(/what changed since last check/i)).not.toBeInTheDocument();
  expect(screen.getByText(/what to watch/i)).toBeInTheDocument();
  expect(screen.getByText(/accommodation context/i)).toBeInTheDocument();
  expect(screen.getByText(/stay-base estimate, not live hotel inventory/i)).toBeInTheDocument();
  expect(screen.getByText(/companion history/i)).toBeInTheDocument();
});
```

- [ ] **Step 2: Run focused current-trip test**

Run:

```bash
cd frontend && npm test -- App.test.tsx -t "companion preview sections"
```

Expected: fail because the old layout does not include `What to watch`.

- [ ] **Step 3: Create `frontend/src/trip/CurrentTripView.tsx`**

Use the existing prop contract from `App.tsx` and render:

- empty state with `Save a resort first`
- dark upcoming-trip hero with resort name, travel window, stay base, booking status, `Mark checked`, and `Edit trip`
- `Today's conditions`
- `Trip details`
- `Planning update`
- `What to watch`
- `Accommodation context`
- `Companion status`
- `Companion history`
- `Quick actions`

`Accommodation context` should remain subordinate to trip identity and conditions:

- If the current trip or latest selected result has a selected suggested stay, show accommodation name, provider, price label, access cue, and provider/freshness badge.
- If no property-level data exists, show `Stay-base estimate, not live hotel inventory` and keep the existing accommodation-search handoff.
- Do not add hotel filters, ratings, amenities, cancellation policy, room inventory, or property photos.
- Do not require current-trip API contract changes in Sprint 34. Use already available selected-result/session state when present; otherwise render the estimate-only state.

`What to watch` should use existing available fields only:

```tsx
const watchItems = [
  "Late-April snow risk below 1,800m",
  "Monitor wind and fresh snow closer to arrival",
];
```

Keep `Mark checked` wired to `onMarkChecked`.

- [ ] **Step 4: Run frontend tests**

Run:

```bash
cd frontend && npm test -- App.test.tsx
cd frontend && npm run test:e2e
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/trip/CurrentTripView.tsx frontend/src/App.tsx frontend/src/App.test.tsx frontend/tests/e2e/app.spec.ts
git commit -m "feat: redesign current trip companion preview"
```

---

### Task 7: Public Resort Guide Visual Refresh

**Files:**
- Modify: `app/public_pages.py`
- Modify: `tests/test_public_pages.py`
- Modify: `README.md`

- [ ] **Step 1: Write failing public-page hierarchy test**

Add to `tests/test_public_pages.py`:

```python
def test_public_resort_page_uses_snowcast_editorial_hierarchy(client):
    response = client.get("/ski-resorts/tignes")

    assert response.status_code == 200
    assert "Current snow outlook" in response.text
    assert "Archive-backed evidence" in response.text
    assert "Turning weather data into resort insight" in response.text
    assert "Planning actual dates?" in response.text
    assert "April-May" in response.text or "April" in response.text
```

- [ ] **Step 2: Run focused public-page test**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_public_pages.py::test_public_resort_page_uses_snowcast_editorial_hierarchy -q
```

Expected: fail because current public page uses the older CSS and content hierarchy.

- [ ] **Step 3: Restyle `app/public_pages.py`**

Update `_render_public_resort_page` CSS tokens to match the frontend:

```python
colors = {
    "midnight": "#021a35",
    "midnight_soft": "#08284f",
    "snow": "#f8fbff",
    "ice": "#edf6fb",
    "line": "#cbd9e8",
    "ink": "#07182f",
    "muted": "#53657d",
    "alpenglow": "#ff5f8f",
    "pine": "#087f68",
    "amber": "#f59e0b",
}
```

Update page hierarchy:

- dark hero with `SNOWCAST`, resort name, location, elevation, season
- `Current snow outlook` card in the hero
- `Conditions calendar (archive-backed)` section
- month cards with `Archive-backed` badges
- `Turning weather data into resort insight`
- bottom planning CTA with search input-style form that links to `/`

Do not add JavaScript. The page must remain backend-rendered HTML.

- [ ] **Step 4: Run public-page tests**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_public_pages.py -q
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add app/public_pages.py tests/test_public_pages.py README.md
git commit -m "feat: align public resort pages with snowcast visual system"
```

---

### Task 8: Documentation, Browser Verification, And Visual Fidelity Gate

**Files:**
- Modify: `PROJECT.md`
- Modify: `docs/engineering-notes.md`

- [ ] **Step 1: Update durable docs**

Add to `PROJECT.md` near the latest sprint notes:

```markdown
**Web UI/UX redesign direction**

The approved Snowcast web direction is a premium planning workspace: dark editorial command entry, compact post-search command bar, evidence-first recommendation board, selected-resort dossier, current-trip companion preview, and matching public resort guide language. The redesign keeps backend search/ranking contracts unchanged and treats resort imagery carefully: abstract alpine imagery is acceptable for brand atmosphere, while factual resort imagery must be licensed/source-safe or omitted.

Execution detail lives in [`docs/superpowers/specs/2026-05-08-web-ui-ux-redesign-design.md`](docs/superpowers/specs/2026-05-08-web-ui-ux-redesign-design.md) and [`docs/superpowers/plans/2026-05-08-web-ui-ux-redesign.md`](docs/superpowers/plans/2026-05-08-web-ui-ux-redesign.md).
```

Add to `docs/engineering-notes.md` under the current web frontend shape section:

```markdown
### Target web UI route boundaries
- The React web app remains the anonymous planning and demo surface, not the authenticated mobile companion.
- Search should open as an editorial command surface, then collapse into a compact command bar after results exist.
- Manual filter editing belongs in a refine drawer; the primary post-search workspace belongs to recommendation comparison and evidence.
- `/resorts/:resortId` remains a search-context recommendation dossier. Public resort content remains backend-rendered under `/ski-resorts/{resort_id}`.
- The shared visual system uses midnight blue for trust, creamy alpenglow pink for brand atmosphere and date/window emphasis, alpine blue for evidence/data, and green/amber/orange for semantic status. Pink must not be the only risk indicator.
```

- [ ] **Step 2: Run automated checks**

Run:

```bash
cd frontend && npm test
cd frontend && npm run build
cd frontend && npm run test:e2e
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_public_pages.py -q
```

Expected: all pass.

- [ ] **Step 3: Start local app for visual QA**

Start the backend/frontend path the repo documents:

```bash
cd frontend && npm run dev -- --host 127.0.0.1
```

If that server is only the frontend, also start the backend in a separate terminal when API-backed flows need live data:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config uvicorn app.main:app --reload
```

- [ ] **Step 4: Browser plugin visual checks**

Use the Browser plugin to inspect:

- `http://127.0.0.1:5173/` initial state at desktop width.
- Search flow with: `Ski in Italy from Warsaw, 21-27 Apr 2027`.
- Refine drawer open.
- Result click to `/resorts/:resortId`.
- `/current-trip` empty or populated state depending on local auth/API.
- `http://127.0.0.1:8000/ski-resorts/tignes` public guide.

- [ ] **Step 5: Capture implementation screenshots and compare with concepts**

Use Browser screenshots for each surface and `view_image` on both concept and implementation screenshots. Inspect at least these points:

- Copy: hero heading, snow-risk signal, button labels, result headings.
- Layout: dark command area, collapsed command bar, chip row, drawer side panel, result board plus decision rail.
- Palette: midnight background, alpenglow accents, alpine blue data marks, semantic risk/status colors.
- Typography: display heading scale, card heading scale, label tracking, button text sizing.
- Container model: no nested card-heavy clutter; result cards and dossier sections match accepted hierarchy.
- Responsive behavior: mobile stacks command, chips, results, rail, drawer without horizontal overflow.

- [ ] **Step 6: Fix visual mismatches found in QA**

For each mismatch, make the smallest CSS/component change that restores fidelity. Re-run:

```bash
cd frontend && npm run build
```

Expected: build passes after fixes.

- [ ] **Step 7: Final commit**

```bash
git add PROJECT.md docs/engineering-notes.md frontend app tests README.md
git commit -m "docs: record snowcast web ui redesign direction"
```

## Self-Review Checklist

- The plan covers search initial state, post-search command bar, refine drawer, recommendation board, decision rail, selected resort detail, current trip, and public resort guide.
- Backend ranking, parser, search contract, and current-trip contracts remain unchanged.
- Resort imagery policy is explicit: no fake factual resort photos.
- Tests cover extracted helpers, search route, result board, selected detail, current trip, and public page hierarchy.
- Verification includes Vitest, build, Playwright, pytest for public pages, Browser inspection, and concept-to-screenshot comparison.
