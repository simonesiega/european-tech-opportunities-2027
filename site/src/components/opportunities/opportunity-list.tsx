"use client";

import {useState} from "react";
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
import type {Opportunity} from "@/types/opportunity";

type OpportunityListProps = {
  opportunities: Opportunity[];
  onReset: () => void;
};

export function OpportunityList({opportunities, onReset}: OpportunityListProps) {
  const [sorting, setSorting] = useState<SortingState>([]);
  // TanStack Table intentionally returns non-memoizable functions as part of its API.
  // eslint-disable-next-line react-hooks/incompatible-library
  const table = useReactTable({
    data: opportunities,
    columns: opportunityColumns,
    state: {sorting},
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: {pagination: {pageIndex: 0, pageSize: 10}},
  });

  return (
    <div className="mt-4">
      <div className="overflow-hidden rounded-lg border border-[var(--border)] bg-[var(--surface)] shadow-[0_1px_2px_rgb(0_0_0/3%)]">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header, index) => (
                  <TableHead
                    key={header.id}
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
                ))}
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
                    <strong className="text-sm">No opportunities found</strong>
                    <span className="mb-2 text-[13px] text-[var(--text-soft)]">
                      Try changing or clearing your filters.
                    </span>
                    <Button variant="outline" size="sm" onClick={onReset}>
                      Reset filters
                    </Button>
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
              value={table.getState().pagination.pageSize}
              onChange={(event) => table.setPageSize(Number(event.target.value))}
              aria-label="Rows per page"
            >
              {[10, 20, 30, 50, 100].map((pageSize) => (
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
            Page {table.getState().pagination.pageIndex + 1} of {Math.max(table.getPageCount(), 1)}
          </span>
          <Button
            variant="outline"
            size="icon"
            onClick={() => table.previousPage()}
            disabled={!table.getCanPreviousPage()}
            aria-label="Previous page"
          >
            <ChevronLeft aria-hidden="true" />
          </Button>
          <Button
            variant="outline"
            size="icon"
            onClick={() => table.nextPage()}
            disabled={!table.getCanNextPage()}
            aria-label="Next page"
          >
            <ChevronRight aria-hidden="true" />
          </Button>
        </div>
      </div>
    </div>
  );
}
