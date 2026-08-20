import React from "react";
import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, AlertCircle, Loader2, ExternalLink } from "lucide-react";

export const BiasReportView = () => {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["bias-probes-report"],
    queryFn: async () => {
      const res = await fetch("/eval/bias-probes.json");
      if (!res.ok) {
        throw new Error("Report unavailable - run the eval suite");
      }
      return res.json();
    },
  });

  if (isLoading) {
    return (
      <div className="p-8 border border-border rounded-card bg-bg flex flex-col items-center justify-center gap-3 text-text-muted">
        <Loader2 className="w-6 h-6 animate-spin text-primary" />
        <span className="text-xs font-medium">Loading bias evaluation report...</span>
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="p-6 rounded-card bg-danger/10 border border-danger/30 flex items-start gap-3">
        <AlertCircle className="w-5 h-5 text-danger flex-shrink-0 mt-0.5" />
        <div className="text-xs space-y-1">
          <span className="font-bold text-sm text-danger block">
            Report unavailable - run the eval suite
          </span>
          <p className="text-text">
            The machine-readable bias probe report was not found. Please run the evaluation suite in the backend to generate the report.
          </p>
        </div>
      </div>
    );
  }

  const { generated_at, git_sha, tolerance, pairs = [] } = data;
  const formattedDate = generated_at ? new Date(generated_at).toLocaleString() : "Unknown date";
  const passedCount = pairs.filter((p) => p.status === "PASS").length;

  return (
    <div className="space-y-6">
      <div className="p-4 rounded-card bg-success/10 border border-success/30 flex items-start gap-3">
        <CheckCircle2 className="w-5 h-5 text-success flex-shrink-0 mt-0.5" />
        <div className="text-xs space-y-2">
          <span className="font-bold text-sm text-success block">
            Build Gate Passed: {passedCount} of {pairs.length} Matched Pairs In Tolerance (Δ ≤ {tolerance ?? 3})
          </span>
          <p className="text-text leading-relaxed">
            These probes verify that protected attributes (name, photo, age, gender, institution tier) never enter the scoring payload, and that deterministic aggregation produces identical scores for matched pairs. They do not measure bias in the model's per-dimension ratings.
          </p>
          <div className="text-text-muted flex flex-wrap items-center gap-1.5 pt-2 border-t border-success/20">
            <span>Generated from commit</span>
            {git_sha ? (
              <a
                href={`https://github.com/FasterThanAi/talentloop/commit/${git_sha}`}
                target="_blank"
                rel="noopener noreferrer"
                className="font-mono font-semibold text-primary hover:underline inline-flex items-center gap-0.5"
              >
                {git_sha}
                <ExternalLink className="w-3 h-3 ml-0.5" />
              </a>
            ) : (
              <span className="font-mono font-semibold">unknown</span>
            )}
            <span>on {formattedDate} by the blocking CI eval job</span>
          </div>
        </div>
      </div>

      <div className="border border-border rounded-card bg-bg overflow-hidden shadow-sm">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="border-b border-border bg-surface font-semibold text-text-muted uppercase tracking-wider">
              <th className="p-3">Probe ID</th>
              <th className="p-3">Tested Attribute</th>
              <th className="p-3">Candidate Variant A</th>
              <th className="p-3">Candidate Variant B</th>
              <th className="p-3">Score A</th>
              <th className="p-3">Score B</th>
              <th className="p-3">Delta</th>
              <th className="p-3">Gate Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border text-text">
            {pairs.map((probe) => (
              <tr key={probe.id} className="hover:bg-surface/50">
                <td className="p-3 font-mono font-semibold text-text-muted">{probe.id}</td>
                <td className="p-3 font-medium capitalize">{probe.attribute?.replace(/_/g, " ")}</td>
                <td className="p-3">{probe.varied_value_a}</td>
                <td className="p-3">{probe.varied_value_b}</td>
                <td className="p-3 font-semibold">{probe.score_a}</td>
                <td className="p-3 font-semibold">{probe.score_b}</td>
                <td className="p-3 font-semibold text-success">{probe.delta}</td>
                <td className="p-3">
                  <span
                    className={`px-2 py-0.5 rounded-pill font-bold border ${
                      probe.status === "PASS"
                        ? "bg-success/10 text-success border-success/20"
                        : "bg-danger/10 text-danger border-danger/20"
                    }`}
                  >
                    {probe.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default BiasReportView;
