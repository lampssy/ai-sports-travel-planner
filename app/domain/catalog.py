from collections.abc import Iterable, Mapping
from types import MappingProxyType
from typing import Annotated, Any, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    PlainSerializer,
    StringConstraints,
    ValidationInfo,
    field_validator,
    model_validator,
)

from app.domain.models import (
    LiftDistance,
    LiftPassPrice,
    LiftPassValidityScope,
    PisteKmByDifficulty,
    PriceLevel,
    Quality,
    SeasonWindow,
    SkillLevel,
)
from app.domain.source_urls import validate_direct_external_http_url

CatalogSchemaVersion = Literal[2]
SkiRegionGroupingPolicy = Literal["trip_market", "regional_network"]
SkiAreaAccessMode = Literal[
    "walk",
    "ski_bus",
    "drive",
    "ski_in_ski_out",
    "mixed",
    "unknown",
]
WeatherSamplingStatus = Literal["active", "deferred"]
TerrainMetricScope = Literal["aggregate", "pass_accessible"]
AvailabilityStatus = Literal["available", "unavailable", "unknown"]
SnowmakingCoverageBasis = Literal[
    "piste_length",
    "skiable_area",
    "run_count",
    "publisher_unspecified",
    "unknown",
]
ApresIntensity = Literal[
    "low_key",
    "moderate",
    "lively",
    "destination_defining",
]
BaseType = Literal[
    "town",
    "village",
    "hamlet",
    "resort_station",
    "neighbourhood",
    "resort_sector",
]
DevelopmentStyle = Literal["traditional", "mixed", "planned_resort", "unknown"]
LocalPace = Literal["quiet", "balanced", "lively", "unknown"]
CatalogId = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
SeasonLabel = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


def _freeze_regional_data_ids(value: Mapping[str, str]) -> Mapping[str, str]:
    return MappingProxyType(dict(value))


def _serialize_regional_data_ids(value: Mapping[str, str]) -> dict[str, str]:
    return dict(value)


def _empty_regional_data_ids() -> Mapping[str, str]:
    return MappingProxyType({})


RegionalDataIds = Annotated[
    Mapping[str, str],
    AfterValidator(_freeze_regional_data_ids),
    PlainSerializer(_serialize_regional_data_ids, return_type=dict[str, str]),
]

_CATALOG_MODEL_CONFIG = ConfigDict(
    frozen=True,
    extra="forbid",
    revalidate_instances="always",
)


class _CatalogModel(BaseModel):
    model_config = _CATALOG_MODEL_CONFIG


class CatalogSeasonWindow(SeasonWindow):
    model_config = _CATALOG_MODEL_CONFIG


class CatalogPisteKmByDifficulty(PisteKmByDifficulty):
    model_config = _CATALOG_MODEL_CONFIG


class CatalogLiftPassPrice(LiftPassPrice):
    model_config = _CATALOG_MODEL_CONFIG


class AvailabilityFact(_CatalogModel):
    availability: AvailabilityStatus = "unknown"


class SnowmakingFact(_CatalogModel):
    availability: AvailabilityStatus = "unknown"
    coverage_pct: float | None = Field(default=None, ge=0, le=100)
    coverage_basis: SnowmakingCoverageBasis = "unknown"
    season_label: SeasonLabel | None = None

    @model_validator(mode="after")
    def validate_coverage(self) -> "SnowmakingFact":
        if self.coverage_pct is None:
            if self.coverage_basis != "unknown":
                raise ValueError("snowmaking coverage basis requires a percentage")
            return self
        if self.coverage_basis == "unknown":
            raise ValueError("snowmaking percentage requires a coverage basis")
        expected_availability = "unavailable" if self.coverage_pct == 0 else "available"
        if self.availability != expected_availability:
            raise ValueError(
                f"snowmaking percentage requires availability={expected_availability}"
            )
        return self


