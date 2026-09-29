"use client";

import type {CSSProperties} from "react";
import type {Column, ColumnDef} from "@tanstack/react-table";
import {ArrowUpDown, ArrowUpRight, Check, X} from "lucide-react";
import {OpportunityActions} from "@/components/opportunities/opportunity-actions";
import {Badge} from "@/components/ui/badge";
import {Button} from "@/components/ui/button";
import {
  formatCategory,
  formatPublishedDate,
  getCategoryHue,
  getEmploymentTypeHue,
} from "@/lib/opportunity-presentation";
import type {Opportunity} from "@/types/opportunity";

function SortableHeader({column, label}: {column: Column<Opportunity>; label: string}) {
  return (
    <Button
      variant="ghost"
      size="sm"
      className="mx-auto h-[30px] px-2.5 text-[11px] text-inherit [&_svg]:size-[13px] [&_svg]:opacity-55"
      onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
    >
      {label}
      <ArrowUpDown aria-hidden="true" />
    </Button>
  );
}

export function opportunityColumns(
  state: {saved: string[]; hidden: string[]; applied: string[]} | null,
  toggle: (field: "saved" | "hidden" | "applied", id: string) => void,
  newIds: Set<string>
): ColumnDef<Opportunity>[] {
  return [
    {
      id: "open",
      header: () => <span className="sr-only">Listing</span>,
      enableSorting: false,
      cell: ({row}) => (
        <a
          className="inline-flex size-8 w-7 items-center justify-center rounded-md text-[var(--text-soft)] transition-colors duration-150 hover:bg-[var(--surface-hover)] hover:text-[var(--text)] [&_svg]:size-4"
          href={row.original.link}
          target="_blank"
          rel="noreferrer"
          aria-label={`Open ${row.original.title} at ${row.original.company}`}
        >
          <ArrowUpRight aria-hidden="true" />
        </a>
      ),
    },
    {
      accessorKey: "company",
      header: ({column}) => <SortableHeader column={column} label="Company" />,
      cell: ({row}) => <span className="font-semibold">{row.original.company}</span>,
    },
    {
      id: "new",
      header: "New",
      enableSorting: false,
      cell: ({row}) =>
        newIds.has(row.original.linkedinJobId) ? (
          <span
            className="inline-flex items-center justify-center text-[var(--text)]"
            aria-label="New since your last visit"
            title="New since your last visit"
          >
            <Check aria-hidden="true" className="size-4" />
            <span className="sr-only">Yes</span>
          </span>
        ) : (
          <span
            className="inline-flex items-center justify-center text-[var(--text-faint)]"
            aria-label="Not new since your last visit"
            title="Not new since your last visit"
          >
            <X aria-hidden="true" className="size-4" />
            <span className="sr-only">No</span>
          </span>
        ),
    },
    {
      accessorKey: "title",
      header: ({column}) => <SortableHeader column={column} label="Role" />,
      cell: ({row}) => (
        <a
          className="line-clamp-2 leading-[1.35] font-medium hover:underline hover:underline-offset-3"
          href={row.original.link}
          target="_blank"
          rel="noreferrer"
        >
          {row.original.title}
        </a>
      ),
    },
    {
      accessorKey: "category",
      header: "Category",
      cell: ({row}) => (
        <Badge
          className="border-[hsl(var(--badge-hue)_38%_82%)] bg-[hsl(var(--badge-hue)_55%_93%)] text-[hsl(var(--badge-hue)_38%_32%)] dark:border-[hsl(var(--badge-hue)_25%_28%)] dark:bg-[hsl(var(--badge-hue)_28%_18%)] dark:text-[hsl(var(--badge-hue)_45%_76%)]"
          variant="secondary"
          style={{"--badge-hue": getCategoryHue(row.original.category)} as CSSProperties}
        >
          {formatCategory(row.original.category)}
        </Badge>
      ),
    },
    {
      accessorKey: "industries",
      header: "Industries",
      cell: ({row}) => (
        <span className="leading-[1.4] text-[var(--text-soft)]">
          {row.original.industries ?? "Not specified"}
        </span>
      ),
    },
    {
      accessorKey: "employmentType",
      header: "Employment type",
      cell: ({row}) => (
        <Badge
          className="border-[hsl(var(--badge-hue)_38%_82%)] bg-[hsl(var(--badge-hue)_55%_93%)] text-[hsl(var(--badge-hue)_38%_32%)] dark:border-[hsl(var(--badge-hue)_25%_28%)] dark:bg-[hsl(var(--badge-hue)_28%_18%)] dark:text-[hsl(var(--badge-hue)_45%_76%)]"
          variant="outline"
          style={
            {
              "--badge-hue": getEmploymentTypeHue(row.original.employmentType),
            } as CSSProperties
          }
        >
          {formatCategory(row.original.employmentType)}
        </Badge>
      ),
    },
    {
      accessorKey: "location",
      header: ({column}) => <SortableHeader column={column} label="Location" />,
      cell: ({row}) => (
        <span className="leading-[1.4] text-[var(--text-soft)]">{row.original.location}</span>
      ),
    },
    {
      accessorKey: "startDate",
      header: "Start date",
      cell: ({row}) => (
        <span className="leading-[1.4] whitespace-nowrap text-[var(--text-soft)]">
          {row.original.startDate ?? "—"}
        </span>
      ),
    },
    {
      accessorKey: "firstSeenAt",
      header: ({column}) => <SortableHeader column={column} label="First seen" />,
      cell: ({row}) => (
        <time
          className="leading-[1.4] whitespace-nowrap text-[var(--text-soft)]"
          dateTime={row.original.firstSeenAt}
        >
          {formatPublishedDate(row.original.firstSeenAt)}
        </time>
      ),
    },
    {
      id: "actions",
      header: "Your list",
      enableSorting: false,
      cell: ({row}) => (
        <OpportunityActions
          opportunity={row.original}
          saved={state?.saved.includes(row.original.linkedinJobId) ?? false}
          applied={state?.applied.includes(row.original.linkedinJobId) ?? false}
          hidden={state?.hidden.includes(row.original.linkedinJobId) ?? false}
          disabled={!state}
          onToggle={toggle}
        />
      ),
    },
  ];
}
