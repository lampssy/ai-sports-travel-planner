import re
from collections.abc import Callable, Iterator, Mapping
from copy import deepcopy
from dataclasses import dataclass
from typing import Annotated, Any, Generic, Literal, Self, TypeVar
from urllib.parse import parse_qs, urlsplit

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PlainSerializer,
    StringConstraints,
    field_validator,
)

from app.domain.catalog import CatalogSnapshot, SkiAreaAccess
from app.domain.source_urls import (
    DIRECT_EXTERNAL_HTTP_URL_ERROR,
    validate_direct_external_http_url,
)

CatalogEntityType = Literal[
    "ski_regions",
    "stay_destinations",
    "stay_bases",
    "ski_areas",
    "ski_area_access",
    "terrain_domains",
    "lift_pass_products",
    "rental_display_facts",
]
Status = Literal[
    "verified",
    "verified_with_adjustment",
    "estimated",
    "needs_source",
]

_KeyT = TypeVar("_KeyT")
_ValueT = TypeVar("_ValueT")


class _FrozenMapping(Mapping[_KeyT, _ValueT], Generic[_KeyT, _ValueT]):
    __slots__ = ("_items",)

    def __init__(self, value: Mapping[_KeyT, _ValueT]) -> None:
        object.__setattr__(self, "_items", tuple(value.items()))

    def __getitem__(self, key: _KeyT) -> _ValueT:
        for candidate, value in self._items:
            if candidate == key:
                return value
        raise KeyError(key)

    def __iter__(self) -> Iterator[_KeyT]:
        return (key for key, _ in self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __setattr__(self, name: str, value: object) -> None:
        raise TypeError("frozen mapping is immutable")

    def __delattr__(self, name: str) -> None:
        raise TypeError("frozen mapping is immutable")

    def __copy__(self) -> Self:
        return self

    def __deepcopy__(self, memo: dict[int, Any]) -> Self:
        copied = object.__new__(type(self))
        memo[id(self)] = copied
        object.__setattr__(copied, "_items", deepcopy(self._items, memo))
        return copied

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Mapping):
            return False
        return dict(self.items()) == dict(other.items())

    def __repr__(self) -> str:
        return f"{type(self).__name__}({dict(self.items())!r})"


_ENTITY_TYPES: tuple[CatalogEntityType, ...] = (
    "ski_regions",
    "stay_destinations",
    "stay_bases",
    "ski_areas",
    "ski_area_access",
    "terrain_domains",
    "lift_pass_products",
    "rental_display_facts",
)
_STATUS_VALUES: tuple[Status, ...] = (
    "verified",
    "verified_with_adjustment",
    "estimated",
    "needs_source",
)
_SOURCE_REQUIRED_STATUSES = frozenset({"verified", "verified_with_adjustment"})

FIELD_GROUPS: Mapping[CatalogEntityType, tuple[str, ...]] = _FrozenMapping(
    {
        "ski_regions": ("identity", "membership_context"),
        "stay_destinations": (
            "identity_location",
            "coordinates",
            "price_level",
        ),
        "stay_bases": (
            "identity_ownership",
            "coordinates",
            "elevation",
            "lodging_price_quality",
            "base_type",
            "base_character",
            "local_apres",
        ),
        "ski_areas": (
            "identity_coordinates",
            "elevation_season",
            "terrain_metrics",
            "skill_fit",
            "snowmaking",
            "glacier_terrain",
            "snow_park",
            "night_skiing",
            "marked_freeride_routes",
            "ski_day_apres",
            "official_documents",
        ),
        "ski_area_access": ("relationship", "access_mode_distance"),
        "terrain_domains": (
            "membership_connectivity",
            "aggregate_terrain",
            "season",
            "official_documents",
        ),
        "lift_pass_products": (
            "identity_scope_availability",
            "coverage",
            "prices",
            "pass_accessible_terrain",
        ),
        "rental_display_facts": (
            "identity_ownership",
            "price_quality_access",
        ),
    }
)

_MODEL_CONFIG = ConfigDict(
    frozen=True,
    extra="forbid",
    revalidate_instances="always",
)
_NonBlankText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]


class _TrustModel(BaseModel):
    model_config = _MODEL_CONFIG

    def model_copy(
        self,
        *,
        update: Mapping[str, Any] | None = None,
        deep: bool = False,
    ) -> Self:
        data = self.model_dump(mode="python", round_trip=True)
        if deep:
            data = deepcopy(data)
        if update is not None:
            validated_update = deepcopy(dict(update)) if deep else dict(update)
            data.update(validated_update)
        return type(self).model_validate(data)


def _freeze_statuses(value: Mapping[str, Status]) -> Mapping[str, Status]:
    return _FrozenMapping(dict(value))


def _serialize_statuses(value: Mapping[str, Status]) -> dict[str, Status]:
    return dict(value)


