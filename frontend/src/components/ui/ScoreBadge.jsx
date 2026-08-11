import React from "react";

export const getScoreBandStyles = (score) => {
  if (score === null || score === undefined) {
    return {
      bg: "bg-surface",
      text: "text-text-muted",
      border: "border-border",
      label: "Unscored",
    };
  }
  if (score >= 80) {
    return {
      bg: "bg-[#0F7A5A]/10",
      text: "text-success",
      border: "border-success/30",
      label: "Strong Fit",
    };
  }
  if (score >= 60) {
    return {
      bg: "bg-primary-weak",
      text: "text-primary",
      border: "border-primary/30",
      label: "Partial Fit",
    };
  }
  if (score >= 40) {
    return {
      bg: "bg-warning/10",
      text: "text-warning",
      border: "border-warning/30",
      label: "Weak Fit",
    };
  }
  // 0-39: Muted neutral band (NEVER red)
  return {
    bg: "bg-surface",
    text: "text-text-muted",
    border: "border-border",
    label: "Not a Fit",
  };
};

export const ScoreBadge = ({ score, onClick, size = "md", showLabel = false }) => {
  const band = getScoreBandStyles(score);

  const sizeClasses = {
    sm: "px-2 py-0.5 text-xs",
    md: "px-2.5 py-1 text-sm font-semibold",
    lg: "px-3.5 py-1.5 text-base font-bold",
  }[size] || "px-2.5 py-1 text-sm font-semibold";

  return (
    <button
      type="button"
      onClick={onClick}
      className={`inline-flex items-center gap-1.5 rounded-pill border ${band.bg} ${band.text} ${band.border} ${sizeClasses} transition-all hover:opacity-90 active:scale-95 focus:outline-none focus:ring-2 focus:ring-primary`}
      title="Click to view explainable fit score breakdown & evidence citations"
    >
      <span>{score !== null && score !== undefined ? `${score}` : "—"}</span>
      {showLabel && <span className="text-xs font-normal opacity-80">({band.label})</span>}
      <svg className="w-3.5 h-3.5 opacity-60 ml-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7" />
      </svg>
    </button>
  );
};

export default ScoreBadge;
