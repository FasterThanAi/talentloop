import React from "react";

export const ConfidenceMeter = ({ confidence = "medium" }) => {
  const confStyles = {
    high: {
      bg: "bg-success/10",
      text: "text-success",
      border: "border-success/30",
      label: "High Confidence",
      desc: "Supported by multiple verifiable public evidence sources.",
    },
    medium: {
      bg: "bg-primary-weak",
      text: "text-primary",
      border: "border-primary/30",
      label: "Medium Confidence",
      desc: "Sufficient evidence available, with minor unverified areas.",
    },
    low: {
      bg: "bg-warning/10",
      text: "text-warning",
      border: "border-warning/30",
      label: "Low Confidence (Capped ≤70)",
      desc: "Sparse public evidence. Score strictly capped at 70.",
    },
  }[confidence.toLowerCase()] || {
    bg: "bg-surface",
    text: "text-text-muted",
    border: "border-border",
    label: confidence,
    desc: "",
  };

  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-control border ${confStyles.bg} ${confStyles.text} ${confStyles.border}`}
      title={confStyles.desc}
    >
      <span className="w-1.5 h-1.5 rounded-full bg-current" />
      {confStyles.label}
    </span>
  );
};

export default ConfidenceMeter;
