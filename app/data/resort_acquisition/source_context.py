from __future__ import annotations

from dataclasses import dataclass, field

from app.data.resort_acquisition.models import (
    OfficialUrlRole,
    RegionalDataIds,
    ResortSourceConfig,
)

MAX_EFFECTIVE_OFFICIAL_URLS_PER_ROLE = 3


@dataclass(frozen=True)
class DiscoveredOfficialUrl:
    role: OfficialUrlRole
    url: str
    confidence: float
    source: str


@dataclass
class SourceRunContext:
    configured: ResortSourceConfig
    discovered_official_urls: list[DiscoveredOfficialUrl] = field(default_factory=list)
    discovered_regional_ids: RegionalDataIds = field(default_factory=RegionalDataIds)

    @classmethod
    def from_config(cls, config: ResortSourceConfig) -> "SourceRunContext":
        return cls(configured=config)

    def add_discovered_official_url(
        self,
        discovered_url: DiscoveredOfficialUrl,
    ) -> None:
        if discovered_url.url.strip():
            self.discovered_official_urls.append(discovered_url)

    def add_discovered_regional_id(self, field_name: str, value: str) -> None:
        if not value.strip():
            return
        if getattr(self.configured.regional_data_ids, field_name) is not None:
            return
        if getattr(self.discovered_regional_ids, field_name) is not None:
            return
        self.discovered_regional_ids = self.discovered_regional_ids.model_copy(
            update={field_name: value}
        )

    def effective_regional_ids(self) -> RegionalDataIds:
        configured_ids = self.configured.regional_data_ids
        return configured_ids.model_copy(
            update={
                "opendatahub_ski_area_id": (
                    configured_ids.opendatahub_ski_area_id
                    or self.discovered_regional_ids.opendatahub_ski_area_id
                ),
                "osm_relation_id": (
                    configured_ids.osm_relation_id
                    or self.discovered_regional_ids.osm_relation_id
                ),
                "wikidata_id": (
                    configured_ids.wikidata_id
                    or self.discovered_regional_ids.wikidata_id
                ),
            }
        )

    def effective_official_urls_by_role(
        self,
        *,
        max_urls_per_role: int = MAX_EFFECTIVE_OFFICIAL_URLS_PER_ROLE,
    ) -> dict[OfficialUrlRole, list[str]]:
        urls_by_role: dict[OfficialUrlRole, list[str]] = {
            role: [url]
            for role, url in self.configured.official_urls.items()
            if url.strip()
        }
        seen_by_role = {role: set(urls) for role, urls in urls_by_role.items()}

        discovered_urls = sorted(
            self.discovered_official_urls,
            key=lambda discovered_url: discovered_url.confidence,
            reverse=True,
        )
        for discovered_url in discovered_urls:
            role_urls = urls_by_role.setdefault(discovered_url.role, [])
            seen_urls = seen_by_role.setdefault(discovered_url.role, set())
            if discovered_url.url in seen_urls:
                continue
            role_urls.append(discovered_url.url)
            seen_urls.add(discovered_url.url)

        return {
            role: urls[:max_urls_per_role]
            for role, urls in urls_by_role.items()
            if urls[:max_urls_per_role]
        }

    def effective_official_extraction_config(self) -> ResortSourceConfig:
        official_urls: dict[OfficialUrlRole, str] = {}
        provider_urls: dict[str, str] = dict(self.configured.provider_urls)

        for role, urls in self.effective_official_urls_by_role().items():
            official_urls[role] = urls[0]
            for index, url in enumerate(urls[1:], start=2):
                provider_urls[f"discovered:{role}:{index}"] = url

        return self.configured.model_copy(
            update={
                "official_urls": official_urls,
                "provider_urls": provider_urls,
                "regional_data_ids": self.effective_regional_ids(),
            }
        )
