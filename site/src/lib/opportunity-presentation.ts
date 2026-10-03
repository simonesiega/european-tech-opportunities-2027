export const ALL_FILTER_VALUE = "all";

const OPPORTUNITY_DATE_FORMATTER = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "short",
  year: "numeric",
  timeZone: "UTC",
});

export function getCountries(location: string): string[] {
  return [
    ...new Set(
      location
        .split(";")
        .map((item) => item.split(",").at(-1)?.trim() || item.trim())
        .filter(Boolean)
    ),
  ];
}

export function formatCategory(category: string): string {
  return category
    .split("-")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

export function getCategoryHue(category: string): number {
  return [...category].reduce((hash, character) => (hash * 17 + character.charCodeAt(0)) % 360, 0);
}

export function getEmploymentTypeHue(employmentType: string): number {
  const hues: Record<string, number> = {
    internship: 265,
    "new-grad": 145,
  };
  return hues[employmentType] ?? 210;
}

export function parseOpportunityTimestamp(value: string): number {
  try {
    return Date.parse(normalizeOpportunityTimestamp(value));
  } catch {
    return NaN;
  }
}

// SQLite stores naive UTC values; API and HTML timestamps must be explicit UTC.
// Validate before using Date, which otherwise normalizes impossible calendar dates.
export function normalizeOpportunityTimestamp(value: string): string {
  const match =
    /^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):(\d{2})(?:\.(\d{1,6}))?(Z|([+-])(\d{2}):(\d{2}))?$/.exec(
      value
    );
  if (!match) throw new Error("Invalid opportunity timestamp");

  const [
    ,
    yearText,
    monthText,
    dayText,
    hourText,
    minuteText,
    secondText,
    fractionText,
    ,
    sign,
    offsetHourText,
    offsetMinuteText,
  ] = match;
  const year = Number(yearText);
  const month = Number(monthText);
  const day = Number(dayText);
  const hour = Number(hourText);
  const minute = Number(minuteText);
  const second = Number(secondText);
  const offsetHour = Number(offsetHourText ?? 0);
  const offsetMinute = Number(offsetMinuteText ?? 0);
  const leapYear = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
  const daysInMonth = [31, leapYear ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  if (
    year < 1 ||
    month < 1 ||
    month > 12 ||
    day < 1 ||
    day > daysInMonth[month - 1]! ||
    hour > 23 ||
    minute > 59 ||
    second > 59 ||
    offsetHour > 23 ||
    offsetMinute > 59
  ) {
    throw new Error("Invalid opportunity timestamp");
  }

  const timestamp = new Date(0);
  timestamp.setUTCFullYear(year, month - 1, day);
  timestamp.setUTCHours(hour, minute, second, 0);
  const offset = (offsetHour * 60 + offsetMinute) * (sign === "+" ? 1 : -1);
  timestamp.setTime(timestamp.getTime() - offset * 60_000);
  if (timestamp.getUTCFullYear() < 1 || timestamp.getUTCFullYear() > 9999) {
    throw new Error("Invalid opportunity timestamp");
  }
  const normalized = timestamp.toISOString();
  // Date keeps only milliseconds; preserve the original microseconds for the public contract.
  const fraction = (fractionText ?? "").padEnd(6, "0");
  return `${normalized.slice(0, 19)}.${fraction}+00:00`;
}

export function formatOpportunityDate(value: string): string {
  return OPPORTUNITY_DATE_FORMATTER.format(new Date(parseOpportunityTimestamp(value)));
}
