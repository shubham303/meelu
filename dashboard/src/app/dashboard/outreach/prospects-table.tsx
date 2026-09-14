"use client";

import { useMemo } from "react";
import {
  type ColumnDef,
  type PaginationState,
  type SortingState,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { ArrowDown, ArrowUp, ChevronsUpDown } from "lucide-react";
import { Badge, Button, Table, TCell, TRow, type BadgeTone } from "@/components/ui";
import { cn, formatRelative } from "@/lib/utils";
import type { Prospect, ProspectStatus } from "@/lib/types";

const prospectTone: Record<ProspectStatus, BadgeTone> = {
  found: "neutral",
  contacted: "accent",
  replied: "good",
  won: "good",
  rejected: "bad",
};

export const PROSPECT_STATUS_LABEL: Record<ProspectStatus, string> = {
  found: "found",
  contacted: "contacted",
  replied: "replied",
  won: "won",
  rejected: "rejected",
};

const STATUS_RANK: Record<ProspectStatus, number> = {
  found: 0,
  contacted: 1,
  replied: 2,
  won: 3,
  rejected: 4,
};

export function ProspectsTable({
  prospects,
  globalFilter,
  onGlobalFilterChange,
  sorting,
  onSortingChange,
  pagination,
  onPaginationChange,
  onOpen,
}: {
  prospects: Prospect[];
  globalFilter: string;
  onGlobalFilterChange: (value: string) => void;
  sorting: SortingState;
  onSortingChange: (updater: React.SetStateAction<SortingState>) => void;
  pagination: PaginationState;
  onPaginationChange: (updater: React.SetStateAction<PaginationState>) => void;
  onOpen: (prospect: Prospect) => void;
}) {
  const columns = useMemo<ColumnDef<Prospect>[]>(
    () => [
      {
        id: "name",
        header: "Name",
        accessorFn: (p) => `${p.name} ${p.role ?? ""}`,
        cell: ({ row }) => (
          <div className="min-w-0">
            <p className="text-ink truncate">{row.original.name}</p>
            {row.original.role && (
              <p className="text-xs text-faint truncate">{row.original.role}</p>
            )}
          </div>
        ),
      },
      {
        id: "company",
        header: "Company",
        accessorFn: (p) => p.company ?? "",
        cell: ({ getValue }) => (
          <span className="text-sub">{(getValue() as string) || "—"}</span>
        ),
      },
      {
        id: "email",
        header: "Email",
        accessorFn: (p) => p.email ?? "",
        cell: ({ getValue }) => (
          <span className="text-sub break-all">{(getValue() as string) || "—"}</span>
        ),
      },
      {
        id: "status",
        header: "Status",
        accessorFn: (p) => STATUS_RANK[p.status] ?? 0,
        cell: ({ row }) => (
          <Badge tone={prospectTone[row.original.status] ?? "neutral"}>
            {PROSPECT_STATUS_LABEL[row.original.status] ?? row.original.status}
          </Badge>
        ),
      },
      {
        id: "createdAt",
        header: "Added",
        accessorFn: (p) => new Date(p.createdAt).getTime(),
        cell: ({ row }) => (
          <span className="text-sub">{formatRelative(row.original.createdAt)}</span>
        ),
      },
    ],
    [],
  );

  const table = useReactTable({
    data: prospects,
    columns,
    state: { sorting, globalFilter, pagination },
    onSortingChange,
    onGlobalFilterChange: (updater) =>
      onGlobalFilterChange(
        typeof updater === "function" ? (updater as (old: string) => string)(globalFilter) : updater,
      ),
    onPaginationChange,
    globalFilterFn: "includesString",
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
  });

  const rows = table.getRowModel().rows;
  const total = table.getFilteredRowModel().rows.length;
  const first = total === 0 ? 0 : pagination.pageIndex * pagination.pageSize + 1;
  const last = Math.min(total, (pagination.pageIndex + 1) * pagination.pageSize);

  return (
    <>
      <Table>
        <thead>
          {table.getHeaderGroups().map((group) => (
            <tr key={group.id} className="border-b border-edge">
              {group.headers.map((header) => {
                const sorted = header.column.getIsSorted();
                const Icon = sorted === "asc" ? ArrowUp : sorted === "desc" ? ArrowDown : ChevronsUpDown;
                return (
                  <th key={header.id} className="text-left px-4 py-3">
                    <button
                      onClick={header.column.getToggleSortingHandler()}
                      className={cn(
                        "inline-flex items-center gap-1 text-xs font-medium uppercase tracking-wide cursor-pointer",
                        sorted ? "text-ink" : "text-sub hover:text-ink",
                      )}
                    >
                      {flexRender(header.column.columnDef.header, header.getContext())}
                      <Icon size={11} className={cn(!sorted && "opacity-40")} />
                    </button>
                  </th>
                );
              })}
            </tr>
          ))}
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <TRow>
              <TCell className="text-center text-faint py-10">
                <span>No prospects match that search.</span>
              </TCell>
            </TRow>
          ) : (
            rows.map((row) => (
              <TRow key={row.id} onClick={() => onOpen(row.original)}>
                {row.getVisibleCells().map((cell) => (
                  <TCell key={cell.id}>
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </TCell>
                ))}
              </TRow>
            ))
          )}
        </tbody>
      </Table>

      <div className="flex flex-wrap items-center justify-between gap-3 mt-3">
        <p className="text-xs text-faint">
          {total === 0 ? "Nothing to show" : `${first}–${last} of ${total}`}
        </p>
        <div className="flex items-center gap-1">
          <Button
            variant="outline"
            size="sm"
            disabled={!table.getCanPreviousPage()}
            onClick={() => table.previousPage()}
          >
            Previous
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={!table.getCanNextPage()}
            onClick={() => table.nextPage()}
          >
            Next
          </Button>
        </div>
      </div>
    </>
  );
}