class SnowParkFact(_CatalogModel):
    availability: AvailabilityStatus = "unknown"
    park_count: int | None = Field(default=None, ge=1)
    season_label: SeasonLabel | None = None

    @model_validator(mode="after")
    def validate_count(self) -> "SnowParkFact":
        if self.park_count is not None and self.availability != "available":
            raise ValueError("snow park count requires availability=available")
        return self


class SeasonalFeatureFact(_CatalogModel):
    availability: AvailabilityStatus = "unknown"
    season_label: SeasonLabel | None = None


class MarkedFreerideRoutesFact(_CatalogModel):
    availability: AvailabilityStatus = "unknown"
    route_count: int | None = Field(default=None, ge=1)
    season_label: SeasonLabel | None = None

    @model_validator(mode="after")
    def validate_count(self) -> "MarkedFreerideRoutesFact":
        if self.route_count is not None and self.availability != "available":
            raise ValueError("freeride route count requires availability=available")
        return self


class OfficialLinkFact(_CatalogModel):
    url: str
    season_label: SeasonLabel | None = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        return validate_direct_external_http_url(value)


class ApresProfileFact(_CatalogModel):
    availability: AvailabilityStatus = "unknown"
    intensity: ApresIntensity | None = None
    season_label: SeasonLabel | None = None

    @model_validator(mode="after")
    def validate_intensity(self) -> "ApresProfileFact":
        if self.availability == "available" and self.intensity is None:
            raise ValueError("available apres requires intensity")
        if self.availability != "available" and self.intensity is not None:
            raise ValueError("apres intensity requires availability=available")
        return self


class BaseCharacterFact(_CatalogModel):
    development_style: DevelopmentStyle = "unknown"
    local_pace: LocalPace = "unknown"


def _unique_ids(items: Iterable[BaseModel], id_field: str) -> set[str]:
    ids: set[str] = set()
    for item in items:
        item_id = getattr(item, id_field)
        if item_id in ids:
            raise ValueError(f"duplicate {id_field}: {item_id}")
        ids.add(item_id)
    return ids


def _validate_source_urls(values: tuple[str, ...], owner: str) -> tuple[str, ...]:
    normalized: list[str] = []
    for index, source_url in enumerate(values):
        try:
            normalized.append(validate_direct_external_http_url(source_url))
        except ValueError as error:
            raise ValueError(f"{owner} source_urls[{index}] {error}") from error
    return tuple(normalized)


def _require_source_urls(data: Any, owner: str) -> Any:
    if isinstance(data, dict) and not data.get("source_urls"):
        raise ValueError(f"{owner} source_urls must contain at least one direct URL")
    return data


def _source_owner_from_context(info: ValidationInfo, fallback: str) -> str:
    if isinstance(info.context, dict):
        owner = info.context.get("source_owner")
        if isinstance(owner, str):
            return owner
    return fallback


def _source_owner_is_usable(info: ValidationInfo) -> bool:
    return (
        isinstance(info.context, dict)
        and info.context.get("source_owner_usable") is True
    )


def _owner_id_is_usable(owner_id: object) -> bool:
    return isinstance(owner_id, str) and bool(owner_id.strip())


def _owner_label(owner_field: str, owner_id: object) -> str:
    if _owner_id_is_usable(owner_id):
        assert isinstance(owner_id, str)
        return f"{owner_field} {owner_id.strip()}"
    return f"{owner_field} <invalid>"


def _reject_duplicate_ids(
    values: tuple[CatalogId, ...], owner: str, field_name: str
) -> None:
    seen: set[str] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"{owner} has duplicate {field_name}: {value}")
        seen.add(value)


class SkiRegion(_CatalogModel):
    ski_region_id: CatalogId
    name: str
    grouping_policy: SkiRegionGroupingPolicy
    parent_ski_region_id: CatalogId | None = None
    source_urls: tuple[str, ...] = ()

    @field_validator("source_urls")
    @classmethod
    def validate_source_urls(
        cls, values: tuple[str, ...], info: ValidationInfo
    ) -> tuple[str, ...]:
        owner = _owner_label("ski_region_id", info.data.get("ski_region_id"))
        return _validate_source_urls(values, owner)


