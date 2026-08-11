import React, { useState } from "react";
import { X, Upload, Globe, Database, Loader2, CheckCircle2 } from "lucide-react";
import api from "../../lib/api";

export const SourcingModal = ({ isOpen, onClose, requisitionId, onJobStarted }) => {
  const [sourceType, setSourceType] = useState("csv"); // "csv" | "urls" | "rizeos"
  const [file, setFile] = useState(null);
  const [urlsText, setUrlsText] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setIsSubmitting(true);

    try {
      let res;
      if (sourceType === "csv") {
        if (!file) throw new Error("Please select a CSV or ZIP file to upload.");
        const formData = new FormData();
        formData.append("file", file);
        res = await api.post(`/requisitions/${requisitionId}/source/csv`, formData, {
          headers: { "Content-Type": "multipart/form-data" },
        });
      } else if (sourceType === "urls") {
        const urls = urlsText
          .split("\n")
          .map((u) => u.trim())
          .filter((u) => u.length > 0);
        if (urls.length === 0) throw new Error("Please provide at least one URL.");
        res = await api.post(`/requisitions/${requisitionId}/source/urls`, { urls });
      } else if (sourceType === "rizeos") {
        res = await api.post(`/requisitions/${requisitionId}/source/rizeos-pool`);
      }

      if (res.job_id && onJobStarted) {
        onJobStarted(res.job_id);
      }
      onClose();
    } catch (err) {
      setError(err.message || "Failed to initiate sourcing job.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-text/30 backdrop-blur-sm">
      <div className="bg-bg border border-border rounded-card max-w-lg w-full p-6 shadow-2xl space-y-4">
        <div className="flex items-center justify-between border-b border-border pb-3">
          <h3 className="text-base font-semibold text-text">Source Candidates</h3>
          <button onClick={onClose} className="p-1 rounded-control text-text-muted hover:text-text">
            <X className="w-4 h-4" />
          </button>
        </div>

        {error && <div className="p-3 bg-danger/10 text-danger text-xs rounded-control">{error}</div>}

        {/* Sourcing Channel Selector */}
        <div className="grid grid-cols-3 gap-2">
          <button
            type="button"
            onClick={() => setSourceType("csv")}
            className={`p-3 rounded-control border text-left flex flex-col items-center justify-center gap-1.5 transition-colors ${
              sourceType === "csv"
                ? "border-primary bg-primary-weak text-primary font-semibold"
                : "border-border bg-surface text-text-muted hover:text-text"
            }`}
          >
            <Upload className="w-4 h-4" />
            <span className="text-xs">CSV / Resumes</span>
          </button>
          <button
            type="button"
            onClick={() => setSourceType("urls")}
            className={`p-3 rounded-control border text-left flex flex-col items-center justify-center gap-1.5 transition-colors ${
              sourceType === "urls"
                ? "border-primary bg-primary-weak text-primary font-semibold"
                : "border-border bg-surface text-text-muted hover:text-text"
            }`}
          >
            <Globe className="w-4 h-4" />
            <span className="text-xs">Public URLs</span>
          </button>
          <button
            type="button"
            onClick={() => setSourceType("rizeos")}
            className={`p-3 rounded-control border text-left flex flex-col items-center justify-center gap-1.5 transition-colors ${
              sourceType === "rizeos"
                ? "border-primary bg-primary-weak text-primary font-semibold"
                : "border-border bg-surface text-text-muted hover:text-text"
            }`}
          >
            <Database className="w-4 h-4" />
            <span className="text-xs">RizeOS Pool</span>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 pt-2">
          {sourceType === "csv" && (
            <div className="p-4 border-2 border-dashed border-border rounded-card bg-surface/30 text-center space-y-2">
              <input
                type="file"
                accept=".csv,.zip"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
                className="text-xs text-text-muted file:mr-3 file:py-1.5 file:px-3 file:rounded-control file:border file:border-border file:bg-bg file:text-xs file:font-semibold file:text-text hover:file:bg-surface"
              />
              <p className="text-[11px] text-text-muted">
                Accepts <code>.csv</code> (name, email, public_urls) or <code>.zip</code> of PDF/DOCX resumes.
              </p>
            </div>
          )}

          {sourceType === "urls" && (
            <div>
              <label className="block text-xs font-semibold text-text uppercase tracking-wider mb-1">
                Recruiter-Supplied Public Profile URLs (One per line)
              </label>
              <textarea
                rows={4}
                value={urlsText}
                onChange={(e) => setUrlsText(e.target.value)}
                placeholder="https://github.com/alexrivera&#10;https://github.com/torvalds"
                className="w-full px-3 py-2 border border-border rounded-control text-xs font-mono bg-bg text-text focus:ring-2 focus:ring-primary focus:outline-none"
              />
            </div>
          )}

          {sourceType === "rizeos" && (
            <div className="p-4 rounded-card bg-primary-weak/50 border border-primary/20 text-xs text-text space-y-1">
              <span className="font-semibold text-primary block">RizeOS Talent Network Pool</span>
              <p className="text-text-muted">
                Imports verified candidates who have explicitly opted into recruiting discovery. Zero gated platform scraping.
              </p>
            </div>
          )}

          <div className="flex justify-end gap-2 pt-2 border-t border-border">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-1.5 text-xs font-medium text-text bg-surface border border-border rounded-control hover:bg-border"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-4 py-1.5 text-xs font-semibold text-white bg-primary hover:bg-primary/90 rounded-control flex items-center gap-1.5 disabled:opacity-50"
            >
              {isSubmitting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              Start Ingestion Job
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default SourcingModal;
