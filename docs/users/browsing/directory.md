# Find and share opportunities

[← User guide](../README.md) · [Your local lists](lists.md) · [Get help](help.md) · [Open the directory](https://techopportunities.eu/)

Find technology internships and **New Grad** roles (graduate and entry-level positions) across Europe for the 2027 hiring cycle. Each listing has passed the project's eligibility checks and is marked open by the project. Availability can change between checks. Always confirm requirements and availability on the original listing.

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
| Industries | The industry information provided by the original listing; `Not specified` means it was not available |
| Employment type | Internship or New Grad, based on wording in the role title |
| Start date | A stated month or season and year, when available; `—` means unknown |
| First seen | A date set when the role is added and kept unchanged; it may come from the source's approximate posting age, a posting date checked by a maintainer, or when the project first found the role |

**First seen is not an application deadline.** The site does not guarantee compensation, sponsorship, remote eligibility, or suitability for your background. The collection date in the footer describes the latest successful collection, not the last check of every individual listing.

## Share or bookmark a view

Copy the address bar after setting your filters. Search, filters, sort, rows per page, and page number are included. Browser Back and Forward restore earlier views; typing a search does not add one history entry per character.

Example: [internships in Germany](https://techopportunities.eu/?country=Germany&type=internship).

Your saved/applied/hidden lists and previous-visit time are **not** in the URL. Someone opening your link sees the public filters, not your private list. Changing filters or sort returns to page one. If the URL contains an unsupported filter or page value, the site ignores it or uses a supported value.

Building an application? Use the [API](../data/api.md), which measures recency against the published dataset so the same data gives the same results. The website measures recency when you load the directory.

## Take the listings with you

**Download CSV** and **Download JSON** give you the complete public dataset, not just your current filtered or saved view. See the [download guide](../data/data.md) for fields, date limitations, and integrity checks.

## Subscribe to new opportunities

Use a feed-reader app to follow recent roles without repeatedly checking the directory. In your reader, choose its add-feed or subscribe action and paste one of these URLs. The directory itself requires no account, email address, or notification signup:

- RSS 2.0: [https://techopportunities.eu/feed.xml](https://techopportunities.eu/feed.xml)
- Atom 1.0: [https://techopportunities.eu/atom.xml](https://techopportunities.eu/atom.xml)

Each feed contains up to 50 **currently open** opportunities, newest **First seen** date first. That date stays unchanged after a role is added and may reflect an approximate source posting date rather than the exact discovery time. Closed listings and listings that fall outside the latest 50 are no longer included.

To follow only some roles, use the filtered example below. If you want to build your own feed URL, add these exact parameters; filters combine:

| Parameter | Values |
|---|---|
| `type` | `internship` or `new-grad` |
| `country` | Exact country name from the listing location |
| `category` | Exact category identifier, such as `software-engineering` |

For example, paste this [feed for software internships in Ireland](https://techopportunities.eu/feed.xml?type=internship&country=Ireland&category=software-engineering) into your reader. The same filters work with the Atom URL. If a feed fails to load, check the parameter names and values and use each parameter only once. A valid filter with no matches produces an empty feed. These feeds use public opportunity data only: browser-saved, applied, and hidden lists are not included.