class StayDestination(_CatalogModel):
    stay_destination_id: CatalogId
    name: str
    country: str
    region: str
    price_level: PriceLevel
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    trip_market_region_id: CatalogId
    regional_data_ids: RegionalDataIds = Field(default_factory=_empty_regional_data_ids)


class StayBase(_CatalogModel):
    stay_base_id: CatalogId
    stay_destination_id: CatalogId
    name: str
    price_range: str
    price_min: float
    price_max: float
    quality: Quality
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    elevation_m: int | None = Field(default=None, ge=0)
    base_type: BaseType | None = None
    base_character: BaseCharacterFact = Field(default_factory=BaseCharacterFact)
    local_apres_profile: ApresProfileFact = Field(default_factory=ApresProfileFact)
    regional_data_ids: RegionalDataIds = Field(default_factory=_empty_regional_data_ids)


class SkiArea(_CatalogModel):
    ski_area_id: CatalogId
    name: str
    weather_sampling_status: WeatherSamplingStatus
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    base_elevation_m: int = Field(ge=0)
    summit_elevation_m: int = Field(ge=0)
    season_start_month: int = Field(ge=1, le=12)
    season_end_month: int = Field(ge=1, le=12)
    season_windows: tuple[CatalogSeasonWindow, ...] = ()
    total_piste_km: float | None = Field(default=None, ge=0)
    total_lift_count: int | None = Field(default=None, ge=0)
    piste_km_by_difficulty: CatalogPisteKmByDifficulty | None = None
    supported_skill_levels: tuple[SkillLevel, ...] = ()
    snowmaking: SnowmakingFact = Field(default_factory=SnowmakingFact)
    glacier_terrain: AvailabilityFact = Field(default_factory=AvailabilityFact)
    snow_park: SnowParkFact = Field(default_factory=SnowParkFact)
    night_skiing: SeasonalFeatureFact = Field(default_factory=SeasonalFeatureFact)
    marked_freeride_routes: MarkedFreerideRoutesFact = Field(
        default_factory=MarkedFreerideRoutesFact
    )
    official_trail_map: OfficialLinkFact | None = None
    ski_day_apres_profile: ApresProfileFact = Field(default_factory=ApresProfileFact)


class SkiAreaAccess(_CatalogModel):
    ski_area_access_id: CatalogId
    stay_base_id: CatalogId
    ski_area_id: CatalogId
    access_mode: SkiAreaAccessMode
    lift_distance: LiftDistance
    nearest_lift_name: str | None = None
    distance_m: int | None = Field(default=None, ge=0)
    duration_minutes: int | None = Field(default=None, ge=0)
    is_direct: bool
    regional_data_ids: RegionalDataIds = Field(default_factory=_empty_regional_data_ids)
    source_urls: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="before")
    @classmethod
    def validate_required_source_urls(cls, data: Any) -> Any:
        if isinstance(data, dict):
            owner_id = data.get("ski_area_access_id")
            if _owner_id_is_usable(owner_id):
                owner = _owner_label("ski_area_access_id", owner_id)
                return _require_source_urls(data, owner)
        return data

    @field_validator("source_urls")
    @classmethod
    def validate_source_urls(
        cls, values: tuple[str, ...], info: ValidationInfo
    ) -> tuple[str, ...]:
        owner = _owner_label("ski_area_access_id", info.data.get("ski_area_access_id"))
        return _validate_source_urls(values, owner)


