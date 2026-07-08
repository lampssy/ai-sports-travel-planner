from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    field_validator,
    model_validator,
)


class MaintainerLane(StrEnum):
    CATALOG_DISCOVERY = "lane:catalog-discovery"
    CATALOG_CURATION = "lane:catalog-curation"


class MaintainerState(StrEnum):
    PROPOSAL = "maintainer:proposal"
    WORKING = "maintainer:working"
    WAITING_CI = "maintainer:waiting-ci"
    READY = "maintainer:ready"
    OWNER_DECISION = "maintainer:owner-decision"
    MANUAL_CHECK = "maintainer:manual-check"
    BLOCKED = "maintainer:blocked"


class _MaintainerModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class PullRequest(_MaintainerModel):
    number: int = Field(gt=0)
    title: str
    url: HttpUrl
    base_ref_name: str
    head_ref_name: str
    head_repository_owner: str
    is_cross_repository: bool
    created_at: datetime
    labels: frozenset[str] = Field(default_factory=frozenset)
    head_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    mergeable: Literal["MERGEABLE", "CONFLICTING", "UNKNOWN"]
    check_state: Literal["pending", "success", "failure"]
    changed_paths: frozenset[str] = Field(default_factory=frozenset)
    body: str = ""

    @field_validator("title")
    @classmethod
    def validate_title(cls, title: str) -> str:
        if not title.strip():
            raise ValueError("title must not be blank")
        return title

    @field_validator("url")
    @classmethod
    def validate_url(cls, url: HttpUrl) -> HttpUrl:
        if url.scheme != "https" or url.host != "github.com":
            raise ValueError("url must be a GitHub URL")
        return url

    @model_validator(mode="after")
    def validate_routing_labels(self) -> Self:
        lanes = [lane for lane in MaintainerLane if lane.value in self.labels]
        if len(lanes) > 1:
            raise ValueError("pull request may have at most one maintainer lane")

        states = [state for state in MaintainerState if state.value in self.labels]
        if len(states) > 1:
            raise ValueError("pull request may have at most one maintainer state")
        return self

    @property
    def lane(self) -> MaintainerLane | None:
        return next(
            (lane for lane in MaintainerLane if lane.value in self.labels),
            None,
        )

    @property
    def maintainer_state(self) -> MaintainerState | None:
        return next(
            (state for state in MaintainerState if state.value in self.labels),
            None,
        )


class MachineState(_MaintainerModel):
    schema_version: Literal[1] = 1
    head_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    lineage_id: str
    completed_cycles: int = Field(default=0, ge=0, le=3)
    candidate_key: str | None = None
    candidate_origin_fingerprint: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    candidate_fingerprint: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    regional_graph_key: str | None = Field(
        default=None,
        pattern=r"^[a-z0-9-]+$",
    )
    last_publication: Literal["none", "body", "comment", "labels", "complete"]

    @field_validator("lineage_id")
    @classmethod
    def validate_lineage_id(cls, lineage_id: str) -> str:
        if not lineage_id.strip():
            raise ValueError("lineage_id must not be blank")
        return lineage_id

    @field_validator("candidate_key")
    @classmethod
    def validate_candidate_key(cls, candidate_key: str | None) -> str | None:
        if candidate_key is not None and not candidate_key.strip():
            raise ValueError("candidate_key must not be blank")
        return candidate_key

    @model_validator(mode="after")
    def validate_candidate_metadata(self) -> Self:
        metadata = (
            self.candidate_origin_fingerprint,
            self.candidate_fingerprint,
            self.regional_graph_key,
        )
        if self.candidate_key is None and any(value is not None for value in metadata):
            raise ValueError(
                "candidate fingerprints and graph metadata require candidate_key"
            )
        return self
