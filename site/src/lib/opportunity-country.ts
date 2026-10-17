import geography from "../../../src/opportunities/normalization/geography.json";

const countries = new Map<string, {name: string; aliases: readonly string[]}>(
  Object.entries(geography.countries)
);
const cities = new Map(Object.entries(geography.cities));
const aliases = new Map(
  [...countries].flatMap(([code, country]) =>
    [country.name, ...country.aliases].map((name) => [normalizedKey(name), code] as const)
  )
);
const modifiers = new RegExp(`\\b(?:${geography.modifiers.join("|")})\\b`, "g");
const regions = new Set(geography.regions.map(geographicKey));

function normalizedKey(value: string): string {
  // Stripping non-Latin words could invent city-only evidence from a qualified location.
  return value
    .normalize("NFKD")
    .replace(/\p{M}/gu, "")
    .toLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, " ")
    .trim();
}

function geographicKey(value: string): string {
  return normalizedKey(value).replace(modifiers, " ").replace(/\s+/g, " ").trim();
}

export function normalizeCountryFilter(value: string): string {
  // A filter selects one country; independent locations must not be silently discarded.
  if (value.includes(";")) return value;
  const countries = getCountries(value);
  return countries.length === 1 ? countries[0]! : value;
}

// Country labels share the collector's vocabulary, not its acceptance decisions.
export function getCountries(location: string): string[] {
  const names = new Set<string>();
  for (const entry of location.split(";")) {
    const key = normalizedKey(entry);
    const withoutWorkplace = entry.replace(/\b(?:remote|hybrid|on[- ]?site)\b/gi, "");
    const codes = new Set(withoutWorkplace.match(/(?<![A-Za-z])[A-Z]{2}(?![A-Za-z])/g) ?? []);
    const nonEuropean =
      [...codes].some(
        (code) => !countries.has(code) && code !== "EU" && !aliases.has(code.toLowerCase())
      ) || geography.nonEuropeanMarkers.some((marker) => ` ${key} `.includes(` ${marker} `));
    const components = entry
      .split(/,|[()|]|\s+[—–-]\s+/)
      .map(geographicKey)
      .filter(Boolean);
    const named = components.flatMap((component) => {
      const code = aliases.get(component);
      return code ? [code] : [];
    });
    for (const code of named) names.add(countries.get(code)!.name);
    if (named.length === 0 && !nonEuropean) {
      const terminal = components.at(-1)?.toUpperCase() ?? "";
      const code =
        codes.has(terminal) && countries.has(terminal)
          ? terminal
          : cities.get(geographicKey(entry));
      if (code) names.add(countries.get(code)!.name);
      else if (components.some((component) => regions.has(component))) names.add("Europe");
    }
  }
  return [...names];
}