class AggregateTerrainMetrics(_CatalogModel):
    metric_scope: Literal["pass_accessible"] = "pass_accessible"
    total_piste_km: float | None = Field(default=None, ge=0)
    total_lift_count: int | None = Field(default=None, ge=0)
    piste_km_by_difficulty: CatalogPisteKmByDifficulty | None = None
    source_urls: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="before")
    @classmethod
    def validate_required_source_urls(cls, data: Any, info: ValidationInfo) -> Any:
        if _source_owner_is_usable(info):
            owner = _source_owner_from_context(info, "pass aggregate")
            return _require_source_urls(data, owner)
        return data

    @field_validator("source_urls")
    @classmethod
    def validate_source_urls(
        cls, values: tuple[str, ...], info: ValidationInfo
    ) -> tuple[str, ...]:
        owner = _source_owner_from_context(info, "pass aggregate")
        return _validate_source_urls(values, owner)


class TerrainDomain(_CatalogModel):
    terrain_domain_id: CatalogId
    name: str
    ski_area_ids: tuple[CatalogId, ...] = Field(min_length=2)
    metric_scope: Literal["aggregate"] = "aggregate"
    total_piste_km: float | None = Field(default=None, ge=0)
    total_lift_count: int | None = Field(default=None, ge=0)
    base_elevation_m: int | None = Field(default=None, ge=0)
    summit_elevation_m: int | None = Field(default=None, ge=0)
    piste_km_by_difficulty: CatalogPisteKmByDifficulty | None = None
    season_windows: tuple[CatalogSeasonWindow, ...] = ()
    official_trail_map: OfficialLinkFact | None = None
    source_urls: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="before")
    @classmethod
    def validate_required_source_urls(cls, data: Any) -> Any:
        if isinstance(data, dict):
            owner_id = data.get("terrain_domain_id")
            if _owner_id_is_usable(owner_id):
                owner = _owner_label("terrain_domain_id", owner_id)
                data = _require_source_urls(data, owner)
                ski_area_ids = data.get("ski_area_ids")
                if isinstance(ski_area_ids, (list, tuple)) and len(ski_area_ids) < 2:
                    raise ValueError(
                        f"{owner} ski_area_ids must contain at least two distinct IDs"
                    )
            return data
        return data

    @field_validator("source_urls")
    @classmethod
    def validate_source_urls(
        cls, values: tuple[str, ...], info: ValidationInfo
    ) -> tuple[str, ...]:
        owner = _owner_label("terrain_domain_id", info.data.get("terrain_domain_id"))
        return _validate_source_urls(values, owner)

    @model_validator(mode="after")
    def validate_unique_ski_area_ids(self) -> "TerrainDomain":
        owner = f"terrain_domain_id {self.terrain_domain_id}"
        _reject_duplicate_ids(self.ski_area_ids, owner, "ski_area_ids")
        if len(set(self.ski_area_ids)) < 2:
            raise ValueError(
                f"{owner} ski_area_ids must contain at least two distinct IDs"
            )
        return self


