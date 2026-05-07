# Trip Context And Clarifying Search Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Sprint 31 trip context and bounded clarification cards while keeping the existing search API compatible.

**Architecture:** Parse output gains an optional `trip_context` object and deterministic `clarifications` list. Existing `/api/search` remains unchanged; the web client keeps search filters compatible while storing richer trip context locally and applying clarification patches to local state.

**Tech Stack:** FastAPI, Pydantic v2, pytest, React 18, TypeScript, Vitest/React Testing Library.

**Implementation status:** Complete. Manual product acceptance remains a local handoff step for the reviewer/operator.

---

## File Structure

- Create `app/domain/trip_context.py`
  - Owns trip-context value helpers and deterministic clarification generation.
  - Does not call LLMs or repositories.
- Modify `app/domain/models.py`
  - Adds public parse-response models for `TripContext`, `TripClarification`, and `TripClarificationOption`.
  - Keeps existing `ParsedQueryResponse.filters`, `confidence`, and `unknown_parts` compatible.
- Modify `app/ai/parser.py`
  - Extends LLM schema/prompt and heuristic parser output with trip context.
  - Calls deterministic clarification policy after parser normalization or fallback.
- Modify `tests/test_parser.py`
  - Covers trip-context parsing, heuristic fallback, and clarification generation.
- Modify `tests/test_api.py`
  - Covers `/api/parse-query` compatibility and new fields.
- Modify `frontend/src/types.ts`
  - Adds TypeScript types matching the backend parse-response extension.
- Modify `frontend/src/App.tsx`
  - Persists trip context in search state.
  - Renders clarification cards below "What we understood".
  - Applies clarification patches to trip context and filters.
- Modify `frontend/src/App.test.tsx`
  - Covers clarification cards and patch behavior.

Do not modify `/api/search` behavior in Sprint 31. Do not add routing, geocoding, transport planning, hotel inventory, or live accommodation pricing.

## Data Contract

Backend parse response should remain backward compatible:

```json
{
  "filters": {
    "location": "France",
    "skill_level": "intermediate"
  },
  "confidence": 0.82,
  "unknown_parts": [],
  "trip_context": {
    "budget_mode": null,
    "budget_min": null,
    "budget_max": null,
    "party_size": null,
    "trip_duration_nights": null,
    "origin_text": null
  },
  "clarifications": [
    {
      "id": "budget-mode",
      "question": "Is this budget for nightly lodging or the whole trip?",
      "reason": "Budget amount was detected without clear budget mode.",
      "priority": 10,
      "options": [
        {
          "id": "lodging-nightly",
          "label": "Nightly lodging",
          "description": "Use the amount as the stay-base nightly budget.",
          "context_patch": { "budget_mode": "lodging_nightly" },
          "filter_patch": { "min_price": 150, "max_price": 320 }
        }
      ]
    }
  ],
  "assumptions": []
}
```

Allowed context values:

- `budget_mode`: `lodging_nightly`, `total_trip`, or `null`
- `budget_min` / `budget_max`: numeric, optional
- `party_size`: positive integer, optional
- `trip_duration_nights`: positive integer, optional
- `origin_text`: string, optional

Clarification options patch local UI state only. They do not call a new backend endpoint.

---

### Task 1: Backend Trip Context Models And Clarification Policy

**Files:**
- Create: `app/domain/trip_context.py`
- Modify: `app/domain/models.py`
- Test: `tests/test_parser.py`

- [x] **Step 1: Write failing tests for deterministic clarification policy**

Append these tests to `tests/test_parser.py`:

```python
def test_trip_context_clarifies_ambiguous_budget_mode() -> None:
    payload = HeuristicQueryParser(reference_date=date(2026, 1, 1)).parse(
        "France ski trip for two people with EUR 1500 budget"
    )

    assert payload["trip_context"]["budget_min"] == 1500
    assert payload["trip_context"]["budget_max"] == 1500
    assert payload["trip_context"]["budget_mode"] is None
    clarification = payload["clarifications"][0]
    assert clarification["id"] == "budget-mode"
    assert [option["id"] for option in clarification["options"]] == [
        "lodging-nightly",
        "total-trip",
    ]


def test_trip_context_clarifies_total_budget_duration_and_origin() -> None:
    payload = HeuristicQueryParser(reference_date=date(2026, 1, 1)).parse(
        "France ski trip total budget EUR 1500 for two people not too far away"
    )

    ids = [clarification["id"] for clarification in payload["clarifications"]]
    assert "trip-duration" in ids
    assert "travel-origin" in ids
    assert "party-size" not in ids
    assert payload["trip_context"]["budget_mode"] == "total_trip"
    assert payload["trip_context"]["party_size"] == 2
```

- [x] **Step 2: Run tests to verify they fail**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_parser.py::test_trip_context_clarifies_ambiguous_budget_mode tests/test_parser.py::test_trip_context_clarifies_total_budget_duration_and_origin -q
```

Expected: fail because `trip_context` and `clarifications` are not implemented.

- [x] **Step 3: Add models in `app/domain/models.py`**

Add literal aliases near the existing domain literal aliases:

```python
BudgetMode = Literal["lodging_nightly", "total_trip"]
```

Add models before `ParseQueryRequest`:

```python
class TripContext(BaseModel):
    budget_mode: BudgetMode | None = Field(
        default=None,
        description="Whether detected budget is nightly lodging or total trip budget.",
    )
    budget_min: float | None = Field(
        default=None,
        ge=0,
        description="Detected budget lower bound before search-filter projection.",
    )
    budget_max: float | None = Field(
        default=None,
        ge=0,
        description="Detected budget upper bound before search-filter projection.",
    )
    party_size: int | None = Field(
        default=None,
        ge=1,
        description="Detected number of travelers when present.",
    )
    trip_duration_nights: int | None = Field(
        default=None,
        ge=1,
        description="Detected or derived trip length in nights.",
    )
    origin_text: str | None = Field(
        default=None,
        description="User-provided origin text captured for Sprint 32 travel effort.",
    )


class TripContextPatch(BaseModel):
    budget_mode: BudgetMode | None = None
    party_size: int | None = Field(default=None, ge=1)
    trip_duration_nights: int | None = Field(default=None, ge=1)
    origin_text: str | None = None


class SearchFilterPatch(BaseModel):
    min_price: float | None = Field(default=None, ge=0)
    max_price: float | None = Field(default=None, ge=0)


class TripClarificationOption(BaseModel):
    id: str
    label: str
    description: str
    context_patch: TripContextPatch = Field(default_factory=TripContextPatch)
    filter_patch: SearchFilterPatch | None = None


class TripClarification(BaseModel):
    id: str
    question: str
    reason: str
    priority: int
    options: list[TripClarificationOption]
```

Extend `ParsedQueryResponse`:

```python
class ParsedQueryResponse(BaseModel):
    filters: dict[str, str | int | float] = Field(...)
    confidence: float = Field(...)
    unknown_parts: list[str] = Field(...)
    trip_context: TripContext = Field(default_factory=TripContext)
    clarifications: list[TripClarification] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
```

- [x] **Step 4: Add deterministic policy in `app/domain/trip_context.py`**

Create the module:

```python
from __future__ import annotations

import re
from datetime import date
from typing import Any

from app.domain.models import (
    SearchFilterPatch,
    TripClarification,
    TripClarificationOption,
    TripContext,
    TripContextPatch,
)

_MONEY_PATTERN = re.compile(
    r"(?:eur|€)\s*(?P<amount>\d{2,5}(?:[.,]\d{1,2})?)|"
    r"(?P<amount_before>\d{2,5}(?:[.,]\d{1,2})?)\s*(?:eur|€)",
    re.IGNORECASE,
)
_TOTAL_BUDGET_TERMS = ("total", "overall", "all in", "all-in", "whole trip")
_NIGHTLY_BUDGET_TERMS = ("per night", "nightly", "a night", "/night")
_TRAVEL_EFFORT_TERMS = (
    "not too far",
    "near me",
    "from ",
    "drive",
    "driving",
    "distance",
)
_PARTY_SIZE_WORDS = {
    "solo": 1,
    "alone": 1,
    "two people": 2,
    "2 people": 2,
    "couple": 2,
    "family": 4,
    "group": 4,
}


