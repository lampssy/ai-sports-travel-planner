"""Typed Search V4 factor evaluation contracts."""

from app.domain.search_factors.models import FactorEvaluation
from app.domain.search_factors.registry import FactorRegistry, FactorRegistryError


def build_static_factor_registry() -> FactorRegistry:
    from app.domain.search_factors.static import (
        build_static_factor_registry as build,
    )

    return build()


def build_weather_factor_registry() -> FactorRegistry:
    from app.domain.search_factors.weather import (
        build_weather_factor_registry as build,
    )

    return build()


def build_factor_registry() -> FactorRegistry:
    static = build_static_factor_registry()
    weather = build_weather_factor_registry()
    return FactorRegistry(
        (
            *(static.get(factor_id) for factor_id in static.factor_ids),
            *(weather.get(factor_id) for factor_id in weather.factor_ids),
        )
    )


__all__ = (
    "FactorEvaluation",
    "FactorRegistry",
    "FactorRegistryError",
    "build_factor_registry",
    "build_static_factor_registry",
    "build_weather_factor_registry",
)