_FieldStatuses = Annotated[
    Mapping[str, Status],
    PlainSerializer(_serialize_statuses, return_type=dict[str, Status]),
]


_GOOGLE_SEARCH_HOST_PATTERN = re.compile(
    r"(?:[a-z0-9-]+\.)*google\."
    r"(?:[a-z]{2,3}|(?:co|com)\.[a-z]{2})",
    flags=re.IGNORECASE,
)
_SEARCH_RESULT_PATTERNS = (
    (
        "bing.com",
        ("/images/search", "/news/search", "/search", "/videos/search"),
        frozenset({"q"}),
    ),
    ("search.yahoo.com", ("/search",), frozenset({"p"})),
    (
        "duckduckgo.com",
        ("/", "/html", "/lite"),
        frozenset({"q"}),
    ),
    (
        "search.brave.com",
        ("/images", "/news", "/search", "/videos"),
        frozenset({"q"}),
    ),
    ("ecosia.org", ("/images", "/news", "/search", "/videos"), frozenset({"q"})),
    (
        "startpage.com",
        ("/do/search", "/sp/search"),
        frozenset({"query"}),
    ),
    ("qwant.com", ("/", "/search"), frozenset({"q"})),
    ("baidu.com", ("/s", "/search"), frozenset({"wd", "word"})),
    (
        "yandex.com",
        ("/images/search", "/news", "/search", "/video/search"),
        frozenset({"text"}),
    ),
    (
        "yandex.ru",
        ("/images/search", "/news", "/search", "/video/search"),
        frozenset({"text"}),
    ),
)


def _hostname_matches(hostname: str, expected: str) -> bool:
    return hostname == expected or hostname.endswith(f".{expected}")


def _path_matches_category(path: str, category: str) -> bool:
    if category == "/":
        return path == category
    return path == category or path.startswith(f"{category}/")


def _is_web_search_result_url(value: str) -> bool:
    parsed = urlsplit(value)
    hostname = (parsed.hostname or "").casefold()
    path = parsed.path.rstrip("/").casefold() or "/"
    query_keys = {
        key.casefold() for key in parse_qs(parsed.query, keep_blank_values=True)
    }

    if _GOOGLE_SEARCH_HOST_PATTERN.fullmatch(hostname):
        if path == "/search" and "q" in query_keys:
            return True
        if path == "/url" and query_keys.intersection({"q", "url"}):
            return True

    return any(
        _hostname_matches(hostname, expected_hostname)
        and any(
            _path_matches_category(path, search_path) for search_path in search_paths
        )
        and not query_keys.isdisjoint(search_query_keys)
        for expected_hostname, search_paths, search_query_keys in (
            _SEARCH_RESULT_PATTERNS
        )
    )


def _validate_source_refs(
    values: tuple[str, ...],
    *,
    field_path: str,
) -> tuple[str, ...]:
    normalized: list[str] = []
    for index, source_ref in enumerate(values):
        try:
            direct_url = validate_direct_external_http_url(source_ref)
        except ValueError as error:
            raise ValueError(f"{field_path}[{index}] {error}") from error
        if _is_web_search_result_url(direct_url):
            raise ValueError(
                f"{field_path}[{index}] {DIRECT_EXTERNAL_HTTP_URL_ERROR}: "
                "web search result URLs are not allowed"
            )
        normalized.append(direct_url)
    return tuple(sorted(set(normalized)))


def _serialize_field_source_refs(
    value: Mapping[str, tuple[str, ...]],
) -> dict[str, tuple[str, ...]]:
    return dict(value)


_FieldSourceRefs = Annotated[
    Mapping[str, tuple[str, ...]],
    PlainSerializer(
        _serialize_field_source_refs,
        return_type=dict[str, tuple[str, ...]],
    ),
]


class EntityTrustEntry(_TrustModel):
    display_name: _NonBlankText
    field_statuses: _FieldStatuses
    field_source_refs: _FieldSourceRefs
    notes: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("field_statuses")
    @classmethod
    def freeze_field_statuses(cls, value: Mapping[str, Status]) -> Mapping[str, Status]:
        return _freeze_statuses(value)

    @field_validator("field_source_refs")
    @classmethod
    def validate_field_source_refs(
        cls,
        values: Mapping[str, tuple[str, ...]],
    ) -> Mapping[str, tuple[str, ...]]:
        return _FrozenMapping(
            {
                group: _validate_source_refs(
                    refs,
                    field_path=f"field_source_refs.{group}",
                )
                for group, refs in values.items()
            }
        )


