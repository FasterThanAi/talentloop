import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Award, CheckCircle2, ShieldAlert, Send, Eye, Loader2 } from "lucide-react";
import api from "../../lib/api";
import PageHeader from "../../components/ui/PageHeader";
import ScoreBadge from "../../components/ui/ScoreBadge";
import StatusPill from "../../components/ui/StatusPill";

export const RecruiterReleaseQueue = () => {
  const queryClient = useQueryClient();
  const [selectedPipelineId, setSelectedPipelineId] = useState(null);
  const [selectedReport, setSelectedReport] = useState(null);

  const { data: entries, isLoading, refetch } = useQuery({
    queryKey: ["pipeline"],
    queryFn: () => api.get("/pipeline"),
  });

  const releaseMutation = useMutation({
    mutationFn: (peId) => api.post(`/pipeline/${peId}/feedback/release`),
    onSuccess: () => {
      queryClient.invalidateQueries(["pipeline"]);
      alert("Feedback report released to candidate portal!");
    },
    onError: (err) => {
      alert(`Release blocked: ${err.message}`);
    },
  });

  const handlePreviewReport = async (pe) => {
    setSelectedPipelineId(pe.id);
    try {
      const fb = await api.get(`/pipeline/${pe.id}/feedback`);
      setSelectedReport(fb);
    } catch (err) {
      alert("Feedback report not yet generated for this candidate.");
    }
  };

  return (
    <div>
      <PageHeader
        title="Candidate Feedback Release Queue"
        subtitle="The Differentiator: Review and release explainable, role-relative feedback reports to candidates."
      />

      {isLoading && (
        <div className="p-12 text-center text-text-muted flex items-center justify-center gap-2">
          <Loader2 className="w-5 h-5 animate-spin text-primary" /> Loading feedback queue...
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Candidates List */}
        <div className="space-y-3">
          <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-2">
            Candidates with Generated Reports
          </h3>

          {entries?.map((pe) => {
            const isSelected = selectedPipelineId === pe.id;

            return (
              <div
                key={pe.id}
                onClick={() => handlePreviewReport(pe)}
                className={`p-4 rounded-card border cursor-pointer transition-all ${
                  isSelected
                    ? "bg-primary-weak/40 border-primary shadow-sm"
                    : "bg-bg border-border hover:bg-surface"
                }`}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <span className="font-semibold text-text text-sm block">
                      {pe.candidate?.full_name || "Candidate"}
                    </span>
                    <span className="text-xs text-text-muted">{pe.candidate?.email}</span>
                  </div>
                  <ScoreBadge score={pe.fit_score} />
                </div>

                <div className="flex items-center justify-between mt-3 pt-2 border-t border-border/50 text-xs">
                  <StatusPill status={pe.stage} />
                  <span className="text-primary font-medium hover:underline flex items-center gap-1">
                    <Eye className="w-3.5 h-3.5" /> Preview Report
                  </span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Report Preview & Release Panel */}
        <div>
          {selectedReport ? (
            <div className="p-6 rounded-card border border-border bg-bg shadow-sm space-y-5 sticky top-6">
              <div className="flex items-center justify-between border-b border-border pb-3">
                <div>
                  <span className="text-xs font-semibold text-text-muted uppercase tracking-wider block">
                    Candidate-Facing Report Preview
                  </span>
                  <span className="text-xs text-text-muted">
                    Status: {selectedReport.released_at ? "Released" : "Unreleased Draft"}
                  </span>
                </div>
                {!selectedReport.released_at && (
                  <button
                    onClick={() => releaseMutation.mutate(selectedPipelineId)}
                    disabled={releaseMutation.isPending}
                    className="px-4 py-1.5 text-xs font-semibold text-white bg-success hover:bg-success/90 rounded-control flex items-center gap-1.5 shadow-sm transition-colors"
                  >
                    <Send className="w-3.5 h-3.5" /> Release to Candidate
                  </button>
                )}
              </div>

              {/* Fit Summary */}
              <div className="p-3 bg-surface rounded-control text-sm text-text leading-relaxed">
                <span className="font-semibold text-xs text-text-muted uppercase tracking-wider block mb-1">
                  Fit Summary (Role-Relative)
                </span>
                {selectedReport.fit_summary}
              </div>

              {/* Strengths */}
              <div>
                <span className="text-xs font-semibold text-success uppercase tracking-wider block mb-2">
                  Evidenced Strengths
                </span>
                <div className="space-y-1.5">
                  {selectedReport.strengths?.map((s, i) => (
                    <div key={i} className="p-2.5 rounded bg-success/10 border border-success/20 text-xs text-text">
                      {s.point}
                    </div>
                  ))}
                </div>
              </div>

              {/* Missing Requirements / Gaps */}
              <div>
                <span className="text-xs font-semibold text-warning uppercase tracking-wider block mb-2">
                  Missing Requirements / Unevidenced Areas
                </span>
                <div className="space-y-1.5">
                  {selectedReport.gaps?.map((g, i) => (
                    <div key={i} className="p-2.5 rounded bg-warning/10 border border-warning/20 text-xs text-text space-y-1">
                      <p className="font-medium">{g.point}</p>
                      {g.why_it_mattered && (
                        <p className="text-text-muted text-[11px]">Why it mattered: {g.why_it_mattered}</p>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* Actionable Improvement Advice */}
              <div>
                <span className="text-xs font-semibold text-primary uppercase tracking-wider block mb-2">
                  Concrete Next Actions
                </span>
                <ul className="list-disc list-inside text-xs text-text space-y-1">
                  {selectedReport.improve_advice?.map((adv, i) => (
                    <li key={i}>{adv}</li>
                  ))}
                </ul>
              </div>
            </div>
          ) : (
            <div className="p-12 text-center border border-dashed border-border rounded-card bg-surface/30">
              <Award className="w-8 h-8 text-text-muted mx-auto opacity-50 mb-2" />
              <h4 className="text-base font-semibold text-text">Select a candidate to preview report</h4>
              <p className="text-xs text-text-muted mt-1">
                Reports are generated automatically after fit scoring and stay unreleased until approved.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default RecruiterReleaseQueue;
