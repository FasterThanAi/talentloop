import React from "react";

export const StatusPill = ({ status = "draft" }) => {
  const statusMap = {
    draft: { bg: "bg-surface", text: "text-text-muted", border: "border-border", label: "Draft" },
    approved: { bg: "bg-primary-weak", text: "text-primary", border: "border-primary/30", label: "Approved" },
    sent: { bg: "bg-success/10", text: "text-success", border: "border-success/30", label: "Sent" },
    replied: { bg: "bg-evidence/10", text: "text-evidence", border: "border-evidence/30", label: "Replied" },
    released: { bg: "bg-success/10", text: "text-success", border: "border-success/30", label: "Released" },
    needs_review: { bg: "bg-warning/10", text: "text-warning", border: "border-warning/30", label: "Needs Review" },
    failed: { bg: "bg-danger/10", text: "text-danger", border: "border-danger/30", label: "Failed" },
    active: { bg: "bg-success/10", text: "text-success", border: "border-success/30", label: "Active" },
    scored: { bg: "bg-primary-weak", text: "text-primary", border: "border-primary/30", label: "Scored" },
    sourced: { bg: "bg-surface", text: "text-text-muted", border: "border-border", label: "Sourced" },
  };

  const current = statusMap[status.toLowerCase()] || statusMap.draft;

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-pill text-xs font-medium border ${current.bg} ${current.text} ${current.border}`}
    >
      {current.label}
    </span>
  );
};

export default StatusPill;