def _canonicalize_entry_groups(
    entity_type: CatalogEntityType,
    entry: EntityTrustEntry,
) -> EntityTrustEntry:
    declared_groups = FIELD_GROUPS[entity_type]
    expected_groups = set(declared_groups)
    for field_name, values in (
        ("field_statuses", entry.field_statuses),
        ("field_source_refs", entry.field_source_refs),
    ):
        actual_groups = set(values)
        missing_groups = sorted(expected_groups - actual_groups)
        unknown_groups = sorted(actual_groups - expected_groups)
        if missing_groups or unknown_groups:
            details: list[str] = []
            if missing_groups:
                details.append(f"missing: {', '.join(missing_groups)}")
            if unknown_groups:
                details.append(f"unknown: {', '.join(unknown_groups)}")
            raise ValueError(
                f"{entity_type} {field_name} must match FIELD_GROUPS "
                f"({'; '.join(details)})"
            )
    return entry.model_copy(
        update={
            "field_statuses": {
                group: entry.field_statuses[group] for group in declared_groups
            },
            "field_source_refs": {
                group: entry.field_source_refs[group] for group in declared_groups
            },
        }
    )


def _serialize_field_groups(
    value: Mapping[CatalogEntityType, tuple[str, ...]],
) -> dict[CatalogEntityType, tuple[str, ...]]:
    return dict(value)


_FieldGroups = Annotated[
    Mapping[CatalogEntityType, tuple[str, ...]],
    PlainSerializer(
        _serialize_field_groups,
        return_type=dict[CatalogEntityType, tuple[str, ...]],
    ),
]


def _serialize_entities(
    value: Mapping[CatalogEntityType, Mapping[str, EntityTrustEntry]],
) -> dict[CatalogEntityType, dict[str, EntityTrustEntry]]:
    return {entity_type: dict(entries) for entity_type, entries in value.items()}


_Entities = Annotated[
    Mapping[CatalogEntityType, Mapping[str, EntityTrustEntry]],
    PlainSerializer(
        _serialize_entities,
        return_type=dict[CatalogEntityType, dict[str, EntityTrustEntry]],
    ),
]


def _validate_namespace_keys(value: Any, field_name: str) -> Any:
    if not isinstance(value, Mapping):
        return value

    invalid_key_types = sorted(
        {type(key).__name__ for key in value if not isinstance(key, str)}
    )
    if invalid_key_types:
        raise ValueError(
            f"{field_name} namespace keys must be strings; "
            f"got: {', '.join(invalid_key_types)}"
        )

    actual = set(value)
    expected = set(_ENTITY_TYPES)
    missing = sorted(expected - actual)
    unknown = sorted(actual - expected)
    if missing or unknown:
        details: list[str] = []
        if missing:
            details.append(f"missing: {', '.join(missing)}")
        if unknown:
            details.append(f"unknown: {', '.join(unknown)}")
        raise ValueError(
            f"{field_name} must contain exactly all catalog entity namespaces "
            f"({'; '.join(details)})"
        )
    return value


@dataclass(frozen=True)
class _CatalogNameIndex:
    stay_bases: Mapping[str, str]
    ski_areas: Mapping[str, str]


def _direct_display_name(entity: Any, _: _CatalogNameIndex) -> str:
    return str(entity.name)


def _access_display_name(entity: Any, names: _CatalogNameIndex) -> str:
    base_name = names.stay_bases[entity.stay_base_id]
    area_name = names.ski_areas[entity.ski_area_id]
    return f"{base_name} -> {area_name}"


@dataclass(frozen=True)
class _EntityDescriptor:
    entity_type: CatalogEntityType
    id_field: str
    display_name: Callable[[Any, _CatalogNameIndex], str]


_ENTITY_DESCRIPTORS = (
    _EntityDescriptor("ski_regions", "ski_region_id", _direct_display_name),
    _EntityDescriptor("stay_destinations", "stay_destination_id", _direct_display_name),
    _EntityDescriptor("stay_bases", "stay_base_id", _direct_display_name),
    _EntityDescriptor("ski_areas", "ski_area_id", _direct_display_name),
    _EntityDescriptor("ski_area_access", "ski_area_access_id", _access_display_name),
    _EntityDescriptor("terrain_domains", "terrain_domain_id", _direct_display_name),
    _EntityDescriptor(
        "lift_pass_products", "lift_pass_product_id", _direct_display_name
    ),
    _EntityDescriptor(
        "rental_display_facts", "rental_display_fact_id", _direct_display_name
    ),
)


def _validate_access_source_rollup(
    access: SkiAreaAccess,
    entry: EntityTrustEntry,
) -> None:
    catalog_sources = set(access.source_urls)
    grouped_sources = {
        source for sources in entry.field_source_refs.values() for source in sources
    }
    unowned = sorted(catalog_sources - grouped_sources)
    if unowned:
        raise ValueError(
            f"ski_area_access/{access.ski_area_access_id}: catalog sources without "
            f"field-group ownership: {', '.join(unowned)}"
        )
    absent = sorted(grouped_sources - catalog_sources)
    if absent:
        raise ValueError(
            f"ski_area_access/{access.ski_area_access_id}: field-group sources "
            f"absent from catalog source_urls: {', '.join(absent)}"
        )


