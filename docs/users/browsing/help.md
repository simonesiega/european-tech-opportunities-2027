# Questions and troubleshooting

[← User guide](../README.md) · [Directory](directory.md) · [Local lists](lists.md) · [Downloads](../data/data.md) · [API](../data/api.md)

Find answers about listing eligibility, dates, local lists, and downloads. These checks do not require installing or running the project.

## Which roles are included?

Technology internships and New Grad roles with clear early-career title evidence and European location evidence. Listings need an explicit 2027 opportunity cycle, or no conflicting cycle and eligible posting evidence from May 1, 2026 onward. Senior or unrelated roles and ambiguous evidence are excluded. Graduation-year eligibility alone does not establish an internship cycle.

The project is not a complete index of every employer or country. A valid listing can be missed by bounded discovery. [Suggest a missing listing](https://github.com/simonesiega/european-tech-opportunities-2027/issues/new?template=add-position.yml) with its public URL and relevant evidence. Suggestions are reviewed, not automatically published.

## Is every listing still available?

Availability can change between checks. The directory uses conservative evidence rather than assuming that a role has closed when it disappears from search results. Open the original listing to verify before applying. The site does not guarantee deadlines, eligibility, sponsorship, compensation, or remote-work arrangements.

## Why do dates look unexpected?

**First seen** can reflect approximate posting age, a reviewed posting timestamp, or the project's first observation. It does not change on later observations. A newly added role may therefore have an older date. **Start date** is separate and only appears when stated clearly. The footer shows the latest successful collection, not the freshness of every row.

## No roles match my search

Choose **Reset** and **View all opportunities**. Check your hidden list if a specific role is missing. Add filters one at a time. If the unfiltered directory is empty, try again later; do not assume your saved list is a backup of removed jobs.

## My saved or applied list disappeared

Lists belong to the browser profile and website address where you saved them. A different device, private window, cleared site data, blocked storage, or a closed/removed listing can explain missing entries. There is no server copy to restore. See [what persists](lists.md#what-persists).

## I cannot find the row actions on my phone

Scroll the table horizontally to the **Your list** column. Keyboard users can Tab to the bookmark icon, applied check icon, and **More actions** button. Enter or Space activates a button; Escape closes the menu.

## The new-role count differs from the filtered results

The count covers all open roles you have not hidden with a **First seen** date after your previous visit. The current filters may match fewer. Reloading during the same visit keeps the same previous-visit time for comparison; see [what is new](lists.md#see-what-is-new).

## A download or API request failed

- Retry a missing download later. The site does not substitute a stale file when the current export is unavailable.
- For API `400`, check [query parameters](../data/api.md#query-parameters), spelling, encoding, duplicate keys, and bounds.
- For API `503`, try again later; do not treat an unavailable dataset as an empty successful response.
- If metadata hashes differ from downloads, fetch all three again: a publication may have occurred between requests.
- CSV and JSON contain all open listings, not your filtered or saved view.

## Does the project track my applications?

No. Marking a role applied saves a reminder in your browser, not an application record on the server. The public site uses aggregate usage analytics and ordinary hosting and security services. The [privacy notice](../../../PRIVACY.md) explains providers, storage, retention, and your choices. Blocking analytics does not prevent normal use.

## Report a problem

[Open a bug report](https://github.com/simonesiega/european-tech-opportunities-2027/issues/new?template=bug-report.yml) with the page URL, browser, steps, and expected result. Remove private information from screenshots. Never post credentials, browser storage, application documents, or database files. Use the [security policy](../../../SECURITY.md) for private vulnerability reports.

Operating the service rather than browsing it? Use [maintainer troubleshooting](../../maintainers/operations/troubleshooting.md).