def build_trip_context_payload(
    *,
    query: str,
    filters: dict[str, str | int | float],
    trip_context: TripContext | None = None,
) -> dict[str, Any]:
    context = trip_context or TripContext()
    normalized = query.lower()
    context = _with_heuristic_context(context, normalized)
    context = _derive_duration_from_filters(context, filters)
    clarifications = build_clarifications(
        query=query,
        filters=filters,
        trip_context=context,
    )
    assumptions = build_assumptions(trip_context=context)
    return {
        "trip_context": context.model_dump(),
        "clarifications": [item.model_dump() for item in clarifications],
        "assumptions": assumptions,
    }


def build_clarifications(
    *,
    query: str,
    filters: dict[str, str | int | float],
    trip_context: TripContext,
) -> list[TripClarification]:
    clarifications: list[TripClarification] = []
    budget_min = trip_context.budget_min
    budget_max = trip_context.budget_max
    if budget_min is None and "min_price" in filters:
        budget_min = float(filters["min_price"])
    if budget_max is None and "max_price" in filters:
        budget_max = float(filters["max_price"])

    if (budget_min is not None or budget_max is not None) and trip_context.budget_mode is None:
        filter_patch = None
        if budget_min is not None or budget_max is not None:
            filter_patch = SearchFilterPatch(
                min_price=budget_min,
                max_price=budget_max or budget_min,
            )
        clarifications.append(
            TripClarification(
                id="budget-mode",
                question="Is this budget for nightly lodging or the whole trip?",
                reason="Budget amount was detected without clear budget mode.",
                priority=10,
                options=[
                    TripClarificationOption(
                        id="lodging-nightly",
                        label="Nightly lodging",
                        description="Use the amount as the stay-base nightly budget.",
                        context_patch=TripContextPatch(
                            budget_mode="lodging_nightly"
                        ),
                        filter_patch=filter_patch,
                    ),
                    TripClarificationOption(
                        id="total-trip",
                        label="Total trip",
                        description="Treat the amount as the approximate full trip budget.",
                        context_patch=TripContextPatch(budget_mode="total_trip"),
                    ),
                ],
            )
        )

    if (
        trip_context.budget_mode == "total_trip"
        and trip_context.trip_duration_nights is None
        and not ("trip_start_date" in filters and "trip_end_date" in filters)
    ):
        clarifications.append(
            TripClarification(
                id="trip-duration",
                question="How long is the trip?",
                reason="Total-trip budget needs duration before it can be estimated.",
                priority=20,
                options=[
                    TripClarificationOption(
                        id="short-break",
                        label="3-4 nights",
                        description="Use a short ski break assumption.",
                        context_patch=TripContextPatch(trip_duration_nights=4),
                    ),
                    TripClarificationOption(
                        id="one-week",
                        label="1 week",
                        description="Use a seven-night ski week assumption.",
                        context_patch=TripContextPatch(trip_duration_nights=7),
                    ),
                ],
            )
        )

    if trip_context.budget_mode == "total_trip" and trip_context.party_size is None:
        clarifications.append(
            TripClarification(
                id="party-size",
                question="How many people is the budget for?",
                reason="Total-trip budget depends on party size.",
                priority=30,
                options=[
                    TripClarificationOption(
                        id="solo",
                        label="Solo",
                        description="Estimate the budget for one traveler.",
                        context_patch=TripContextPatch(party_size=1),
                    ),
                    TripClarificationOption(
                        id="two-people",
                        label="2 people",
                        description="Estimate the budget for two travelers.",
                        context_patch=TripContextPatch(party_size=2),
                    ),
                    TripClarificationOption(
                        id="family-group",
                        label="Family/group",
                        description="Use a four-person group assumption.",
                        context_patch=TripContextPatch(party_size=4),
                    ),
                ],
            )
        )

    if _mentions_travel_effort(query) and not trip_context.origin_text:
        clarifications.append(
            TripClarification(
                id="travel-origin",
                question="Where will you start from?",
                reason="Origin will help estimate drive effort in a later sprint.",
                priority=40,
                options=[
                    TripClarificationOption(
                        id="add-origin-later",
                        label="I'll add it later",
                        description="Search now and keep travel effort out for the moment.",
                    ),
                ],
            )
        )

    return sorted(clarifications, key=lambda item: item.priority)[:3]