class LiftPassProduct(_CatalogModel):
    lift_pass_product_id: CatalogId
    name: str
    validity_scope: LiftPassValidityScope
    available_from_stay_destination_ids: tuple[CatalogId, ...] = Field(min_length=1)
    default_for_stay_destination_ids: tuple[CatalogId, ...] = ()
    valid_ski_area_ids: tuple[CatalogId, ...] = ()
    terrain_domain_ids: tuple[CatalogId, ...] = ()
    validity_windows: tuple[CatalogSeasonWindow, ...] = ()
    external_validity_summary: str | None = None
    pass_accessible_terrain: AggregateTerrainMetrics | None = None
    prices: tuple[CatalogLiftPassPrice, ...] = ()

    @field_validator("pass_accessible_terrain", mode="before")
    @classmethod
    def validate_pass_accessible_terrain(
        cls, value: Any, info: ValidationInfo
    ) -> AggregateTerrainMetrics | None:
        if value is None:
            return None
        if isinstance(value, AggregateTerrainMetrics):
            value = value.model_dump()
        pass_id = info.data.get("lift_pass_product_id")
        owner_usable = _owner_id_is_usable(pass_id)
        return AggregateTerrainMetrics.model_validate(
            value,
            context={
                "source_owner": (
                    f"{_owner_label('lift_pass_product_id', pass_id)} "
                    "pass_accessible_terrain"
                ),
                "source_owner_usable": owner_usable,
            },
        )

    @field_validator("prices")
    @classmethod
    def validate_price_source_urls(
        cls, prices: tuple[CatalogLiftPassPrice, ...], info: ValidationInfo
    ) -> tuple[CatalogLiftPassPrice, ...]:
        owner = _owner_label(
            "lift_pass_product_id", info.data.get("lift_pass_product_id")
        )
        normalized_prices: list[CatalogLiftPassPrice] = []
        for index, price in enumerate(prices):
            if price.source_url is None:
                normalized_prices.append(price)
                continue
            try:
                source_url = validate_direct_external_http_url(price.source_url)
            except ValueError as error:
                raise ValueError(
                    f"{owner} prices[{index}].source_url {error}"
                ) from error
            normalized_prices.append(
                price.model_copy(update={"source_url": source_url})
            )
        return tuple(normalized_prices)

    @model_validator(mode="after")
    def validate_unique_relationship_ids(self) -> "LiftPassProduct":
        owner = f"lift_pass_product_id {self.lift_pass_product_id}"
        for field_name in (
            "available_from_stay_destination_ids",
            "default_for_stay_destination_ids",
            "valid_ski_area_ids",
            "terrain_domain_ids",
        ):
            _reject_duplicate_ids(getattr(self, field_name), owner, field_name)
        return self


class RentalDisplayFact(_CatalogModel):
    rental_display_fact_id: CatalogId
    stay_destination_id: CatalogId
    stay_base_id: CatalogId | None = None
    name: str
    price_range: str
    price_min: float
    price_max: float
    quality: Quality
    lift_distance: LiftDistance


def _validate_region_hierarchy(
    regions: tuple[SkiRegion, ...], region_ids: set[str]
) -> None:
    parent_by_id: dict[str, str | None] = {}
    for region in regions:
        parent_id = region.parent_ski_region_id
        if parent_id is not None and parent_id not in region_ids:
            raise ValueError(
                f"unknown parent_ski_region_id: {parent_id} "
                f"for ski_region_id: {region.ski_region_id}"
            )
        parent_by_id[region.ski_region_id] = parent_id

    for region in regions:
        path: list[str] = []
        path_positions: dict[str, int] = {}
        current_id: str | None = region.ski_region_id
        while current_id is not None:
            if current_id in path_positions:
                cycle = path[path_positions[current_id] :] + [current_id]
                raise ValueError(f"ski region parent cycle: {' -> '.join(cycle)}")
            path_positions[current_id] = len(path)
            path.append(current_id)
            current_id = parent_by_id[current_id]


def _validate_destination_regions(
    destinations: tuple[StayDestination, ...], regions_by_id: dict[str, SkiRegion]
) -> None:
    for destination in destinations:
        region_id = destination.trip_market_region_id
        region = regions_by_id.get(region_id)
        if region is None:
            raise ValueError(
                f"unknown trip_market_region_id: {region_id} "
                f"for stay_destination_id: {destination.stay_destination_id}"
            )
        if region.grouping_policy != "trip_market":
            raise ValueError(
                f"stay_destination_id {destination.stay_destination_id} must "
                f"reference a trip_market ski region: {region_id}"
            )


def _validate_base_destinations(
    stay_bases: tuple[StayBase, ...], destination_ids: set[str]
) -> None:
    for stay_base in stay_bases:
        destination_id = stay_base.stay_destination_id
        if destination_id not in destination_ids:
            raise ValueError(
                f"unknown stay_destination_id: {destination_id} "
                f"for stay_base_id: {stay_base.stay_base_id}"
            )


