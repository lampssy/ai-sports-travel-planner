# Coordinated Multi-Operator Ski Areas Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow a schema-version-3 curation report to justify one complete skier-facing `SkiArea` through an explicit, source-backed coordinated multi-operator boundary without weakening the normal independent-owner rule.

**Architecture:** Extend the report-only Pydantic contract with separate operations and weather scope types, coordinated evidence signals, and component references. Validate each coordinated parent locally, then validate component closure across the complete report; runtime catalog entities, search behavior, and weather activation remain unchanged. Render the extra provenance only for coordinated reports so historical Markdown remains stable.

**Tech Stack:** Python 3.12, Pydantic v2, pytest, Ruff, deterministic Markdown rendering, local Codex skills

**Spec:** `docs/superpowers/specs/2026-08-26-coordinated-multi-operator-ski-areas-design.md`

## Global Constraints

- Keep runtime `SkiArea`, API, search, ranking, and recommendation behavior unchanged.
- Keep `report_schema_version=3`; existing version-3 JSON reports must remain parseable without adding fields manually.
- Keep legacy version-3 Markdown byte-for-byte unchanged when no assessment uses coordinated metadata.
- Permit `coordinated` only for `operational_scope`; `weather_scope=coordinated` must fail Pydantic validation.
- Require complete terrain scope, material separation, all three coordinated signals, a full-component pass, and complete component reconciliation.
- A shared pass, regional brand, operator directory, common website, or map proximity cannot establish the boundary alone.
- Keep weather sampling independently gated by ADR 0021; this change must not activate, backfill, migrate, or re-key weather data.
- Do not modify PR #36 or Livigno catalog data in this policy implementation branch.
- Use deterministic validation for report structure and evidence closure; do not add an LLM call, prompt, cache, dependency, or request-path work.
- Update installed curation and review skills only after the repository contract is merged to `main`; do not create a skill/repository contract mismatch while the feature is still unmerged.

---

### Task 1: Extend The Schema-V3 Report Contract

**Files:**
- Modify: `app/data/catalog_curation.py:75-220`
- Modify: `app/data/catalog_curation.py:840-880`
- Test: `tests/test_catalog_curation.py:255-285`
- Test: `tests/test_catalog_curation.py:899-1125`

**Interfaces:**
- Consumes: existing `CatalogScopeSignalType`, `CatalogSkiAreaBoundaryAssessment`, and `_validate_string_list()`.
- Produces: `CatalogSkiAreaOperationalScope`, `CatalogSkiAreaWeatherScope`, the three coordinated signal values, and two backward-compatible list fields on `CatalogSkiAreaBoundaryAssessment`.

- [ ] **Step 1: Extend the test payload helper and add failing model-contract tests**

Update `_ski_area_boundary_payload()` so later tests can state coordinated metadata explicitly:

```python
def _ski_area_boundary_payload(
    *,
    parent_ski_area_id: str | None = None,
    terrain_scope: str = "complete",
    connectivity_to_parent: str = "not_applicable",
    operational_scope: str = "unknown",
    weather_scope: str = "unknown",
    pass_scope: str = "none",
    provider_consensus: str = "separate",
    separation_value: str = "material",
    component_candidate_ids: list[str] | None = None,
    coordination_evidence_refs: list[str] | None = None,
    evidence_refs: list[str] | None = None,
) -> dict:
    return {
        "parent_ski_area_id": parent_ski_area_id,
        "terrain_scope": terrain_scope,
        "connectivity_to_parent": connectivity_to_parent,
        "operational_scope": operational_scope,
        "weather_scope": weather_scope,
        "pass_scope": pass_scope,
        "provider_consensus": provider_consensus,
        "separation_value": separation_value,
        "component_candidate_ids": component_candidate_ids or [],
        "coordination_evidence_refs": coordination_evidence_refs or [],
        "evidence_refs": evidence_refs or ["example-scope"],
    }
```

Add these tests next to the existing ski-area boundary contract tests:

```python
def test_schema_three_rejects_coordinated_weather_scope() -> None:
    payload = _scope_report_payload(
        candidate_kind="ski_area",
        disposition="represented",
        target_type="ski_area",
        target_id="example-area",
    )
    payload["report_schema_version"] = 3
    payload["entity_scope_assessments"][0]["ski_area_boundary"] = (
        _ski_area_boundary_payload(weather_scope="coordinated")
    )

    with pytest.raises(ValidationError, match="weather_scope"):
        CatalogCurationReport.model_validate(payload)


def test_schema_three_defaults_coordination_metadata_for_legacy_boundary() -> None:
    payload = _scope_report_payload(
        candidate_kind="ski_area",
        disposition="not_separate",
        signals=["official_map_sector"],
        target_type="ski_area",
        target_id="parent-area",
    )
    payload["report_schema_version"] = 3
    payload["entity_scope_assessments"][0]["ski_area_boundary"] = (
        _ski_area_boundary_payload(
            parent_ski_area_id="parent-area",
            terrain_scope="sector",
            connectivity_to_parent="connected",
            operational_scope="parent_owned",
            weather_scope="parent_owned",
            pass_scope="shared_only",
            provider_consensus="aggregated",
            separation_value="redundant",
        )
    )

    report = CatalogCurationReport.model_validate(payload)
    boundary = report.entity_scope_assessments[0].ski_area_boundary

    assert boundary is not None
    assert boundary.component_candidate_ids == []
    assert boundary.coordination_evidence_refs == []


def test_schema_three_rejects_coordination_metadata_on_independent_boundary() -> None:
    payload = _scope_report_payload(
        candidate_kind="ski_area",
        disposition="represented",
        target_type="ski_area",
        target_id="example-area",
    )
    payload["report_schema_version"] = 3
    payload["entity_scope_assessments"][0]["ski_area_boundary"] = (
        _ski_area_boundary_payload(
            operational_scope="independent",
            component_candidate_ids=["operator-a", "operator-b"],
            coordination_evidence_refs=["example-scope"],
        )
    )

    with pytest.raises(
        ValidationError,
        match="coordination metadata requires operational_scope=coordinated",
    ):
        CatalogCurationReport.model_validate(payload)


def test_schema_three_rejects_unowned_coordination_evidence() -> None:
    payload = _scope_report_payload(
        candidate_kind="ski_area",
        disposition="represented",
        target_type="ski_area",
        target_id="example-area",
    )
    payload["report_schema_version"] = 3
    payload["entity_scope_assessments"][0]["ski_area_boundary"] = (
        _ski_area_boundary_payload(
            operational_scope="coordinated",
            component_candidate_ids=["operator-a", "operator-b"],
            coordination_evidence_refs=["missing-coordination-evidence"],
        )
    )

    with pytest.raises(
        ValidationError,
        match="coordination_evidence_refs must be included in evidence_refs",
    ):
        CatalogCurationReport.model_validate(payload)
```