assert tuple(descriptor.entity_type for descriptor in _ENTITY_DESCRIPTORS) == (
    _ENTITY_TYPES
)


class CatalogTrustManifest(_TrustModel):
    version: _NonBlankText
    catalog_schema_version: Literal[2]
    status_values: tuple[Status, ...]
    field_groups: _FieldGroups
    entities: _Entities

    @field_validator("status_values")
    @classmethod
    def validate_status_values(cls, values: tuple[Status, ...]) -> tuple[Status, ...]:
        if len(values) != len(set(values)):
            raise ValueError("status_values must not contain duplicates")
        if set(values) != set(_STATUS_VALUES):
            raise ValueError("status_values must contain exactly all four statuses")
        return _STATUS_VALUES

    @field_validator("field_groups", mode="before")
    @classmethod
    def validate_field_group_namespaces(cls, value: Any) -> Any:
        return _validate_namespace_keys(value, "field_groups")

    @field_validator("field_groups")
    @classmethod
    def validate_and_freeze_field_groups(
        cls, value: Mapping[CatalogEntityType, tuple[str, ...]]
    ) -> Mapping[CatalogEntityType, tuple[str, ...]]:
        for entity_type in _ENTITY_TYPES:
            if value[entity_type] != FIELD_GROUPS[entity_type]:
                raise ValueError(
                    f"field_groups {entity_type} must equal FIELD_GROUPS: "
                    f"expected {FIELD_GROUPS[entity_type]}, got {value[entity_type]}"
                )
        return _FrozenMapping(
            {entity_type: tuple(value[entity_type]) for entity_type in _ENTITY_TYPES}
        )

    @field_validator("entities", mode="before")
    @classmethod
    def validate_entity_namespaces(cls, value: Any) -> Any:
        return _validate_namespace_keys(value, "entities")

    @field_validator("entities")
    @classmethod
    def freeze_entities(
        cls,
        value: Mapping[CatalogEntityType, Mapping[str, EntityTrustEntry]],
    ) -> Mapping[CatalogEntityType, Mapping[str, EntityTrustEntry]]:
        return _FrozenMapping(
            {
                entity_type: _FrozenMapping(
                    {
                        entity_id: _canonicalize_entry_groups(
                            entity_type,
                            value[entity_type][entity_id],
                        )
                        for entity_id in sorted(value[entity_type])
                    }
                )
                for entity_type in _ENTITY_TYPES
            }
        )

    def validate_against_catalog(self, snapshot: CatalogSnapshot) -> None:
        if self.catalog_schema_version != snapshot.schema_version:
            raise ValueError(
                "catalog_schema_version does not match catalog schema_version"
            )

        names = _CatalogNameIndex(
            stay_bases={item.stay_base_id: item.name for item in snapshot.stay_bases},
            ski_areas={item.ski_area_id: item.name for item in snapshot.ski_areas},
        )
        for descriptor in _ENTITY_DESCRIPTORS:
            catalog_entities = getattr(snapshot, descriptor.entity_type)
            catalog_by_id = {
                getattr(entity, descriptor.id_field): entity
                for entity in catalog_entities
            }
            trust_entries = self.entities[descriptor.entity_type]

            missing_ids = sorted(set(catalog_by_id) - set(trust_entries))
            if missing_ids:
                entity_id = missing_ids[0]
                raise ValueError(
                    f"{descriptor.entity_type}/{entity_id}: missing trust entry"
                )

            unknown_ids = sorted(set(trust_entries) - set(catalog_by_id))
            if unknown_ids:
                entity_id = unknown_ids[0]
                raise ValueError(
                    f"{descriptor.entity_type}/{entity_id}: unknown trust entry"
                )

            required_groups = FIELD_GROUPS[descriptor.entity_type]
            for entity_id, entity in catalog_by_id.items():
                entry = trust_entries[entity_id]
                expected_name = descriptor.display_name(entity, names)
                if entry.display_name != expected_name:
                    raise ValueError(
                        f"{descriptor.entity_type}/{entity_id}: display_name "
                        f"{entry.display_name!r} does not match catalog name "
                        f"{expected_name!r}"
                    )

                for group in required_groups:
                    if (
                        entry.field_statuses[group] in _SOURCE_REQUIRED_STATUSES
                        and not entry.field_source_refs[group]
                    ):
                        raise ValueError(
                            f"{descriptor.entity_type}/{entity_id}/{group}: "
                            "verified status requires at least one source ref"
                        )
                if descriptor.entity_type == "ski_area_access":
                    _validate_access_source_rollup(entity, entry)