def _validate_access_graph(
    accesses: tuple[SkiAreaAccess, ...], base_ids: set[str], area_ids: set[str]
) -> None:
    access_pairs: set[tuple[str, str]] = set()
    connected_base_ids: set[str] = set()
    connected_area_ids: set[str] = set()
    for access in accesses:
        if access.stay_base_id not in base_ids:
            raise ValueError(
                f"unknown stay_base_id: {access.stay_base_id} "
                f"for ski_area_access_id: {access.ski_area_access_id}"
            )
        if access.ski_area_id not in area_ids:
            raise ValueError(
                f"unknown ski_area_id: {access.ski_area_id} "
                f"for ski_area_access_id: {access.ski_area_access_id}"
            )

        pair = (access.stay_base_id, access.ski_area_id)
        if pair in access_pairs:
            raise ValueError(
                "duplicate ski area access pair: "
                f"stay_base_id {access.stay_base_id}, "
                f"ski_area_id {access.ski_area_id}"
            )
        access_pairs.add(pair)
        connected_base_ids.add(access.stay_base_id)
        connected_area_ids.add(access.ski_area_id)

    inaccessible_base_ids = base_ids - connected_base_ids
    if inaccessible_base_ids:
        raise ValueError(
            f"stay_base_id has no ski area access: {sorted(inaccessible_base_ids)[0]}"
        )
    inaccessible_area_ids = area_ids - connected_area_ids
    if inaccessible_area_ids:
        raise ValueError(
            f"ski_area_id has no stay-base access: {sorted(inaccessible_area_ids)[0]}"
        )


def _validate_terrain_domains(
    terrain_domains: tuple[TerrainDomain, ...], area_ids: set[str]
) -> None:
    for domain in terrain_domains:
        for area_id in domain.ski_area_ids:
            if area_id not in area_ids:
                raise ValueError(
                    f"unknown ski_area_id: {area_id} "
                    f"for terrain_domain_id: {domain.terrain_domain_id}"
                )


def _validate_lift_passes(
    lift_passes: tuple[LiftPassProduct, ...],
    destination_ids: set[str],
    area_ids: set[str],
    terrain_domain_ids: set[str],
) -> None:
    default_pass_ids_by_destination: dict[str, list[str]] = {}
    for lift_pass in lift_passes:
        pass_id = lift_pass.lift_pass_product_id
        for destination_id in lift_pass.available_from_stay_destination_ids:
            if destination_id not in destination_ids:
                raise ValueError(
                    f"unknown available stay_destination_id: {destination_id} "
                    f"for lift_pass_product_id: {pass_id}"
                )
        for destination_id in lift_pass.default_for_stay_destination_ids:
            if destination_id not in destination_ids:
                raise ValueError(
                    f"unknown default stay_destination_id: {destination_id} "
                    f"for lift_pass_product_id: {pass_id}"
                )
        for area_id in lift_pass.valid_ski_area_ids:
            if area_id not in area_ids:
                raise ValueError(
                    f"unknown valid ski_area_id: {area_id} "
                    f"for lift_pass_product_id: {pass_id}"
                )
        for domain_id in lift_pass.terrain_domain_ids:
            if domain_id not in terrain_domain_ids:
                raise ValueError(
                    f"unknown terrain_domain_id: {domain_id} "
                    f"for lift_pass_product_id: {pass_id}"
                )

        if not lift_pass.valid_ski_area_ids and not lift_pass.terrain_domain_ids:
            raise ValueError(
                f"lift_pass_product_id {pass_id} must cover at least one "
                "ski area or terrain domain"
            )
        if lift_pass.validity_scope == "single_ski_area" and (
            len(lift_pass.valid_ski_area_ids) != 1 or bool(lift_pass.terrain_domain_ids)
        ):
            raise ValueError(
                f"single_ski_area lift_pass_product_id {pass_id} requires "
                "exactly one direct valid_ski_area_id and no terrain_domain_ids"
            )

        available_destination_ids = set(lift_pass.available_from_stay_destination_ids)
        for destination_id in lift_pass.default_for_stay_destination_ids:
            if destination_id not in available_destination_ids:
                raise ValueError(
                    f"default stay_destination_id {destination_id} is not "
                    f"available for lift_pass_product_id {pass_id}"
                )
        for destination_id in dict.fromkeys(lift_pass.default_for_stay_destination_ids):
            default_pass_ids_by_destination.setdefault(destination_id, []).append(
                pass_id
            )

    for destination_id, pass_ids in default_pass_ids_by_destination.items():
        if len(pass_ids) > 1:
            raise ValueError(
                f"stay_destination_id {destination_id} has multiple default "
                f"lift passes: {', '.join(pass_ids)}"
            )