- [ ] **Step 2: Run the model-contract tests and confirm they fail for the intended reasons**

Run:

```bash
uv run --no-config pytest -q \
  tests/test_catalog_curation.py::test_schema_three_rejects_coordinated_weather_scope \
  tests/test_catalog_curation.py::test_schema_three_defaults_coordination_metadata_for_legacy_boundary \
  tests/test_catalog_curation.py::test_schema_three_rejects_coordination_metadata_on_independent_boundary \
  tests/test_catalog_curation.py::test_schema_three_rejects_unowned_coordination_evidence
```

Expected: failures because `coordinated` and the two metadata fields are not yet part of the contract.

- [ ] **Step 3: Add separate scope aliases, coordinated signals, and metadata fields**

Replace the shared owner alias with operations- and weather-specific aliases:

```python
CatalogSkiAreaOperationalScope = Literal[
    "independent",
    "parent_owned",
    "coordinated",
    "mixed",
    "unknown",
]
CatalogSkiAreaWeatherScope = Literal[
    "independent",
    "parent_owned",
    "mixed",
    "unknown",
]
```

Add these values to `CatalogScopeSignalType`:

```python
"official_complete_lift_inventory",
"coordinated_status_or_schedule",
"common_full_coverage_pass",
```

Update the boundary model:

```python
class CatalogSkiAreaBoundaryAssessment(CatalogCurationContractModel):
    parent_ski_area_id: str | None = None
    terrain_scope: CatalogSkiAreaTerrainScope
    connectivity_to_parent: CatalogSkiAreaParentConnectivity
    operational_scope: CatalogSkiAreaOperationalScope
    weather_scope: CatalogSkiAreaWeatherScope
    pass_scope: CatalogSkiAreaPassScope
    provider_consensus: CatalogSkiAreaProviderConsensus
    separation_value: CatalogSkiAreaSeparationValue
    component_candidate_ids: list[str] = Field(default_factory=list)
    coordination_evidence_refs: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(min_length=1)

    @field_validator(
        "component_candidate_ids",
        "coordination_evidence_refs",
        "evidence_refs",
    )
    @classmethod
    def validate_reference_lists(cls, values: list[str], info: ValidationInfo) -> list[str]:
        return _validate_string_list(values, f"ski-area boundary {info.field_name}")

    @model_validator(mode="after")
    def validate_coordination_metadata(self) -> CatalogSkiAreaBoundaryAssessment:
        has_coordination_metadata = bool(
            self.component_candidate_ids or self.coordination_evidence_refs
        )
        if self.operational_scope != "coordinated" and has_coordination_metadata:
            raise ValueError(
                "coordination metadata requires operational_scope=coordinated"
            )
        if not set(self.coordination_evidence_refs).issubset(self.evidence_refs):
            raise ValueError(
                "coordination_evidence_refs must be included in evidence_refs"
            )
        return self
```

Import `ValidationInfo` from Pydantic if the module does not already import it. Preserve the existing parent/connectivity checks in the same model validator or in a separate `mode="after"` validator.

- [ ] **Step 4: Run the model-contract tests and the complete curation unit file**

Run:

```bash
uv run --no-config pytest -q tests/test_catalog_curation.py
```

Expected: all tests pass, including the new type and backward-compatibility cases.

- [ ] **Step 5: Commit the report contract**

```bash
git add app/data/catalog_curation.py tests/test_catalog_curation.py
git commit -m "feat: add coordinated ski area report contract"
```

---

### Task 2: Validate Coordinated Parent Eligibility

**Files:**
- Modify: `app/data/catalog_curation.py:203-225`
- Modify: `app/data/catalog_curation.py:1423-1510`
- Test: `tests/test_catalog_curation.py:899-1125`

**Interfaces:**
- Consumes: Task 1's `operational_scope="coordinated"`, component IDs, coordination evidence refs, and signal literals.
- Produces: `SKI_AREA_COORDINATED_OPERATION_SIGNALS` and deterministic parent-level validation through `_validate_ski_area_boundary_assessment()`.

- [ ] **Step 1: Add a reusable valid coordinated-report test builder**

Add this helper after `_complete_new_ski_area_report_target()`:

```python
def _coordinated_ski_area_report_payload() -> dict:
    parent_id = "coordinated-area"
    component_ids = ["operator-a-sector", "operator-b-sector"]
    payload = _scope_report_payload(
        candidate_kind="ski_area",
        disposition="add_entity",
        signals=[
            "official_complete_lift_inventory",
            "coordinated_status_or_schedule",
            "common_full_coverage_pass",
        ],
        target_type="ski_area",
        target_id=parent_id,
    )
    payload["report_schema_version"] = 3
    payload["entity_scope_assessments"][0]["ski_area_boundary"] = (
        _ski_area_boundary_payload(
            operational_scope="coordinated",
            weather_scope="unknown",
            pass_scope="shared_only",
            provider_consensus="aggregated",
            component_candidate_ids=component_ids,
            coordination_evidence_refs=["example-scope"],
        )
    )
    _complete_new_ski_area_report_target(payload, parent_id)
    for component_id in component_ids:
        payload["entity_scope_assessments"].append(
            {
                "candidate_id": component_id,
                "candidate_name": component_id.replace("-", " ").title(),
                "candidate_kind": "ski_area",
                "disposition": "not_separate",
                "signals": ["official_map_sector", "ski_connected_terrain"],
                "evidence_refs": ["example-scope"],
                "target_refs": [
                    {"target_type": "ski_area", "target_id": parent_id}
                ],
                "rationale": "The complete coordinated sources assign this sector.",
                "ski_area_boundary": _ski_area_boundary_payload(
                    parent_ski_area_id=parent_id,
                    terrain_scope="sector",
                    connectivity_to_parent="connected",
                    operational_scope="coordinated",
                    weather_scope="parent_owned",
                    pass_scope="shared_only",
                    provider_consensus="aggregated",
                    separation_value="redundant",
                ),
            }
        )
    return payload
```

