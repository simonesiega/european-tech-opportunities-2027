"""Conservative European location and workplace normalization."""

from __future__ import annotations

import re
from dataclasses import dataclass

from internships.utils.text import clean_text, normalized_key

EUROPEAN_COUNTRY_CODES = frozenset(
    {
        "AD",
        "AL",
        "AT",
        "BA",
        "BE",
        "BG",
        "CH",
        "CY",
        "CZ",
        "DE",
        "DK",
        "EE",
        "ES",
        "FI",
        "FR",
        "GB",
        "GR",
        "HR",
        "HU",
        "IE",
        "IS",
        "IT",
        "LI",
        "LT",
        "LU",
        "LV",
        "MC",
        "MD",
        "ME",
        "MK",
        "MT",
        "NL",
        "NO",
        "PL",
        "PT",
        "RO",
        "RS",
        "SE",
        "SI",
        "SK",
        "SM",
        "UA",
        "VA",
        "XK",
    }
)

_COUNTRY_ALIASES: dict[str, str] = {
    "albania": "AL",
    "andorra": "AD",
    "austria": "AT",
    "belgium": "BE",
    "bosnia": "BA",
    "bosnia and herzegovina": "BA",
    "bulgaria": "BG",
    "croatia": "HR",
    "cyprus": "CY",
    "czech republic": "CZ",
    "czechia": "CZ",
    "denmark": "DK",
    "england": "GB",
    "estonia": "EE",
    "finland": "FI",
    "france": "FR",
    "germany": "DE",
    "greece": "GR",
    "hungary": "HU",
    "iceland": "IS",
    "ireland": "IE",
    "italy": "IT",
    "kosovo": "XK",
    "latvia": "LV",
    "liechtenstein": "LI",
    "lithuania": "LT",
    "luxembourg": "LU",
    "malta": "MT",
    "moldova": "MD",
    "monaco": "MC",
    "montenegro": "ME",
    "netherlands": "NL",
    "north macedonia": "MK",
    "northern ireland": "GB",
    "norway": "NO",
    "poland": "PL",
    "portugal": "PT",
    "romania": "RO",
    "san marino": "SM",
    "scotland": "GB",
    "serbia": "RS",
    "slovakia": "SK",
    "slovenia": "SI",
    "spain": "ES",
    "sweden": "SE",
    "switzerland": "CH",
    "uk": "GB",
    "u k": "GB",
    "united kingdom": "GB",
    "ukraine": "UA",
    "vatican city": "VA",
    "wales": "GB",
}

_CITY_COUNTRIES: dict[str, str] = {
    "amsterdam": "NL",
    "athens": "GR",
    "barcelona": "ES",
    "belgrade": "RS",
    "berlin": "DE",
    "bratislava": "SK",
    "brussels": "BE",
    "bucharest": "RO",
    "budapest": "HU",
    "copenhagen": "DK",
    "dublin": "IE",
    "edinburgh": "GB",
    "helsinki": "FI",
    "krakow": "PL",
    "lisbon": "PT",
    "ljubljana": "SI",
    "london": "GB",
    "luxembourg": "LU",
    "madrid": "ES",
    "manchester": "GB",
    "milan": "IT",
    "munich": "DE",
    "oslo": "NO",
    "paris": "FR",
    "prague": "CZ",
    "riga": "LV",
    "rome": "IT",
    "sofia": "BG",
    "stockholm": "SE",
    "tallinn": "EE",
    "vilnius": "LT",
    "vienna": "AT",
    "warsaw": "PL",
    "zagreb": "HR",
    "zurich": "CH",
}

_NON_EUROPEAN_MARKERS = frozenset(
    {
        "australia",
        "austin",
        "brazil",
        "canada",
        "india",
        "new york",
        "san francisco",
        "seattle",
        "singapore",
        "united states",
        "us remote",
        "usa",
    }
)


@dataclass(frozen=True, slots=True)
class LocationResult:
    """Hold normalized location text and its Europe decision."""

    locations: list[str]
    country_codes: list[str]
    europe_signal: bool
    non_europe_signal: bool


def normalize_locations(values: list[str]) -> LocationResult:
    """Normalize locations and determine European eligibility."""
    locations: list[str] = []
    codes: set[str] = set()
    europe_signal = False
    non_europe_signal = False

    for raw_value in values:
        location = _normalize_display_location(raw_value)
        if location and location not in locations:
            locations.append(location)
        key = normalized_key(raw_value)
        for alias, country_code in _COUNTRY_ALIASES.items():
            if _contains_phrase(key, alias):
                codes.add(country_code)
        for city, country_code in _CITY_COUNTRIES.items():
            if _contains_phrase(key, city):
                codes.add(country_code)
        # Two-letter codes are recognized only when the source writes uppercase ISO
        # tokens. Lowercased matching would mistake common words such as "at" or "it"
        # for Austria and Italy.
        for code in re.findall(r"(?<![A-Za-z])([A-Z]{2})(?![A-Za-z])", raw_value):
            if code in EUROPEAN_COUNTRY_CODES:
                codes.add(code)
        if any(marker in key for marker in ("europe", "european union", "emea")):
            europe_signal = True
        if any(_contains_phrase(key, marker) for marker in _NON_EUROPEAN_MARKERS):
            non_europe_signal = True

    if codes & EUROPEAN_COUNTRY_CODES:
        europe_signal = True
    return LocationResult(
        locations=locations,
        country_codes=sorted(codes),
        europe_signal=europe_signal,
        non_europe_signal=non_europe_signal,
    )


def _contains_phrase(text: str, phrase: str) -> bool:
    """Check whether normalized text contains a complete phrase."""
    return bool(re.search(rf"(?:^|\s){re.escape(phrase)}(?:$|\s)", text))


def _normalize_display_location(value: str) -> str:
    """Normalize spacing and punctuation in a displayed location."""
    cleaned = clean_text(value).strip(" ,-|")
    cleaned = re.sub(r"\bUK Remote\b", "Remote — United Kingdom", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bU\.?K\.?(?=\b|$)", "United Kingdom", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bRemote,? Europe\b", "Remote — Europe", cleaned, flags=re.IGNORECASE)
    return clean_text(cleaned)
