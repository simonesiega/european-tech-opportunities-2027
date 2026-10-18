"""Conservative European location detection and display normalization."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from opportunities.utils.text import clean_text, contains_normalized_phrase, normalized_key


class _Country(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    aliases: tuple[str, ...]


class _Geography(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    countries: dict[str, _Country]
    cities: dict[str, str]
    modifiers: tuple[str, ...]
    regions: tuple[str, ...]
    non_european_markers: tuple[str, ...] = Field(alias="nonEuropeanMarkers")


# The website uses this same vocabulary to label countries without changing job data.
_GEOGRAPHY = _Geography.model_validate_json(
    Path(__file__).with_name("geography.json").read_text(encoding="utf-8")
)
EUROPEAN_COUNTRY_CODES = frozenset(_GEOGRAPHY.countries)
_COUNTRY_ALIASES = {
    normalized_key(alias): code
    for code, country in _GEOGRAPHY.countries.items()
    for alias in (country.name, *country.aliases)
}
_MODIFIERS_RE = re.compile(r"\b(?:" + "|".join(_GEOGRAPHY.modifiers) + r")\b")
_COMPONENTS_RE = re.compile(r",|[()|]|\s+[\u2014\u2013-]\s+")


def _geographic_key(value: str) -> str:
    """Remove known modifiers without erasing unsupported geographic words."""
    decomposed = unicodedata.normalize("NFKD", clean_text(value))
    unaccented = "".join(char for char in decomposed if not unicodedata.combining(char))
    key = re.sub(r"[\W_]+", " ", unaccented.lower())
    return clean_text(_MODIFIERS_RE.sub(" ", key))


_REGION_KEYS = frozenset(map(_geographic_key, _GEOGRAPHY.regions))


@dataclass(frozen=True, slots=True)
class LocationResult:
    """Normalized locations and the evidence for European eligibility."""

    locations: list[str]
    country_codes: list[str]
    europe_signal: bool
    non_europe_signal: bool


def normalize_locations(values: list[str]) -> LocationResult:
    """Normalize independent locations and determine European eligibility."""
    locations: list[str] = []
    codes: set[str] = set()
    europe_signal = False
    non_europe_signal = False

    for raw_value in (entry for value in values for entry in value.split(";")):
        location = _normalize_display_location(raw_value)
        if location and location not in locations:
            locations.append(location)
        key = normalized_key(raw_value)
        without_workplace = re.sub(
            r"\b(?:remote|hybrid|on[- ]?site)\b", "", raw_value, flags=re.IGNORECASE
        )
        uppercase_codes = set(re.findall(r"(?<![A-Za-z])([A-Z]{2})(?![A-Za-z])", without_workplace))
        # Unknown country/state codes cannot be treated as European city qualifiers.
        unknown_codes = {
            code
            for code in uppercase_codes - EUROPEAN_COUNTRY_CODES - {"EU"}
            if code.lower() not in _COUNTRY_ALIASES
        }
        has_non_european_marker = bool(unknown_codes) or any(
            contains_normalized_phrase(key, marker) for marker in _GEOGRAPHY.non_european_markers
        )
        components = [
            component
            for value in _COMPONENTS_RE.split(raw_value)
            if (component := _geographic_key(value))
        ]
        named_countries = {
            _COUNTRY_ALIASES[component] for component in components if component in _COUNTRY_ALIASES
        }
        codes.update(named_countries)
        if not named_countries and not has_non_european_marker:
            # A country code must be the final geographic component, not a US state
            # before an unknown country. Unrecognized qualifiers also prevent city fallback.
            terminal_code = components[-1].upper() if components else ""
            if terminal_code in uppercase_codes & EUROPEAN_COUNTRY_CODES:
                codes.add(terminal_code)
            elif city_country := _GEOGRAPHY.cities.get(_geographic_key(raw_value)):
                codes.add(city_country)
        if any(component in _REGION_KEYS for component in components):
            europe_signal = True
        non_europe_signal |= has_non_european_marker

    if codes:
        europe_signal = True
    return LocationResult(
        locations=locations,
        country_codes=sorted(codes),
        europe_signal=europe_signal,
        non_europe_signal=non_europe_signal,
    )


def _normalize_display_location(value: str) -> str:
    """Normalize spacing and punctuation in a displayed location."""
    cleaned = clean_text(value).strip(" ,-|")
    cleaned = re.sub(r"\bUK Remote\b", "Remote — United Kingdom", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bU\.?K\.?(?=\b|$)", "United Kingdom", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bRemote,? Europe\b", "Remote — Europe", cleaned, flags=re.IGNORECASE)
    return clean_text(cleaned)
