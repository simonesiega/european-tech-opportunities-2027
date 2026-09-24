"use client";

import type {MouseEvent} from "react";
import {
  flexRender,
  getCoreRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
  type SortingState,
} from "@tanstack/react-table";
import {ChevronDown, ChevronLeft, ChevronRight} from "lucide-react";
import {opportunityColumns} from "@/components/opportunities/opportunity-columns";
import {Button} from "@/components/ui/button";
import {Table, TableBody, TableCell, TableHead, TableHeader, TableRow} from "@/components/ui/table";
import {cn} from "@/lib/cn";
import {
  DIRECTORY_PAGE_SIZES,
  type DirectoryPageSize,
  type DirectorySort,
  type DirectoryView,
} from "@/types/directory";
import type {Opportunity} from "@/types/opportunity";

const SORTING_BY_DIRECTORY_SORT: Record<DirectorySort, SortingState[number]> = {
  "company-asc": {id: "company", desc: false},
  "company-desc": {id: "company", desc: true},
  "role-asc": {id: "title", desc: false},
  "role-desc": {id: "title", desc: true},
  "location-asc": {id: "location", desc: false},
  "location-desc": {id: "location", desc: true},
  "first-seen-asc": {id: "firstSeenAt", desc: false},
  "first-seen-desc": {id: "firstSeenAt", desc: true},
};

type OpportunityListProps = {
  opportunities: Opportunity[];
  view: DirectoryView;
  pageHref: (page: number) => string;
  hasActiveFilters: boolean;
  onSortChange: (sort: DirectorySort) => void;
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: DirectoryPageSize) => void;
  onReset: () => void;
};

