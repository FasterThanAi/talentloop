import React, { useState } from "react";
import { Check, X, AlertTriangle } from "lucide-react";

export const ApprovalBar = ({ selectedCount, onApprove, onReject, isApproving = false }) => {
  const [showConfirmModal, setShowConfirmModal] = useState(false);

  if (selectedCount === 0) return null;

  const handleApproveClick = () => {
    if (selectedCount > 20) {
      setShowConfirmModal(true);
    } else {
      onApprove();
    }
  };

  const confirmBulkAction = () => {
    setShowConfirmModal(false);
    onApprove();
  };

  return (
    <>
      <div className="fixed bottom-6 inset-x-0 max-w-2xl mx-auto z-40 px-4">
        <div className="bg-text text-bg p-3 px-5 rounded-card shadow-2xl flex items-center justify-between border border-border/20 backdrop-blur-md">
          <div className="flex items-center gap-3">
            <span className="bg-primary text-white text-xs font-bold px-2.5 py-1 rounded-pill">
              {selectedCount}
            </span>
            <span className="text-sm font-medium">
              {selectedCount === 1 ? "candidate item selected" : "candidate items selected"}
            </span>
          </div>

          <div className="flex items-center gap-2">
            {onReject && (
              <button
                type="button"
                onClick={onReject}
                className="px-3 py-1.5 text-xs font-medium text-text-muted hover:text-white transition-colors"
              >
                Clear
              </button>
            )}
            <button
              type="button"
              onClick={handleApproveClick}
              disabled={isApproving}
              className="px-4 py-1.5 text-xs font-semibold bg-success hover:bg-success/90 text-white rounded-control flex items-center gap-1.5 transition-all active:scale-95 disabled:opacity-50"
            >
              <Check className="w-3.5 h-3.5" />
              {isApproving ? "Processing..." : `Approve & Dispatch (${selectedCount})`}
            </button>
          </div>
        </div>
      </div>

      {/* Confirmation modal for >20 items */}
      {showConfirmModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-text/40 backdrop-blur-sm">
          <div className="bg-bg border border-border rounded-card p-6 max-w-md w-full shadow-2xl space-y-4">
            <div className="flex items-center gap-2 text-warning font-semibold text-base">
              <AlertTriangle className="w-5 h-5" />
              Confirm Bulk Action ({selectedCount} items)
            </div>
            <p className="text-sm text-text-muted">
              You are about to approve and trigger outbound action for {selectedCount} candidate records. This will dispatch real emails or release reports once processed.
            </p>
            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setShowConfirmModal(false)}
                className="px-4 py-2 text-xs font-medium text-text bg-surface border border-border rounded-control hover:bg-border transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={confirmBulkAction}
                className="px-4 py-2 text-xs font-semibold bg-success text-white rounded-control hover:bg-success/90 transition-colors"
              >
                Confirm Bulk Send
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default ApprovalBar;