def build_assumptions(*, trip_context: TripContext) -> list[str]:
    if trip_context.budget_mode == "total_trip":
        return [
            "Total-trip budget is captured for context; travel cost is not included until travel effort is implemented."
        ]
    return []


def _with_heuristic_context(context: TripContext, query: str) -> TripContext:
    data = context.model_dump()
    amount = _extract_budget_amount(query)
    if amount is not None and data.get("budget_min") is None:
        data["budget_min"] = amount
        data["budget_max"] = amount
    if data.get("budget_mode") is None:
        if any(term in query for term in _TOTAL_BUDGET_TERMS):
            data["budget_mode"] = "total_trip"
        elif any(term in query for term in _NIGHTLY_BUDGET_TERMS):
            data["budget_mode"] = "lodging_nightly"
    if data.get("party_size") is None:
        for phrase, value in _PARTY_SIZE_WORDS.items():
            if phrase in query:
                data["party_size"] = value
                break
    return TripContext.model_validate(data)


def _derive_duration_from_filters(
    context: TripContext,
    filters: dict[str, str | int | float],
) -> TripContext:
    if context.trip_duration_nights is not None:
        return context
    start = filters.get("trip_start_date")
    end = filters.get("trip_end_date")
    if not isinstance(start, str) or not isinstance(end, str):
        return context
    start_date = date.fromisoformat(start)
    end_date = date.fromisoformat(end)
    nights = max((end_date - start_date).days, 1)
    return TripContext.model_validate(
        {**context.model_dump(), "trip_duration_nights": nights}
    )


def _extract_budget_amount(query: str) -> float | None:
    match = _MONEY_PATTERN.search(query)
    if match is None:
        return None
    text = match.group("amount") or match.group("amount_before")
    if text is None:
        return None
    return float(text.replace(",", "."))


def _mentions_travel_effort(query: str) -> bool:
    normalized = query.lower()
    return any(term in normalized for term in _TRAVEL_EFFORT_TERMS)
```

- [x] **Step 5: Wire the heuristic parser to include context**

In `HeuristicQueryParser.parse_with_debug`, after the existing `response = ParsedQueryResponse(...)` construction, replace it with:

```python
from app.domain.trip_context import build_trip_context_payload

context_payload = build_trip_context_payload(query=query, filters=filters)
response = ParsedQueryResponse(
    filters=filters,
    confidence=confidence,
    unknown_parts=unknown_parts,
    **context_payload,
)
```

Keep import ordering clean with Ruff.

- [x] **Step 6: Run tests and make Task 1 green**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_parser.py::test_trip_context_clarifies_ambiguous_budget_mode tests/test_parser.py::test_trip_context_clarifies_total_budget_duration_and_origin -q
```

Expected: both tests pass.

---

### Task 2: LLM Parser And API Parse Response Integration

**Files:**
- Modify: `app/ai/parser.py`
- Modify: `tests/test_parser.py`
- Modify: `tests/test_api.py`

- [x] **Step 1: Write failing parser/API tests**

Add to `tests/test_parser.py`:

