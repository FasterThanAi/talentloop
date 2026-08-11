import React, { useState, useEffect } from "react";
import { AlertTriangle, X } from "lucide-react";

export const ConfirmDialog = ({
  isOpen,
  onClose,
  onConfirm,
  title = "Confirm Irreversible Action",
  description = "This action cannot be undone. Please type the confirmation word below.",
  confirmNoun = "CONFIRM",
  confirmButtonText = "Confirm Action",
  isDestructive = true,
  isLoading = false,
}) => {
  const [inputValue, setInputValue] = useState("");

  useEffect(() => {
    if (isOpen) {
      setInputValue("");
    }
  }, [isOpen]);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const isMatched = inputValue.trim().toUpperCase() === confirmNoun.toUpperCase();

  const handleConfirm = (e) => {
    e.preventDefault();
    if (isMatched && !isLoading) {
      onConfirm();
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-text/40 backdrop-blur-sm transition-opacity duration-150"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative w-full max-w-md bg-bg border border-border rounded-card shadow-card p-6 space-y-4 z-10">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2.5">
            <div className={`p-2 rounded-control ${isDestructive ? "bg-danger/10 text-danger" : "bg-warning/10 text-warning"}`}>
              <AlertTriangle className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-text">{title}</h3>
              <p className="text-xs text-text-muted mt-0.5">Irreversible Operation</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded-control text-text-muted hover:text-text hover:bg-surface transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-primary"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <p className="text-sm text-text-muted leading-relaxed font-sans">{description}</p>

        <form onSubmit={handleConfirm} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-text uppercase tracking-wider mb-1.5">
              Type <span className="font-mono text-danger font-bold">{confirmNoun}</span> to proceed:
            </label>
            <input
              type="text"
              autoFocus
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder={confirmNoun}
              className="w-full px-3 py-2 border border-border rounded-control text-sm bg-bg text-text font-mono focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t border-border">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-semibold text-text bg-surface border border-border rounded-control hover:bg-border/40 transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-primary"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!isMatched || isLoading}
              className={`px-4 py-2 text-xs font-semibold text-white rounded-control transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-40 disabled:cursor-not-allowed ${
                isDestructive ? "bg-danger hover:bg-danger/90" : "bg-primary hover:bg-primary/90"
              }`}
            >
              {isLoading ? "Processing..." : confirmButtonText}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ConfirmDialog;