- [ ] **Step 2: Add failing parent-eligibility tests**

```python
def test_schema_three_accepts_complete_coordinated_parent() -> None:
    report = CatalogCurationReport.model_validate(
        _coordinated_ski_area_report_payload()
    )

    validate_catalog_curation_report(report)


@pytest.mark.parametrize(
    "missing_signal",
    [
        "official_complete_lift_inventory",
        "coordinated_status_or_schedule",
        "common_full_coverage_pass",
    ],
)
def test_schema_three_coordinated_parent_requires_every_signal(
    missing_signal: str,
) -> None:
    payload = _coordinated_ski_area_report_payload()
    parent = payload["entity_scope_assessments"][0]
    parent["signals"].remove(missing_signal)
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(
        CatalogValidationError,
        match=f"coordinated ski area requires signal {missing_signal}",
    ):
        validate_catalog_curation_report(report)


@pytest.mark.parametrize("pass_scope", ["limited", "none", "unknown"])
def test_schema_three_coordinated_parent_requires_full_component_pass(
    pass_scope: str,
) -> None:
    payload = _coordinated_ski_area_report_payload()
    payload["entity_scope_assessments"][0]["ski_area_boundary"]["pass_scope"] = (
        pass_scope
    )
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(
        CatalogValidationError,
        match="coordinated ski area requires pass_scope=full_local or shared_only",
    ):
        validate_catalog_curation_report(report)


def test_schema_three_coordinated_parent_requires_two_components() -> None:
    payload = _coordinated_ski_area_report_payload()
    parent_boundary = payload["entity_scope_assessments"][0]["ski_area_boundary"]
    parent_boundary["component_candidate_ids"] = ["operator-a-sector"]
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(
        CatalogValidationError,
        match="coordinated ski area requires at least two component candidates",
    ):
        validate_catalog_curation_report(report)
```

- [ ] **Step 3: Run the parent-eligibility tests and confirm the positive case currently fails**

Run:

```bash
uv run --no-config pytest -q \
  tests/test_catalog_curation.py::test_schema_three_accepts_complete_coordinated_parent \
  tests/test_catalog_curation.py::test_schema_three_coordinated_parent_requires_every_signal \
  tests/test_catalog_curation.py::test_schema_three_coordinated_parent_requires_full_component_pass \
  tests/test_catalog_curation.py::test_schema_three_coordinated_parent_requires_two_components
```

Expected: the positive case fails under the old independent-owner rule; the negative cases do not yet produce the coordinated-specific errors.

- [ ] **Step 4: Implement the coordinated parent path**

Add the coordinated signal set and allow the complete inventory to establish terrain identity:

```python
SKI_AREA_TERRAIN_IDENTITY_SIGNALS = frozenset(
    {
        "official_independent_identity",
        "child_scoped_terrain_metrics",
        "official_complete_lift_inventory",
    }
)
SKI_AREA_COORDINATED_OPERATION_SIGNALS = frozenset(
    {
        "official_complete_lift_inventory",
        "coordinated_status_or_schedule",
        "common_full_coverage_pass",
    }
)
```

In `_validate_ski_area_boundary_assessment()`, retain the existing complete-terrain, terrain-identity, material-separation, and resolved-connectivity checks. Before calculating independent owner categories, branch on coordinated operations:

```python
    if boundary.operational_scope == "coordinated":
        for required_signal in sorted(SKI_AREA_COORDINATED_OPERATION_SIGNALS):
            if required_signal not in signals:
                issues.append(
                    f"{candidate_id}: coordinated ski area requires signal "
                    f"{required_signal}"
                )
        if boundary.pass_scope not in {"full_local", "shared_only"}:
            issues.append(
                f"{candidate_id}: coordinated ski area requires "
                "pass_scope=full_local or shared_only"
            )
        if len(boundary.component_candidate_ids) < 2:
            issues.append(
                f"{candidate_id}: coordinated ski area requires at least two "
                "component candidates"
            )
        if not boundary.coordination_evidence_refs:
            issues.append(
                f"{candidate_id}: coordinated ski area requires coordination "
                "evidence refs"
            )
        return
```

Do not count coordinated signals as independent owner categories. The existing independent path must remain unchanged for `operational_scope != "coordinated"`.

- [ ] **Step 5: Run focused and regression tests**

Run:

```bash
uv run --no-config pytest -q tests/test_catalog_curation.py
```

Expected: all curation contract tests pass; existing connected independent-area tests still exercise the original two-owner-category rule.

- [ ] **Step 6: Commit coordinated parent validation**

```bash
git add app/data/catalog_curation.py tests/test_catalog_curation.py
git commit -m "feat: validate coordinated ski area ownership"
```

---

### Task 3: Enforce Report-Wide Component Closure

**Files:**
- Modify: `app/data/catalog_curation.py:1423-1640`
- Test: `tests/test_catalog_curation.py:899-1205`

**Interfaces:**
- Consumes: Task 2's valid coordinated parent and `_coordinated_ski_area_report_payload()`.
- Produces: `_validate_coordinated_ski_area_components(assessments, issues) -> None`, called once for every schema-version-3 report after per-assessment validation.

- [ ] **Step 1: Add failing graph-closure tests**