```python
def test_llm_parser_returns_trip_context_and_clarifications() -> None:
    parser = LLMBackedQueryParser(
        client=StubLLMClient(
            """
            {
              "filters": {
                "location": "france",
                "skill_level": "intermediate"
              },
              "trip_context": {
                "budget_mode": "total_trip",
                "budget_min": 1500,
                "budget_max": 1500,
                "party_size": null,
                "trip_duration_nights": null,
                "origin_text": null
              },
              "confidence": 0.86,
              "unknown_parts": []
            }
            """
        ),
        cache_repository=LLMCacheRepository(),
    )

    payload = parser.parse("France ski trip total budget EUR 1500")

    assert payload["trip_context"]["budget_mode"] == "total_trip"
    clarification_ids = [item["id"] for item in payload["clarifications"]]
    assert "trip-duration" in clarification_ids
    assert "party-size" in clarification_ids
```

Add to `tests/test_api.py`:

```python
def test_parse_query_returns_trip_context_and_clarifications() -> None:
    app.dependency_overrides[get_query_parser] = lambda: HeuristicQueryParser(
        reference_date=date(2026, 1, 1)
    )
    try:
        response = client.post(
            "/api/parse-query",
            json={"query": "France ski trip total budget EUR 1500 for two people"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["trip_context"]["budget_mode"] == "total_trip"
    assert payload["trip_context"]["party_size"] == 2
    assert "clarifications" in payload
    assert "assumptions" in payload
```

- [x] **Step 2: Run tests to verify they fail**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_parser.py::test_llm_parser_returns_trip_context_and_clarifications tests/test_api.py::test_parse_query_returns_trip_context_and_clarifications -q
```

Expected: fail until LLM schema normalization includes `trip_context`.

- [x] **Step 3: Extend parser schema and payload model**

In `app/ai/parser.py`:

- Bump `PARSER_PROMPT_VERSION` to `"v6"`.
- Bump `PARSER_SCHEMA_VERSION` to `"v5"`.
- Import `TripContext` and `build_trip_context_payload`.
- Add `trip_context` to `PARSER_RESPONSE_JSON_SCHEMA` with nullable fields matching the contract.
- Add `trip_context: TripContext = Field(default_factory=TripContext)` to `LLMParsedQueryPayload`.

- [x] **Step 4: Update parser prompt**

Extend the system prompt to say:

```python
"Return optional trip_context for budget_mode, budget_min, budget_max, "
"party_size, trip_duration_nights, and origin_text. Only put min_price and "
"max_price in filters when the query clearly describes nightly lodging budget. "
"For total, overall, all-in, or whole-trip budget, put the amount in "
"trip_context with budget_mode=total_trip. For ambiguous budget amounts, put "
"the amount in trip_context and leave budget_mode null so the app can ask a "
"clarification. Capture origin_text only when the user states a start point; "
"do not infer device location."
```

- [x] **Step 5: Normalize LLM trip context and deterministic clarifications**

At the end of `_normalize_payload`, call:

```python
context_payload = build_trip_context_payload(
    query=query,
    filters=filters,
    trip_context=normalized.trip_context,
)
response = ParsedQueryResponse(
    filters=filters,
    confidence=normalized.confidence,
    unknown_parts=normalized.unknown_parts,
    **context_payload,
)
return response.model_dump()
```

Keep date normalization exactly as it works now.

- [x] **Step 6: Run focused backend tests**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_parser.py tests/test_api.py::test_parse_query_returns_structured_filters_and_confidence tests/test_api.py::test_parse_query_returns_exact_date_filters tests/test_api.py::test_parse_query_returns_trip_context_and_clarifications -q
```

Expected: pass.

---

