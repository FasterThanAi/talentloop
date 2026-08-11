import React from "react";
import { FolderOpen } from "lucide-react";

export const EmptyState = ({
  icon: Icon = FolderOpen,
  title = "No data found",
  description = "Get started by creating a new entry.",
  action,
}) => {
  return (
    <div className="p-12 text-center border border-dashed border-border rounded-card bg-surface/30 flex flex-col items-center justify-center my-6">
      <div className="p-3 bg-primary-weak text-primary rounded-pill mb-3">
        <Icon className="w-6 h-6" />
      </div>
      <h3 className="text-base font-semibold text-text mb-1">{title}</h3>
      <p className="text-sm text-text-muted max-w-sm mb-4">{description}</p>
      {action && <div>{action}</div>}
    </div>
  );
};

export default EmptyState;