```python
def test_schema_three_coordinated_parent_rejects_missing_component_assessment() -> None:
    payload = _coordinated_ski_area_report_payload()
    payload["entity_scope_assessments"] = [
        assessment
        for assessment in payload["entity_scope_assessments"]
        if assessment["candidate_id"] != "operator-b-sector"
    ]
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(
        CatalogValidationError,
        match="coordinated component operator-b-sector has no scope assessment",
    ):
        validate_catalog_curation_report(report)


@pytest.mark.parametrize(
    ("field_path", "value", "message"),
    [
        ("disposition", "represented", "must use disposition=not_separate"),
        (
            "ski_area_boundary.operational_scope",
            "parent_owned",
            "must use operational_scope=coordinated",
        ),
        (
            "ski_area_boundary.parent_ski_area_id",
            "other-area",
            "must name coordinated parent coordinated-area",
        ),
        (
            "ski_area_boundary.weather_scope",
            "independent",
            "cannot retain independent weather scope",
        ),
    ],
)
def test_schema_three_coordinated_component_must_close_to_parent(
    field_path: str,
    value: str,
    message: str,
) -> None:
    payload = _coordinated_ski_area_report_payload()
    component = payload["entity_scope_assessments"][1]
    target = component
    segments = field_path.split(".")
    for segment in segments[:-1]:
        target = target[segment]
    target[segments[-1]] = value
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(CatalogValidationError, match=message):
        validate_catalog_curation_report(report)


def test_schema_three_coordinated_component_targets_only_parent_catalog_area() -> None:
    payload = _coordinated_ski_area_report_payload()
    payload["entity_scope_assessments"][1]["target_refs"] = [
        {"target_type": "ski_area", "target_id": "other-area"}
    ]
    payload["reviewed_targets"].append(
        {
            "target_type": "ski_area",
            "target_id": "other-area",
            "scope": "narrow",
            "required_field_paths": ["name"],
        }
    )
    payload["field_coverage"].append(
        {
            "target_type": "ski_area",
            "target_id": "other-area",
            "field_path": "name",
            "status": "reviewed-no-change",
        }
    )
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(
        CatalogValidationError,
        match="must target coordinated parent ski_area:coordinated-area",
    ):
        validate_catalog_curation_report(report)


def test_schema_three_coordinated_component_cannot_belong_to_two_parents() -> None:
    payload = _coordinated_ski_area_report_payload()
    first_parent = payload["entity_scope_assessments"][0]
    second_parent = json.loads(json.dumps(first_parent))
    second_parent["candidate_id"] = "second-coordinated-area"
    second_parent["candidate_name"] = "Second Coordinated Area"
    second_parent["target_refs"] = [
        {"target_type": "ski_area", "target_id": "second-coordinated-area"}
    ]
    second_parent["ski_area_boundary"]["component_candidate_ids"] = [
        "operator-a-sector",
        "operator-c-sector",
    ]
    payload["entity_scope_assessments"].append(second_parent)
    _complete_new_ski_area_report_target(payload, "second-coordinated-area")
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(
        CatalogValidationError,
        match="coordinated component operator-a-sector belongs to multiple parents",
    ):
        validate_catalog_curation_report(report)


def test_schema_three_rejects_unlisted_coordinated_child() -> None:
    payload = _coordinated_ski_area_report_payload()
    parent_boundary = payload["entity_scope_assessments"][0]["ski_area_boundary"]
    parent_boundary["component_candidate_ids"] = [
        "operator-a-sector",
        "replacement-sector",
    ]
    replacement = json.loads(json.dumps(payload["entity_scope_assessments"][2]))
    replacement["candidate_id"] = "replacement-sector"
    replacement["candidate_name"] = "Replacement Sector"
    payload["entity_scope_assessments"].append(replacement)
    report = CatalogCurationReport.model_validate(payload)

    with pytest.raises(
        CatalogValidationError,
        match="coordinated child operator-b-sector is not listed by parent coordinated-area",
    ):
        validate_catalog_curation_report(report)
```

- [ ] **Step 2: Run the graph-closure tests and verify they fail**

Run:

```bash
uv run --no-config pytest -q \
  tests/test_catalog_curation.py::test_schema_three_coordinated_parent_rejects_missing_component_assessment \
  tests/test_catalog_curation.py::test_schema_three_coordinated_component_must_close_to_parent \
  tests/test_catalog_curation.py::test_schema_three_coordinated_component_targets_only_parent_catalog_area \
  tests/test_catalog_curation.py::test_schema_three_coordinated_component_cannot_belong_to_two_parents \
  tests/test_catalog_curation.py::test_schema_three_rejects_unlisted_coordinated_child
```

Expected: failures because validation currently has no report-wide view of parent/component membership.

- [ ] **Step 3: Implement report-wide coordinated component validation**

Add a helper adjacent to `_validate_ski_area_boundary_assessment()`:

```python
def _validate_coordinated_ski_area_components(
    assessments: list[CatalogEntityScopeAssessment],
    issues: list[str],
) -> None:
    by_candidate_id = {assessment.candidate_id: assessment for assessment in assessments}
    component_parent_by_id: dict[str, str] = {}
    coordinated_parent_by_target_id: dict[str, CatalogEntityScopeAssessment] = {}

    for parent in assessments:
        boundary = parent.ski_area_boundary
        if boundary is None or boundary.operational_scope != "coordinated":
            continue
        if parent.disposition not in {"represented", "add_entity"}:
            continue
        parent_target_ids = [target.target_id for target in parent.target_refs]
        if len(parent_target_ids) != 1:
            issues.append(
                f"{parent.candidate_id}: coordinated ski area must target exactly "
                "one catalog ski area"
            )
            continue
        parent_target_id = parent_target_ids[0]
        existing_parent = coordinated_parent_by_target_id.get(parent_target_id)
        if existing_parent is not None:
            issues.append(
                f"ski_area:{parent_target_id}: coordinated parent is represented "
                "by multiple candidates"
            )
            continue
        coordinated_parent_by_target_id[parent_target_id] = parent
        for component_id in boundary.component_candidate_ids:
            if component_id == parent.candidate_id:
                issues.append(
                    f"{parent.candidate_id}: coordinated parent cannot list itself "
                    "as a component"
                )
                continue
            prior_parent = component_parent_by_id.setdefault(
                component_id, parent_target_id
            )
            if prior_parent != parent_target_id:
                issues.append(
                    f"coordinated component {component_id} belongs to multiple parents"
                )
            component = by_candidate_id.get(component_id)
            if component is None:
                issues.append(
                    f"{parent.candidate_id}: coordinated component {component_id} "
                    "has no scope assessment"
                )
                continue
            component_boundary = component.ski_area_boundary
            if component.candidate_kind != "ski_area":
                issues.append(
                    f"{component_id}: coordinated component must be a ski-area candidate"
                )
            if component.disposition != "not_separate":
                issues.append(
                    f"{component_id}: coordinated component must use "
                    "disposition=not_separate"
                )
            if component_boundary is None:
                continue
            if component_boundary.operational_scope != "coordinated":
                issues.append(
                    f"{component_id}: coordinated component must use "
                    "operational_scope=coordinated"
                )
            if component_boundary.parent_ski_area_id != parent_target_id:
                issues.append(
                    f"{component_id}: coordinated component must name coordinated "
                    f"parent {parent_target_id}"
                )
            if component_boundary.weather_scope == "independent":
                issues.append(
                    f"{component_id}: coordinated component cannot retain "
                    "independent weather scope"
                )
            if {target.target_id for target in component.target_refs} != {
                parent_target_id
            }:
                issues.append(
                    f"{component_id}: coordinated component must target coordinated "
                    f"parent ski_area:{parent_target_id}"
                )

    for child in assessments:
        boundary = child.ski_area_boundary
        if (
            child.disposition != "not_separate"
            or boundary is None
            or boundary.operational_scope != "coordinated"
            or boundary.parent_ski_area_id is None
        ):
            continue
        parent = coordinated_parent_by_target_id.get(boundary.parent_ski_area_id)
        if parent is None:
            issues.append(
                f"{child.candidate_id}: coordinated child has no represented or "
                "added coordinated parent"
            )
            continue
        parent_boundary = parent.ski_area_boundary
        assert parent_boundary is not None
        if child.candidate_id not in parent_boundary.component_candidate_ids:
            issues.append(
                f"coordinated child {child.candidate_id} is not listed by parent "
                f"{boundary.parent_ski_area_id}"
            )
```

After the per-assessment loop in `_validate_entity_scope_assessments()`, invoke it only for schema version 3:

```python
    if report.report_schema_version == 3:
        _validate_coordinated_ski_area_components(assessments, issues)
```

Keep the existing global duplicate-candidate check. It proves each candidate assessment itself occurs at most once; this helper proves coordinated membership occurs exactly once.

- [ ] **Step 4: Run graph-closure and complete curation tests**

Run:

```bash
uv run --no-config pytest -q tests/test_catalog_curation.py
```

Expected: all tests pass. The valid coordinated parent closes over both children; every malformed graph reports a candidate-specific error.

- [ ] **Step 5: Commit component reconciliation**

```bash
git add app/data/catalog_curation.py tests/test_catalog_curation.py
git commit -m "feat: reconcile coordinated ski area components"
```

---

### Task 4: Render Coordinated Provenance Without Legacy Churn

**Files:**
- Modify: `app/data/catalog_curation.py:2580-2630`
- Test: `tests/test_catalog_curation.py:1257-1285`
- Test: `tests/test_catalog_curation_reconciliation.py:200-285`
- Test: `tests/test_catalog_curation_reconciliation.py:606-646`

**Interfaces:**
- Consumes: Task 1's two metadata lists and Task 3's valid coordinated report helper.
- Produces: conditional `Components` and `Coordination Evidence` Markdown columns; report-only metadata remains outside catalog delta reconciliation.

- [ ] **Step 1: Add failing rendering tests for legacy stability and coordinated visibility**

Extend the existing Markdown test and add a coordinated case:

```python
def test_ski_area_boundary_markdown_is_rendered() -> None:
    # Keep the existing payload and assertions.
    rendered = render_catalog_curation_report_markdown(report)

    assert "## Ski-Area Boundary Assessments" in rendered
    assert "`parent-area`" in rendered
    assert "`parent_owned`" in rendered
    assert "`redundant`" in rendered
    assert "| Components |" not in rendered
    assert "| Coordination Evidence |" not in rendered


def test_coordinated_ski_area_markdown_renders_components_and_evidence() -> None:
    report = CatalogCurationReport.model_validate(
        _coordinated_ski_area_report_payload()
    )

    rendered = render_catalog_curation_report_markdown(report)

    assert "| Components | Coordination Evidence |" in rendered
    assert "`operator-a-sector`, `operator-b-sector`" in rendered
    assert "`example-scope`" in rendered
```

- [ ] **Step 2: Add a failing reconciliation test proving report-only metadata creates no catalog delta**

Add a helper that overlays coordinated provenance on the existing schema-v3 relationship report:

```python
def _with_coordinated_scope_provenance(
    report: CatalogCurationReport,
) -> CatalogCurationReport:
    payload = report.model_dump(mode="json")
    payload["entity_scope_assessments"].extend(
        [
            {
                "candidate_id": "example-area-coordinated-boundary",
                "candidate_name": "Example Area",
                "candidate_kind": "ski_area",
                "disposition": "represented",
                "signals": [
                    "official_complete_lift_inventory",
                    "coordinated_status_or_schedule",
                    "common_full_coverage_pass",
                ],
                "evidence_refs": ["example-access-scope"],
                "target_refs": [
                    {"target_type": "ski_area", "target_id": "example-area"}
                ],
                "rationale": "The official sources define one coordinated area.",
                "ski_area_boundary": {
                    "terrain_scope": "complete",
                    "connectivity_to_parent": "not_applicable",
                    "operational_scope": "coordinated",
                    "weather_scope": "unknown",
                    "pass_scope": "full_local",
                    "provider_consensus": "aggregated",
                    "separation_value": "material",
                    "component_candidate_ids": ["sector-a", "sector-b"],
                    "coordination_evidence_refs": ["example-access-scope"],
                    "evidence_refs": ["example-access-scope"],
                },
            },
            *[
                {
                    "candidate_id": component_id,
                    "candidate_name": component_id.title(),
                    "candidate_kind": "ski_area",
                    "disposition": "not_separate",
                    "signals": ["official_map_sector"],
                    "evidence_refs": ["example-access-scope"],
                    "target_refs": [
                        {"target_type": "ski_area", "target_id": "example-area"}
                    ],
                    "rationale": "The coordinated inventory assigns this sector.",
                    "ski_area_boundary": {
                        "parent_ski_area_id": "example-area",
                        "terrain_scope": "sector",
                        "connectivity_to_parent": "connected",
                        "operational_scope": "coordinated",
                        "weather_scope": "parent_owned",
                        "pass_scope": "shared_only",
                        "provider_consensus": "aggregated",
                        "separation_value": "redundant",
                        "evidence_refs": ["example-access-scope"],
                    },
                }
                for component_id in ("sector-a", "sector-b")
            ],
        ]
    )
    return CatalogCurationReport.model_validate(payload)


def test_reconcile_ignores_coordinated_report_only_provenance(tmp_path: Path) -> None:
    base_paths, current_paths = _relationship_snapshots(tmp_path)
    report = _with_coordinated_scope_provenance(
        _schema_three_relationship_report()
    )

    result = reconcile_catalog_curation_report(
        report,
        base_catalog_path=base_paths[0],
        current_catalog_path=current_paths[0],
        base_trust_manifest_path=base_paths[1],
        current_trust_manifest_path=current_paths[1],
    )

    assert {
        (delta.target_type, delta.target_id, delta.field_path)
        for delta in result.deltas
    } == {
        ("ski_area_access", "example-village--example-area", "distance_m")
    }
```

- [ ] **Step 3: Run the new tests and verify the coordinated rendering test fails**

Run:

```bash
uv run --no-config pytest -q \
  tests/test_catalog_curation.py::test_ski_area_boundary_markdown_is_rendered \
  tests/test_catalog_curation.py::test_coordinated_ski_area_markdown_renders_components_and_evidence \
  tests/test_catalog_curation_reconciliation.py::test_reconcile_ignores_coordinated_report_only_provenance
```

Expected: coordinated rendering fails because the table does not expose the two new lists; reconciliation must remain limited to the existing access delta.

- [ ] **Step 4: Render conditional coordinated columns**

Before constructing the ski-area table header, calculate:

```python
includes_coordination = any(
    bool(
        assessment.ski_area_boundary
        and (
            assessment.ski_area_boundary.component_candidate_ids
            or assessment.ski_area_boundary.coordination_evidence_refs
        )
    )
    for assessment in ski_area_assessments
)
```

Keep the current header and row formatting unchanged when `includes_coordination` is false. When true, append these columns after `Separation Value` and before `Evidence`:

```python
components = ", ".join(
    _code_cell(component_id)
    for component_id in boundary.component_candidate_ids
)
coordination_evidence = ", ".join(
    _code_cell(evidence_id)
    for evidence_id in boundary.coordination_evidence_refs
)
```

Use the exact coordinated header suffix:

```markdown
| Components | Coordination Evidence | Evidence |
```

This conditional branch is required; adding empty columns to every historical report would violate the legacy-rendering constraint.

- [ ] **Step 5: Run rendering and reconciliation suites**

Run:

```bash
uv run --no-config pytest -q \
  tests/test_catalog_curation.py \
  tests/test_catalog_curation_reconciliation.py
```

Expected: both files pass. Legacy rendering has no new columns, coordinated rendering names every component, and reconciliation produces only catalog/trust deltas.

- [ ] **Step 6: Commit rendering and reconciliation coverage**

```bash
git add \
  app/data/catalog_curation.py \
  tests/test_catalog_curation.py \
  tests/test_catalog_curation_reconciliation.py
git commit -m "test: cover coordinated ski area provenance"
```

---

### Task 5: Align Domain, Trust, And Maintainer Policy

**Files:**
- Modify: `docs/domain-language.md:339-366`
- Modify: `docs/data-trust-model.md:12-35`
- Modify: `docs/operating-model/local-maintainer-activation.md:300-445`
- Modify: `docs/engineering-notes.md:1490-1535`
- Modify: `docs/architecture/adr/0022-allow-coordinated-multi-operator-ski-areas.md`
- Modify: `docs/superpowers/specs/2026-08-26-coordinated-multi-operator-ski-areas-design.md`

**Interfaces:**
- Consumes: the implemented contract and validator behavior from Tasks 1-4.
- Produces: one repository-owned policy definition used by curators, reviewers, and post-merge installed skills.

- [ ] **Step 1: Update the domain-language definition**

Under `Ski Area`, retain the complete-terrain and material-separation rules and replace the single-owner-only wording with this distinction:

```markdown
Evidence ownership may be `independent` or `coordinated`. Independent ownership
uses the existing area-level operations, weather, or full-local-pass evidence.
A coordinated multi-operator ski area requires an official complete lift or
terrain inventory, an exhaustive component roster, a current status or schedule
presentation in which every component is addressable, one pass covering every
component, and an explicit `not_separate` assessment for every component. The
pass may also cover a separately modeled adjacent ski area and does not establish
the boundary by itself.

Minor nursery or satellite lifts may remain coordinated components when they
share the complete inventory, status system, pass, and stay market and have no
material independent recommendation, weather, season, operations, or pass value.
A complete transfer-required, weather-distinct, or independently owned area
remains a separate ski area. Coordinated operational ownership does not imply
active weather sampling; ADR 0021 is evaluated independently.
```

- [ ] **Step 2: Update source-integrity and maintainer adjudication rules**