export function OpportunityList({
  opportunities,
  view,
  pageHref,
  hasActiveFilters,
  onSortChange,
  onPageChange,
  onPageSizeChange,
  onReset,
}: OpportunityListProps) {
  const sorting: SortingState = [SORTING_BY_DIRECTORY_SORT[view.sort]];
  const pagination = {pageIndex: view.page - 1, pageSize: view.pageSize};
  const paginationLinkClassName =
    "inline-flex size-[34px] items-center justify-center rounded-md border border-[var(--border)] bg-[var(--surface)] text-[var(--text)] shadow-[0_1px_2px_rgb(0_0_0/3%)] transition-colors duration-150 hover:bg-[var(--surface-hover)] [&_svg]:size-[15px]";

  function followPageLink(event: MouseEvent<HTMLAnchorElement>, page: number) {
    if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
      return;
    }
    event.preventDefault();
    onPageChange(page);
  }

  // TanStack Table intentionally returns non-memoizable functions as part of its API.
  // eslint-disable-next-line react-hooks/incompatible-library
  const table = useReactTable({
    data: opportunities,
    columns: opportunityColumns,
    state: {sorting, pagination},
    onSortingChange: (updater) => {
      const nextSorting = typeof updater === "function" ? updater(sorting) : updater;
      onSortChange(toDirectorySort(nextSorting));
    },
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    autoResetPageIndex: false,
  });

  return (
    <div className="mt-4">
      <div className="overflow-hidden rounded-lg border border-[var(--border)] bg-[var(--surface)] shadow-[0_1px_2px_rgb(0_0_0/3%)]">
        <Table aria-label="Open opportunities">
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header, index) => {
                  const sortDirection = header.column.getIsSorted();
                  return (
                    <TableHead
                      key={header.id}
                      aria-sort={
                        sortDirection === "asc"
                          ? "ascending"
                          : sortDirection === "desc"
                            ? "descending"
                            : undefined
                      }
                      className={cn(
                        index === 0 && "w-7 pr-0 pl-1",
                        index === 1 &&
                          "w-[8%] pl-1.5 [&_button]:relative [&_button]:-left-1.5 [&_button]:p-0",
                        index === 2 && "w-[26%]",
                        index === 3 && "w-[11%]",
                        index === 4 && "w-[calc(11%+8px)]",
                        index === 5 && "w-[9%]",
                        index === 6 && "w-[13%]",
                        (index === 7 || index === 8) && "w-[8%]"
                      )}
                    >
                      {header.isPlaceholder
                        ? null
                        : flexRender(header.column.columnDef.header, header.getContext())}
                    </TableHead>
                  );
                })}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows.length ? (
              table.getRowModel().rows.map((row) => (
                <TableRow key={row.id}>
                  {row.getVisibleCells().map((cell, index) => (
                    <TableCell
                      key={cell.id}
                      className={cn(
                        index === 0 && "w-7 pr-0 pl-1",
                        index === 1 && "w-[8%] pl-3",
                        index === 2 && "w-[26%]",
                        index === 3 && "w-[11%] text-center",
                        index === 4 && "w-[calc(11%+8px)] text-center",
                        index === 5 && "w-[9%] text-center",
                        index === 6 && "w-[13%]",
                        index === 7 && "w-[8%] text-center",
                        index === 8 && "w-[8%]"
                      )}
                    >
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell className="h-[260px] text-center" colSpan={opportunityColumns.length}>
                  <div className="flex flex-col items-center gap-[7px]">
                    <strong className="text-sm">
                      {hasActiveFilters ? "No opportunities found" : "No open opportunities"}
                    </strong>
                    <span
                      className={cn(
                        "text-[13px] text-[var(--text-soft)]",
                        hasActiveFilters && "mb-2"
                      )}
                    >
                      {hasActiveFilters
                        ? "Try changing or clearing your filters."
                        : "The directory currently has no open roles."}
                    </span>
                    {hasActiveFilters ? (
                      <Button variant="outline" size="sm" onClick={onReset}>
                        Reset filters
                      </Button>
                    ) : null}
                  </div>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      <div className="flex min-h-[58px] items-center justify-between px-0.5 text-xs text-[var(--text-soft)] max-[600px]:flex-col max-[600px]:items-start max-[600px]:gap-2.5 max-[600px]:pt-3.5">
        <label className="flex items-center gap-2">
          <span>Rows:</span>
          <span className="relative">
            <select
              className="h-[34px] w-[66px] cursor-pointer appearance-none rounded-md border border-[var(--border)] bg-[var(--surface)] py-0 pr-[30px] pl-2.5 text-xs text-[var(--text)] shadow-[0_1px_2px_rgb(0_0_0/3%)] outline-none focus:border-[var(--text-faint)] focus:shadow-[0_0_0_3px_color-mix(in_srgb,var(--text)_9%,transparent)]"
              value={view.pageSize}
              onChange={(event) => {
                const pageSize = DIRECTORY_PAGE_SIZES.find(
                  (option) => option === Number(event.target.value)
                );
                if (pageSize) onPageSizeChange(pageSize);
              }}
              aria-label="Rows per page"
            >
              {DIRECTORY_PAGE_SIZES.map((pageSize) => (
                <option key={pageSize} value={pageSize}>
                  {pageSize}
                </option>
              ))}
            </select>
            <ChevronDown
              className="pointer-events-none absolute top-1/2 right-[9px] size-3.5 -translate-y-1/2 text-[var(--text-faint)]"
              aria-hidden="true"
            />
          </span>
        </label>
        <div className="flex items-center gap-2">
          <span className="mr-1.5">
            Page {view.page} of {Math.max(table.getPageCount(), 1)}
          </span>
          {table.getCanPreviousPage() ? (
            <a
              className={paginationLinkClassName}
              href={pageHref(view.page - 1)}
              onClick={(event) => followPageLink(event, view.page - 1)}
              aria-label="Previous page"
            >
              <ChevronLeft aria-hidden="true" />
            </a>
          ) : (
            <Button variant="outline" size="icon" disabled aria-label="Previous page">
              <ChevronLeft aria-hidden="true" />
            </Button>
          )}
          {table.getCanNextPage() ? (
            <a
              className={paginationLinkClassName}
              href={pageHref(view.page + 1)}
              onClick={(event) => followPageLink(event, view.page + 1)}
              aria-label="Next page"
            >
              <ChevronRight aria-hidden="true" />
            </a>
          ) : (
            <Button variant="outline" size="icon" disabled aria-label="Next page">
              <ChevronRight aria-hidden="true" />
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

function toDirectorySort(sorting: SortingState): DirectorySort {
  const primarySort = sorting[0];
  if (!primarySort) return "first-seen-desc";

  switch (primarySort.id) {
    case "company":
      return primarySort.desc ? "company-desc" : "company-asc";
    case "title":
      return primarySort.desc ? "role-desc" : "role-asc";
    case "location":
      return primarySort.desc ? "location-desc" : "location-asc";
    case "firstSeenAt":
      return primarySort.desc ? "first-seen-desc" : "first-seen-asc";
    default:
      return "first-seen-desc";
  }
}
