# Find and share opportunities

[← User guide](../README.md) · [Your local lists](lists.md) · [Get help](help.md) · [Open the directory](https://techopportunities.eu/)

The directory shows currently open, validated technology internships and New Grad roles across Europe. It favors clearly relevant listings over complete coverage. Always check requirements and current availability on the original listing.

## Find a role

- **Search** matches company, role, location, category, industries, and employment type. It ignores letter case. Press **Ctrl+K** or **⌘K** to focus the search box.
- **Location** selects a country from the listed locations. A role with more than one location can match more than one country.
- **Company** and **Category** narrow the results further.
- **Employment type** selects Internship or New Grad.
- **First seen** limits results to the last 24 hours, 7 days, or 30 days.

Filters combine: a role must match all your selections. The open-role count reflects the current view. If nothing matches, remove one filter or choose **Reset**. This clears search and filters, but keeps your sorting and rows-per-page choice. If you are browsing a local list, choose **View all opportunities** to leave that list.

## Browse the results

The default order is newest first, with 10 rows per page. Select **Company**, **Role**, **Location**, or **First seen** in the table header to sort. Select the same heading again to reverse the order. Choose 10, 20, 30, 50, or 100 under **Rows**, and use the previous/next arrows to browse.

Open the role title or the arrow at the start of a row to visit its original LinkedIn listing. Saving or marking a role applied does not submit an application. See [your local lists](lists.md).

On a small screen, scroll the table sideways to reach all columns and row actions. Controls have keyboard labels and visible focus. The theme button switches between light and dark; your browser remembers the choice.

## Understand the fields

| Field | What it means |
|---|---|
| Company / Role / Location | Normalized information from the listing; missing detail location can use its search-card location |
| New | Whether the role is newer than your previous visit; [how this works](lists.md#see-what-is-new) |
| Category | The project's technology grouping, not a guarantee about every duty |
| Industries | Structured source metadata; `Not specified` means it was not available |
| Employment type | Internship or New Grad, based on explicit title evidence |
| Start date | A stated month or season and year, when available; `—` means unknown |
| First seen | An immutable date that may use approximate source posting age, a reviewed posting date, or the project's first observation |

**First seen is not an application deadline.** The site does not guarantee compensation, sponsorship, remote eligibility, or suitability for your background. The collection date in the footer describes the latest successful collection, not the last check of every individual listing.

## Share or bookmark a view

Copy the address bar after setting your filters. Search, filters, sort, rows per page, and page number are included. Browser Back and Forward restore earlier views; typing a search does not add one history entry per character.

Example: [internships in Germany](https://techopportunities.eu/?country=Germany&type=internship).

Your saved/applied/hidden lists and previous-visit time are **not** in the URL. Someone opening your link sees the public filters, not your private list. Changing filters or sort returns to page one. Unsupported URL values are ignored or safely constrained.

For a reproducible programmatic query, use the [API](../data/api.md); its recency window is snapshot-relative, unlike the website's request-time window.

## Take the listings with you

**Download CSV** and **Download JSON** give you the complete public dataset, not just your current filtered or saved view. See the [download guide](../data/data.md) for fields, date limitations, and integrity checks.