In `docs/data-trust-model.md`, change the catalog summary from “independent terrain and weather-evidence entities” to complete terrain entities with independent or coordinated evidence ownership. Add the five required source families from the spec and state that broader status/pass sources are acceptable only when every coordinated component is exactly addressable.

In `docs/operating-model/local-maintainer-activation.md`, add the coordinated path to:

1. schema-v3 normalization requirements;
2. graph-scope inventory completeness;
3. ski-area boundary adjudication;
4. fixer instructions after `policy_determined`.

Use these exact adjudication outcomes:

```markdown
- return `policy_determined` when the complete inventory, component roster,
  coordinated status/schedule, complete-component pass, and every child
  `not_separate` assignment reconcile;
- return `evidence_insufficient` when any component cannot be reproduced from
  the bounded official packet;
- do not return `owner_choice_required` merely because several legal operators
  publish one policy-valid coordinated area.
```

- [ ] **Step 3: Record the durable implementation decision**

Add a concise `Coordinated ski-area evidence ownership` section to `docs/engineering-notes.md` stating:

```markdown
The catalog keeps one runtime `SkiArea` for a complete skier-facing area even
when several lift companies operate its components, but only through the
explicit coordinated report contract. Component ownership is curation
provenance, not a runtime `SkiSubArea` graph. Independent weather geometry and
activation remain separate, so coordinated operations cannot silently reuse or
activate weather history.
```

Change ADR 0022 from `Status: proposed` to `Status: accepted`.

Change the feature spec status to `implemented`, set its related plan to
`docs/superpowers/plans/2026-08-26-coordinated-multi-operator-ski-areas.md`, and change ADR 0022 from proposed to accepted in its related-ADR list.

- [ ] **Step 4: Verify terminology and contract consistency**

Run:

```bash
rg -n \
  "coordinated multi-operator|official_complete_lift_inventory|coordinated_status_or_schedule|common_full_coverage_pass|weather_scope" \
  app/data/catalog_curation.py \
  docs/domain-language.md \
  docs/data-trust-model.md \
  docs/operating-model/local-maintainer-activation.md \
  docs/engineering-notes.md \
  docs/architecture/adr/0022-allow-coordinated-multi-operator-ski-areas.md \
  docs/superpowers/specs/2026-08-26-coordinated-multi-operator-ski-areas-design.md
```

Expected: every document uses the same three signals, distinguishes operations from weather, and says shared-pass evidence is necessary but insufficient.

- [ ] **Step 5: Commit policy documentation**

```bash
git add \
  docs/domain-language.md \
  docs/data-trust-model.md \
  docs/operating-model/local-maintainer-activation.md \
  docs/engineering-notes.md \
  docs/architecture/adr/0022-allow-coordinated-multi-operator-ski-areas.md \
  docs/superpowers/specs/2026-08-26-coordinated-multi-operator-ski-areas-design.md
git commit -m "docs: define coordinated ski area evidence ownership"
```

---

### Task 6: Run Final Verification And Advisory Feature Review

**Files:**
- Review: `app/data/catalog_curation.py`
- Review: `tests/test_catalog_curation.py`
- Review: `tests/test_catalog_curation_reconciliation.py`
- Review: all Task 5 documentation

**Interfaces:**
- Consumes: the complete repository implementation from Tasks 1-5.
- Produces: a review-clean, mechanically verified feature branch suitable for merge before installed-skill activation.

- [ ] **Step 1: Run formatting and static checks**

```bash
uv run --no-config ruff format --check \
  app/data/catalog_curation.py \
  tests/test_catalog_curation.py \
  tests/test_catalog_curation_reconciliation.py
uv run --no-config ruff check \
  app/data/catalog_curation.py \
  tests/test_catalog_curation.py \
  tests/test_catalog_curation_reconciliation.py
git diff --check
```

Expected: all commands exit 0.

- [ ] **Step 2: Run the focused catalog contract suite**

```bash
uv run --no-config pytest -q \
  tests/test_catalog_curation.py \
  tests/test_catalog_curation_reconciliation.py \
  tests/test_catalog_models.py \
  tests/test_catalog_trust.py
```

Expected: all tests pass with no database fixture requirement.

- [ ] **Step 3: Run the current catalog validators**

```bash
uv run --no-config python -m app.data.validate_catalog \
  --catalog-path app/data/catalog.json \
  --trust-manifest-path app/data/resort_trust_manifest.json
```

Expected: the checked-in catalog and trust manifest remain valid and unchanged by this report-only feature.

- [ ] **Step 4: Run advisory feature review**

Invoke `snowcast-advisory-review` in `feature-review` mode for:

- `data-trust-source-integrity`: verify the three-signal and five-evidence-family gates, exact component addressability, pass-not-sufficient rule, and fail-closed incomplete inventory behavior;
- `backend-api`: verify backward-compatible Pydantic parsing, report-wide uniqueness/closure, conditional rendering, and absence of runtime API/catalog changes.

Accept no unresolved Blocker or High finding. Fix any accepted finding through the same test-first steps, rerun Steps 1-3, and record the final review result in the feature spec's `Advisory Review` section.

- [ ] **Step 5: Commit final review corrections if any**

If review changes were required:

```bash
git add \
  app/data/catalog_curation.py \
  tests/test_catalog_curation.py \
  tests/test_catalog_curation_reconciliation.py \
  docs/domain-language.md \
  docs/data-trust-model.md \
  docs/operating-model/local-maintainer-activation.md \
  docs/engineering-notes.md \
  docs/architecture/adr/0022-allow-coordinated-multi-operator-ski-areas.md \
  docs/superpowers/specs/2026-08-26-coordinated-multi-operator-ski-areas-design.md
git commit -m "fix: address coordinated ski area review findings"
```

If no files changed, do not create an empty commit.

- [ ] **Step 6: Confirm the branch contains no Livigno data mutation**

```bash
git diff --name-only origin/main...HEAD
git diff --exit-code origin/main...HEAD -- \
  app/data/resorts.json \
  app/data/resort_trust_manifest.json \
  app/data/terrain_domains.json \
  app/data/ski_regions.json
```

