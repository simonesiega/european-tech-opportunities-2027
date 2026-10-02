# Find and share opportunities

[← User guide](../README.md) · [Your local lists](lists.md) · [Get help](help.md) · [Open the directory](https://techopportunities.eu/)

The directory shows currently open, validated technology internships and New Grad roles across Europe. It favors clearly relevant listings over complete coverage. Always check requirements and current availability on the original listing.

## Find a role

- **Search** matches company, role, location, category, industries, and employment type. It ignores letter case. Press **Ctrl+K** or **⌘K** to focus the search box.
- **Location** selects a country from the listed locations. A role with more than one location can match more than one country.
- **Company** and **Category** narrow the results further.
- **Employment type** selects **Internship** or **New Grad**.
- **First seen** limits results to the last 24 hours, 7 days, or 30 days.

Filters combine: a role must match all your selections. The **open roles** badge always shows the directory's full total, including roles you have hidden. The result count beside pagination reflects your current filters and local list. If nothing matches, remove one filter or choose **Reset**. This clears search and filters, but keeps your sorting and rows-per-page choice. If you are browsing a local list, choose **View all opportunities** to leave that list.

## Browse the results

The default order is newest first, with 10 rows per page. Select **Company**, **Role**, **Location**, or **First seen** in the table header to sort. Select the same heading again to reverse the order. Choose 10, 20, 30, 50, or 100 under **Rows**, and use the previous/next arrows to browse.

Open the role title or the arrow at the start of a row to visit its original LinkedIn listing. Saving or marking a role applied does not submit an application. See [your local lists](lists.md).

On a small screen, scroll the table sideways to reach all columns and row actions. You can also move between controls with Tab; a visible outline shows which control is selected. The theme button switches between light and dark; your browser remembers the choice.

## Understand the fields

| Field | What it means |
|---|---|
| Company / Role / Location | Information from the original listing; a missing location may be taken from its search result |
| New | Whether the role is newer than your previous visit; [how this works](lists.md#see-what-is-new) |
| Category | The project's technology grouping, not a guarantee about every duty |
| Industries | Structured source metadata; `Not specified` means it was not available |
| Employment type | Internship or New Grad, based on explicit title evidence |
| Start date | A stated month or season and year, when available; `—` means unknown |
| First seen | A date set when the role is added and kept unchanged; it may use the source's approximate posting age, a reviewed posting date, or the project's first observation |

**First seen is not an application deadline.** The site does not guarantee compensation, sponsorship, remote eligibility, or suitability for your background. The collection date in the footer describes the latest successful collection, not the last check of every individual listing.

## Share or bookmark a view

Copy the address bar after setting your filters. Search, filters, sort, rows per page, and page number are included. Browser Back and Forward restore earlier views; typing a search does not add one history entry per character.

Example: [internships in Germany](https://techopportunities.eu/?country=Germany&type=internship).

Your saved/applied/hidden lists and previous-visit time are **not** in the URL. Someone opening your link sees the public filters, not your private list. Changing filters or sort returns to page one. Unsupported URL values are ignored or safely constrained.

Building an application? Use the [API](../data/api.md), which measures recency against the published dataset so the same data gives the same results. The website measures recency when you load the directory.

## Take the listings with you

**Download CSV** and **Download JSON** give you the complete public dataset, not just your current filtered or saved view. See the [download guide](../data/data.md) for fields, date limitations, and integrity checks.

## Subscribe to new opportunities

Subscribe with any RSS or Atom reader—no account, email address, or notification signup is needed:

- RSS 2.0: [https://techopportunities.eu/feed.xml](https://techopportunities.eu/feed.xml)
- Atom 1.0: [https://techopportunities.eu/atom.xml](https://techopportunities.eu/atom.xml)

Each feed contains up to 50 **currently open** opportunities, newest **First seen** date first. That date stays unchanged after a role is added and may reflect an approximate source posting date rather than the exact discovery time. Closed listings and listings that fall outside the latest 50 are no longer included.

Add any of these exact filters to either feed URL; filters combine:

| Parameter | Values |
|---|---|
| `type` | `internship` or `new-grad` |
| `country` | Exact country name from the listing location |
| `category` | Exact technology-category slug |

For example, [software internships in Ireland](https://techopportunities.eu/feed.xml?type=internship&country=Ireland&category=software-engineering) uses `/feed.xml?type=internship&country=Ireland&category=software-engineering`. Unknown/repeated parameters or invalid values are rejected; a valid filter with no matches produces an empty feed. These feeds use public opportunity data only: browser-saved, applied, and hidden lists are not included.
