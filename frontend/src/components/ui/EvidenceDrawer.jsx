import React, { useEffect } from "react";
import { X, ExternalLink, AlertCircle, CheckCircle2, HelpCircle } from "lucide-react";
import ScoreBadge from "./ScoreBadge";
import ConfidenceMeter from "./ConfidenceMeter";

export const EvidenceDrawer = ({ isOpen, onClose, explainData }) => {
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen || !explainData) return null;

  const {
    candidate_name,
    role_title,
    fit_score,
    score_reason,
    breakdown,
    rubric_version,
    confidence,
    could_not_determine,
    evidence_urls,
  } = explainData;

  const dimensions = breakdown?.dimensions || [];

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-text/30 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />

      <div className="fixed inset-y-0 right-0 max-w-full flex pl-10">
        <div className="w-screen max-w-xl bg-bg border-l border-border shadow-2xl flex flex-col">
          {/* Header */}
          <div className="px-6 py-5 border-b border-border bg-surface flex items-start justify-between">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs font-semibold px-2 py-0.5 rounded-control ai-evidence-chip">
                  Rubric {rubric_version || "v1"}
                </span>
                <ConfidenceMeter confidence={confidence || "medium"} />
              </div>
              <h2 className="text-xl font-semibold text-text">{candidate_name}</h2>
              <p className="text-sm text-text-muted">{role_title}</p>
            </div>
            <button
              onClick={onClose}
              className="p-1 rounded-control text-text-muted hover:text-text hover:bg-border transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Drawer Body */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {/* Top Score Summary Banner */}
            <div className="p-4 rounded-card bg-surface border border-border flex items-center justify-between">
              <div>
                <span className="text-xs uppercase tracking-wider font-semibold text-text-muted block mb-1">
                  Deterministic Fit Score
                </span>
                <p className="text-xs text-text-muted max-w-xs">
                  Model rated individual dimensions; deterministic Python aggregated the weighted sum.
                </p>
              </div>
              <ScoreBadge score={fit_score} size="lg" showLabel />
            </div>

            {/* Score Reason */}
            {score_reason && (
              <div className="p-4 rounded-card bg-primary-weak/50 border border-primary/20 ai-evidence-border">
                <span className="text-xs font-semibold text-primary block mb-1">Reasoning Summary</span>
                <p className="text-sm text-text leading-relaxed">{score_reason}</p>
              </div>
            )}

            {/* Rubric Dimensions */}
            <div>
              <h3 className="text-sm font-semibold text-text uppercase tracking-wider mb-4">
                Rubric Dimension Breakdown (5 Dimensions)
              </h3>
              <div className="space-y-4">
                {dimensions.length === 0 && (
                  <div className="p-4 rounded-card border border-dashed border-border bg-surface/40 text-xs text-text-muted leading-relaxed">
                    <span className="font-semibold text-text block mb-1">Not scored yet</span>
                    This candidate has evidence collected but no rubric evaluation. Open the
                    requisition, make sure the job description is parsed, then run
                    <span className="font-medium text-text"> Score All Candidates</span>.
                  </div>
                )}
                {dimensions.map((dim, idx) => {
                  const dimTitles = {
                    must_have_coverage: "Must-Have Requirements Coverage (40%)",
                    depth_of_experience: "Depth vs. Surface Familiarity (25%)",
                    domain_relevance: "Domain & Context Relevance (15%)",
                    nice_to_have_bonus: "Nice-to-Have Evidenced Skills (10%)",
                    trajectory: "Growth & Ownership Trajectory (10%)",
                  };
                  const title = dimTitles[dim.dimension] || dim.dimension.replace(/_/g, " ");

                  return (
                    <div key={idx} className="p-4 rounded-card border border-border bg-surface/50 space-y-2">
                      <div className="flex items-center justify-between text-sm">
                        <span className="font-medium text-text">{title}</span>
                        <span className="font-semibold text-text">{dim.score}/100</span>
                      </div>

                      {/* Progress Bar */}
                      <div className="w-full bg-border rounded-full h-2 overflow-hidden">
                        <div
                          className={`h-full rounded-full ${
                            dim.score >= 80
                              ? "bg-success"
                              : dim.score >= 60
                              ? "bg-primary"
                              : dim.score >= 40
                              ? "bg-warning"
                              : "bg-text-muted"
                          }`}
                          style={{ width: `${dim.score}%` }}
                        />
                      </div>

                      {/* Justification */}
                      <p className="text-xs text-text-muted leading-relaxed pt-1">
                        {dim.justification}
                      </p>

                      {/* Citations */}
                      {dim.citations && dim.citations.length > 0 && (
                        <div className="pt-2 flex flex-wrap gap-2">
                          <span className="text-xs font-medium text-text-muted flex items-center gap-1">
                            Citations:
                          </span>
                          {dim.citations.map((cite, cIdx) => (
                            <a
                              key={cIdx}
                              href={cite}
                              target="_blank"
                              rel="noreferrer"
                              className="text-xs text-primary hover:underline inline-flex items-center gap-1 bg-primary-weak px-2 py-0.5 rounded"
                            >
                              {cite.replace(/^https?:\/\//, "").slice(0, 30)}...
                              <ExternalLink className="w-3 h-3" />
                            </a>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Could Not Determine */}
            {could_not_determine && could_not_determine.length > 0 && (
              <div className="p-4 rounded-card border border-warning/30 bg-warning/5 space-y-2">
                <div className="flex items-center gap-1.5 text-warning font-semibold text-xs uppercase tracking-wider">
                  <HelpCircle className="w-4 h-4" />
                  Could Not Determine from Public Evidence
                </div>
                <ul className="list-disc list-inside text-xs text-text space-y-1 pl-1">
                  {could_not_determine.map((item, idx) => (
                    <li key={idx}>{item}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* All Stored Evidence URLs */}
            {evidence_urls && evidence_urls.length > 0 && (
              <div className="space-y-2">
                <span className="text-xs font-semibold text-text-muted uppercase tracking-wider block">
                  Verified Source URLs
                </span>
                <div className="space-y-1">
                  {evidence_urls.map((url, idx) => (
                    <a
                      key={idx}
                      href={url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-xs text-text-muted hover:text-primary flex items-center gap-1 truncate"
                    >
                      <ExternalLink className="w-3.5 h-3.5 flex-shrink-0" />
                      <span className="truncate">{url}</span>
                    </a>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Drawer Footer */}
          <div className="p-4 border-t border-border bg-surface flex justify-end">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-text bg-bg border border-border rounded-control hover:bg-surface transition-colors"
            >
              Close Drawer
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default EvidenceDrawer;
