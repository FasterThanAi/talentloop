import React from "react";
import { AlertCircle, RotateCcw } from "lucide-react";
import EmptyState from "./EmptyState";

export const DataTable = ({
  columns = [],
  data = [],
  isLoading = false,
  isError = false,
  error = null,
  onRetry = null,
  emptyTitle = "No records found",
  emptyDescription = "No data available in this view.",
  emptyAction = null,
  selectedIds = [],
  onSelectRow = null,
  onSelectAll = null,
  keyField = "id",
}) => {
  // 1. Loading State (Skeleton rows matching real layout)
  if (isLoading) {
    return (
      <div className="border border-border rounded-card bg-bg overflow-hidden shadow-sm">
        <div className="p-4 border-b border-border bg-surface flex gap-4">
          <div className="h-4 bg-border rounded w-1/4 animate-pulse" />
          <div className="h-4 bg-border rounded w-1/4 animate-pulse" />
          <div className="h-4 bg-border rounded w-1/4 animate-pulse" />
        </div>
        <div className="divide-y divide-border">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="p-4 flex gap-4 items-center">
              <div className="h-4 bg-surface rounded w-1/4 animate-pulse" />
              <div className="h-4 bg-surface rounded w-1/3 animate-pulse" />
              <div className="h-4 bg-surface rounded w-1/6 animate-pulse" />
              <div className="h-4 bg-surface rounded w-1/4 animate-pulse" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  // 2. Error State
  if (isError) {
    return (
      <div className="p-6 border border-danger/20 bg-danger/5 rounded-card text-center space-y-3 my-6">
        <div className="inline-flex p-2 bg-danger/10 text-danger rounded-pill">
          <AlertCircle className="w-6 h-6" />
        </div>
        <h4 className="text-base font-semibold text-text">Failed to load data</h4>
        <p className="text-xs text-text-muted max-w-md mx-auto">
          {error?.message || "An error occurred while fetching information from the server."}
        </p>
        {onRetry && (
          <button
            onClick={onRetry}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold text-text bg-bg border border-border rounded-control hover:bg-surface transition-colors"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            Retry
          </button>
        )}
      </div>
    );
  }

  // 3. Empty State
  if (!data || data.length === 0) {
    return <EmptyState title={emptyTitle} description={emptyDescription} action={emptyAction} />;
  }

  const allSelected = data.length > 0 && selectedIds.length === data.length;

  // 4. Populated State
  return (
    <div className="border border-border rounded-card bg-bg overflow-hidden shadow-sm">
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-border bg-surface text-xs font-semibold text-text-muted uppercase tracking-wider sticky top-0">
              {onSelectAll && (
                <th className="p-4 w-10">
                  <input
                    type="checkbox"
                    checked={allSelected}
                    onChange={onSelectAll}
                    className="rounded border-border text-primary focus:ring-primary h-4 w-4"
                  />
                </th>
              )}
              {columns.map((col, idx) => (
                <th key={idx} className={`p-4 ${col.className || ""}`}>
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-border text-sm text-text">
            {data.map((row, rowIdx) => {
              const rowId = row[keyField];
              const isSelected = selectedIds.includes(rowId);

              return (
                <tr
                  key={rowId || rowIdx}
                  className={`hover:bg-surface/60 transition-colors ${
                    isSelected ? "bg-primary-weak/40" : ""
                  }`}
                >
                  {onSelectRow && (
                    <td className="p-4 w-10">
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => onSelectRow(rowId)}
                        className="rounded border-border text-primary focus:ring-primary h-4 w-4"
                      />
                    </td>
                  )}
                  {columns.map((col, colIdx) => (
                    <td key={colIdx} className={`p-4 ${col.cellClassName || ""}`}>
                      {col.render ? col.render(row) : row[col.accessor]}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default DataTable;