### Task 3: Frontend Clarification Cards And Context State

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.test.tsx`

- [x] **Step 1: Write failing frontend tests**

Add to `frontend/src/App.test.tsx`:

```tsx
const clarificationParseResponse = {
  filters: {
    location: "France",
    skill_level: "intermediate",
  },
  confidence: 0.88,
  unknown_parts: [],
  trip_context: {
    budget_mode: null,
    budget_min: 1500,
    budget_max: 1500,
    party_size: null,
    trip_duration_nights: null,
    origin_text: null,
  },
  clarifications: [
    {
      id: "budget-mode",
      question: "Is this budget for nightly lodging or the whole trip?",
      reason: "Budget amount was detected without clear budget mode.",
      priority: 10,
      options: [
        {
          id: "lodging-nightly",
          label: "Nightly lodging",
          description: "Use the amount as the stay-base nightly budget.",
          context_patch: { budget_mode: "lodging_nightly" },
          filter_patch: { min_price: 1500, max_price: 1500 },
        },
        {
          id: "total-trip",
          label: "Total trip",
          description: "Treat the amount as the approximate full trip budget.",
          context_patch: { budget_mode: "total_trip" },
          filter_patch: null,
        },
      ],
    },
  ],
  assumptions: [],
};

test("shows clarification cards and applies nightly budget choice", async () => {
  const fetchMock = mockFetchRoutes({
    parseResponse: clarificationParseResponse,
    searchResponses: [emptyResponse],
  });
  vi.stubGlobal("fetch", fetchMock);

  const user = userEvent.setup();
  render(<App />);

  await user.clear(screen.getByLabelText(/what are you looking for/i));
  await user.type(
    screen.getByLabelText(/what are you looking for/i),
    "France ski trip with EUR 1500 budget",
  );
  await user.click(screen.getByRole("button", { name: /find resorts/i }));

  expect(
    await screen.findByText(/is this budget for nightly lodging or the whole trip/i),
  ).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: /nightly lodging/i }));

  expect(screen.getByLabelText(/min price/i)).toHaveValue("1500");
  expect(screen.getByLabelText(/max price/i)).toHaveValue("1500");
  expect(screen.getByText(/Budget: nightly lodging/i)).toBeInTheDocument();
});
```

- [x] **Step 2: Run frontend test to verify it fails**

Run:

```bash
cd frontend && npm test -- App.test.tsx -t "shows clarification cards and applies nightly budget choice"
```

Expected: fail because frontend types/state/UI do not support clarifications.

- [x] **Step 3: Add frontend types**

In `frontend/src/types.ts`, add:

```ts
export type BudgetMode = "lodging_nightly" | "total_trip";

export interface TripContext {
  budget_mode: BudgetMode | null;
  budget_min: number | null;
  budget_max: number | null;
  party_size: number | null;
  trip_duration_nights: number | null;
  origin_text: string | null;
}

export interface TripContextPatch {
  budget_mode?: BudgetMode | null;
  party_size?: number | null;
  trip_duration_nights?: number | null;
  origin_text?: string | null;
}

export interface SearchFilterPatch {
  min_price?: number | null;
  max_price?: number | null;
}

export interface TripClarificationOption {
  id: string;
  label: string;
  description: string;
  context_patch: TripContextPatch;
  filter_patch: SearchFilterPatch | null;
}

export interface TripClarification {
  id: string;
  question: string;
  reason: string;
  priority: number;
  options: TripClarificationOption[];
}
```

Extend `ParsedQueryResponse` with:

```ts
  trip_context: TripContext;
  clarifications: TripClarification[];
  assumptions: string[];
```

- [x] **Step 4: Add context state in `App.tsx`**

Import `TripContext`, `TripClarification`, and `TripClarificationOption`.

Add:

```ts
const emptyTripContext: TripContext = {
  budget_mode: null,
  budget_min: null,
  budget_max: null,
  party_size: null,
  trip_duration_nights: null,
  origin_text: null,
};
```

Extend `StoredSearchState` and `emptyStoredSearchState`:

```ts
  tripContext: TripContext;
  clarifications: TripClarification[];
  assumptions: string[];