def _validate_rentals(
    rentals: tuple[RentalDisplayFact, ...],
    destination_ids: set[str],
    bases_by_id: dict[str, StayBase],
) -> None:
    for rental in rentals:
        rental_id = rental.rental_display_fact_id
        destination_id = rental.stay_destination_id
        if destination_id not in destination_ids:
            raise ValueError(
                f"unknown stay_destination_id: {destination_id} "
                f"for rental_display_fact_id: {rental_id}"
            )
        if rental.stay_base_id is None:
            continue

        stay_base = bases_by_id.get(rental.stay_base_id)
        if stay_base is None:
            raise ValueError(
                f"unknown stay_base_id: {rental.stay_base_id} "
                f"for rental_display_fact_id: {rental_id}"
            )
        if stay_base.stay_destination_id != destination_id:
            raise ValueError(
                f"rental_display_fact_id {rental_id} references stay_base_id "
                f"{stay_base.stay_base_id} owned by stay_destination_id "
                f"{stay_base.stay_destination_id}, not {destination_id}"
            )


class CatalogSnapshot(_CatalogModel):
    schema_version: CatalogSchemaVersion
    ski_regions: tuple[SkiRegion, ...]
    stay_destinations: tuple[StayDestination, ...]
    stay_bases: tuple[StayBase, ...]
    ski_areas: tuple[SkiArea, ...]
    ski_area_access: tuple[SkiAreaAccess, ...]
    terrain_domains: tuple[TerrainDomain, ...]
    lift_pass_products: tuple[LiftPassProduct, ...]
    rental_display_facts: tuple[RentalDisplayFact, ...]

    @model_validator(mode="after")
    def validate_graph(self) -> "CatalogSnapshot":
        ski_region_ids = _unique_ids(self.ski_regions, "ski_region_id")
        destination_ids = _unique_ids(self.stay_destinations, "stay_destination_id")
        base_ids = _unique_ids(self.stay_bases, "stay_base_id")
        area_ids = _unique_ids(self.ski_areas, "ski_area_id")
        _unique_ids(self.ski_area_access, "ski_area_access_id")
        terrain_domain_ids = _unique_ids(self.terrain_domains, "terrain_domain_id")
        _unique_ids(self.lift_pass_products, "lift_pass_product_id")
        _unique_ids(self.rental_display_facts, "rental_display_fact_id")

        regions_by_id = {region.ski_region_id: region for region in self.ski_regions}
        bases_by_id = {
            stay_base.stay_base_id: stay_base for stay_base in self.stay_bases
        }
        _validate_region_hierarchy(self.ski_regions, ski_region_ids)
        _validate_destination_regions(self.stay_destinations, regions_by_id)
        _validate_base_destinations(self.stay_bases, destination_ids)
        _validate_access_graph(self.ski_area_access, base_ids, area_ids)
        _validate_terrain_domains(self.terrain_domains, area_ids)
        _validate_lift_passes(
            self.lift_pass_products,
            destination_ids,
            area_ids,
            terrain_domain_ids,
        )
        _validate_rentals(
            self.rental_display_facts,
            destination_ids,
            bases_by_id,
        )
        return self
