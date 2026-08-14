import React, { useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { Loader2, CheckCircle2, AlertCircle } from "lucide-react";
import api from "../../lib/api";

export const JobProgress = ({ jobId, onCompleted, label = "Processing background task" }) => {
  const { data: job } = useQuery({
    queryKey: ["job", jobId],
    queryFn: () => api.get(`/jobs/${jobId}`),
    enabled: Boolean(jobId),
    // MUST stay pure. This runs on every render, so calling onCompleted() from here
    // triggered: callback -> parent re-render -> this re-evaluated -> callback again,
    // an infinite loop that froze the browser tab ("Page Unresponsive").
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "completed" || status === "failed" ? false : 1500;
    },
  });

  // Side effects belong in an effect, and this one must fire exactly once per job.
  const notifiedForJob = useRef(null);
  useEffect(() => {
    if (job?.status === "completed" && notifiedForJob.current !== jobId) {
      notifiedForJob.current = jobId;
      onCompleted?.();
    }
  }, [job?.status, jobId, onCompleted]);

  if (!job) return null;

  const percentage = job.total > 0 ? Math.min(100, Math.round((job.processed / job.total) * 100)) : 0;
  const isFinished = job.status === "completed";
  const isFailed = job.status === "failed";

  return (
    <div className="p-4 rounded-card border border-border bg-surface shadow-sm space-y-3 my-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {!isFinished && !isFailed && <Loader2 className="w-4 h-4 text-primary animate-spin" />}
          {isFinished && <CheckCircle2 className="w-4 h-4 text-success" />}
          {isFailed && <AlertCircle className="w-4 h-4 text-danger" />}
          <span className="text-sm font-semibold text-text">{label}</span>
        </div>
        <span className="text-xs font-semibold text-text-muted">
          {job.processed} of {job.total} ({percentage}%)
        </span>
      </div>

      <div className="w-full bg-border rounded-full h-2 overflow-hidden">
        <div
          className={`h-full transition-all duration-300 rounded-full ${
            isFailed ? "bg-danger" : isFinished ? "bg-success" : "bg-primary"
          }`}
          style={{ width: `${percentage}%` }}
        />
      </div>

      {job.errors && job.errors.length > 0 && (
        <div className="pt-2 text-xs text-warning space-y-1">
          <span className="font-semibold">Notice ({job.errors.length}):</span>
          {job.errors.slice(0, 3).map((err, i) => (
            <p key={i} className="truncate">
              {err.email ? `[${err.email}] ` : ""}
              {err.error || err.info}
            </p>
          ))}
        </div>
      )}
    </div>
  );
};

export default JobProgress;