```

Add state:

```ts
const [tripContext, setTripContext] = useState<TripContext>(
  initialSearchState.tripContext,
);
const [clarifications, setClarifications] = useState<TripClarification[]>(
  initialSearchState.clarifications,
);
const [assumptions, setAssumptions] = useState<string[]>(
  initialSearchState.assumptions,
);
```

Add these fields to the session-storage effect dependency list and saved payload.

- [x] **Step 5: Merge parse response context**

Inside the parse branch of `handleSubmit`, after `setParsedQuery(parsed)`:

```ts
setTripContext(parsed.trip_context ?? emptyTripContext);
setClarifications(parsed.clarifications ?? []);
setAssumptions(parsed.assumptions ?? []);
```

Add a helper:

```ts
function applyClarificationOption(option: TripClarificationOption) {
  setTripContext((current) => ({
    ...current,
    ...option.context_patch,
  }));
  setClarifications((current) =>
    current.filter((clarification) =>
      !clarification.options.some((candidate) => candidate.id === option.id),
    ),
  );
  if (option.filter_patch) {
    setFilters((current) => ({
      ...current,
      minPrice:
        option.filter_patch?.min_price !== undefined &&
        option.filter_patch?.min_price !== null
          ? String(option.filter_patch.min_price)
          : current.minPrice,
      maxPrice:
        option.filter_patch?.max_price !== undefined &&
        option.filter_patch?.max_price !== null
          ? String(option.filter_patch.max_price)
          : current.maxPrice,
    }));
  }
}
```

- [x] **Step 6: Render clarification cards**

Below the parsed "What we understood" block, render:

```tsx
{clarifications.length > 0 ? (
  <div className="mt-4 grid gap-3">
    {clarifications.map((clarification) => (
      <div
        key={clarification.id}
        className="rounded-2xl border border-amber-200 bg-amber-50/80 p-4"
      >
        <p className="text-sm font-semibold text-ink">{clarification.question}</p>
        <p className="mt-1 text-sm text-slate-600">{clarification.reason}</p>
        <div className="mt-3 flex flex-wrap gap-2">
          {clarification.options.map((option) => (
            <button
              key={option.id}
              type="button"
              className="rounded-full border border-amber-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 transition hover:border-alpine hover:text-alpine"
              onClick={() => applyClarificationOption(option)}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>
    ))}
  </div>
) : null}
```

Also add trip-context chips below applied filters:

```tsx
{tripContext.budget_mode ? (
  <span className="rounded-full border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-600">
    Budget: {tripContext.budget_mode === "total_trip" ? "total trip" : "nightly lodging"}
  </span>
) : null}
```

If `assumptions.length > 0`, render a compact caveat under the clarification cards.

- [x] **Step 7: Run focused frontend tests**

Run:

```bash
cd frontend && npm test -- App.test.tsx -t "shows clarification cards and applies nightly budget choice"
```

Expected: pass.

Then run:

```bash
cd frontend && npm test -- App.test.tsx
```

Expected: pass.

---

### Task 4: Integration Verification And Documentation Touch-Up

**Files:**
- Modify: `README.md` only if a user-visible behavior note is missing.
- Modify: `docs/engineering-notes.md` only if the trip-context/clarification model is not already captured.

- [x] **Step 1: Run backend focused verification**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config pytest tests/test_parser.py tests/test_api.py -q
```

Expected: pass.

- [x] **Step 2: Run frontend focused verification**

Run:

```bash
cd frontend && npm test -- App.test.tsx
```

Expected: pass.

- [x] **Step 3: Run lint**

Run:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config ruff check app tests
```

Expected: pass.

Run:

```bash
cd frontend && npm run build
```

Expected: pass.

- [x] **Step 4: Update documentation if needed**

If not already covered, add one concise note:

- `README.md`: web search now may show clarification cards after parse.
- `docs/engineering-notes.md`: trip-context clarification is deterministic policy on parsed context, not open-ended chat.

- [ ] **Step 5: Manual acceptance path**

Start the backend and frontend in separate terminals:

```bash
UV_CACHE_DIR=.uv-cache uv run --no-config uvicorn app.main:app --reload
cd frontend && npm run dev
```

Open the web app and search:

```text
France ski trip total budget EUR 1500 for two people not too far away
```

Expected:

- "What we understood" appears.
- Clarification cards ask for duration and origin.
- Search can still run without answering every clarification.
- No routing, airport, train, or itinerary UI appears.