Expected: the first command lists only contract, tests, spec/ADR, plan, and policy docs; the second command exits 0.

---

### Task 7: Activate Matching Installed Skills After Merge

**Files:**
- Modify after merge: `/Users/awownysz/.codex/skills/snowcast-catalog-curation/SKILL.md`
- Modify after merge: `/Users/awownysz/.codex/skills/snowcast-catalog-review/SKILL.md`
- Read after merge: `/Users/awownysz/.codex/skills/.system/skill-creator/SKILL.md`
- Verify after merge: `docs/operating-model/local-maintainer-activation.md`

**Interfaces:**
- Consumes: the exact repository contract after this branch is merged to current `main`.
- Produces: synchronized local curation and review skills that can classify
  coordinated multi-operator boundaries without a skill/repository mismatch.

- [ ] **Step 1: Stop if the repository contract is not merged**

Run from the primary checkout:

```bash
git fetch origin main
git status --short --branch
feature_commit="$(
  git log -1 --format=%H origin/main -- \
    docs/architecture/adr/0022-allow-coordinated-multi-operator-ski-areas.md
)"
test -n "$feature_commit"
git merge-base --is-ancestor "$feature_commit" origin/main
git show "origin/main:docs/architecture/adr/0022-allow-coordinated-multi-operator-ski-areas.md" \
  | rg -q '^Status: accepted$'
git show "origin/main:app/data/catalog_curation.py" \
  | rg -q 'common_full_coverage_pass'
```

Expected: every command exits 0 and the latest ADR commit is present on
`origin/main`. If any command fails, do not modify installed skills.

- [ ] **Step 2: Load the skill-authoring contract and snapshot both installed skills**

Read `/Users/awownysz/.codex/skills/.system/skill-creator/SKILL.md`, then:

```bash
snapshot_dir="$(mktemp -d /private/tmp/snowcast-coordinated-skills.XXXXXX)"
cp -R /Users/awownysz/.codex/skills/snowcast-catalog-curation "$snapshot_dir/"
cp -R /Users/awownysz/.codex/skills/snowcast-catalog-review "$snapshot_dir/"
printf '%s\n' "$snapshot_dir"
```

Retain the printed path until both updated skills have been inspected successfully.

- [ ] **Step 3: Update the curation skill with the implemented contract**

In the `Entity Scope Inventory` and `Boundary Adjudication` sections, make these requirements explicit:

```markdown
- `operational_scope` accepts `coordinated`; `weather_scope` does not.
- A coordinated parent requires `official_complete_lift_inventory`,
  `coordinated_status_or_schedule`, and `common_full_coverage_pass`, plus
  `pass_scope=full_local` or `shared_only`.
- Reconstruct the exhaustive component roster from official sources. Add every
  component candidate ID to the parent and assess each component exactly once as
  `not_separate`, targeting the parent and using
  `operational_scope=coordinated`.
- A broader status or pass source is valid only when every coordinated component
  is exactly addressable. A pass may also cover a separately modeled adjacent
  area, but pass coverage alone never establishes the coordinated boundary.
- Keep a complete transfer-required, weather-distinct, or independently owned
  area separate. Minor satellite lifts may remain components only when the
  complete inventory, status, pass, stay market, and no-independent-value gates
  all hold.
- Evaluate weather request geometry independently and retain
  `weather_sampling_status=deferred` when ADR 0021 does not pass.
```

For evidence that closes this packet, instruct boundary adjudication to return
`policy_determined`, not `owner_choice_required` merely because multiple
operators exist.

- [ ] **Step 4: Update the review skill symmetrically**

In full review and boundary-adjudication mode, require the reviewer to reconstruct independently:

1. the parent complete map/lift inventory;
2. the exhaustive component/operator roster;
3. exact component addressability on current status/schedule evidence;
4. complete-component pass coverage;
5. every child assessment and parent target;
6. the absence of a child that independently passes complete-area, material-separation, or weather-distinct gates.

Add paired decision examples:

```markdown
- Positive: a transfer-separated independently owned area remains separate
  while adjacent evidence-complete multi-operator terrain can be one
  coordinated area containing its reconciled roster-defined components.
- Negative: a regional pass and member directory spanning transfer-separated
  complete areas cannot create one coordinated ski area without a complete
  common operating boundary.
```

The review skill must classify a missing roster, non-addressable status page, or unassigned component as `evidence_insufficient`/actionable according to the existing workflow rather than inferring closure.

- [ ] **Step 5: Inspect installed/repository consistency**

```bash
rg -n \
  "operational_scope.*coordinated|official_complete_lift_inventory|coordinated_status_or_schedule|common_full_coverage_pass|weather_scope" \
  /Users/awownysz/.codex/skills/snowcast-catalog-curation/SKILL.md \
  /Users/awownysz/.codex/skills/snowcast-catalog-review/SKILL.md \
  app/data/catalog_curation.py \
  docs/domain-language.md \
  docs/data-trust-model.md
```

Expected: both skills and the merged repository use all three exact signals, reserve `coordinated` for operations, and preserve the independent weather gate.

- [ ] **Step 6: Run a read-only PR #36 readiness check**

Invoke each skill in read-only review/adjudication mode against the current PR #36 head. Confirm both produce the same possible policy path:

- Mottolino-Trepalle remains a separate complete area;
- the west side is accepted only if the bounded official packet closes every coordinated component;
- missing component closure remains fail-closed;
- weather activation remains a separate conclusion.

Do not edit PR #36, publish a maintainer label, push its branch, approve it, or merge it during this smoke check.

- [ ] **Step 7: Retain the rollback snapshot through the first maintainer cycle**

Record the private snapshot path in the implementation handoff. Keep it until
one PR #36 maintainer cycle completes under the merged contract. If any
skill/repository mismatch is found, restore both directories from the snapshot
before resuming scheduled maintainer work. Cleanup of that temporary rollback
snapshot is a separate explicit owner action.
