import React from "react";
import { useQuery } from "@tanstack/react-query";
import { Award, ShieldCheck, CheckCircle2, AlertCircle, HelpCircle, ExternalLink, Mail, Loader2 } from "lucide-react";
import api from "../../lib/api";
import ScoreBadge from "../../components/ui/ScoreBadge";
import PageHeader from "../../components/ui/PageHeader";

export const CandidatePortal = () => {
  const { data: reports, isLoading, isError, error } = useQuery({
    queryKey: ["my_feedback"],
    queryFn: () => api.get("/me/feedback"),
  });

  return (
    <div className="max-w-4xl mx-auto py-4 space-y-8">
      <PageHeader
        title="Candidate Feedback & Verification Portal"
        subtitle="You are a first-class user of TalentLoop. Here is your explainable evaluation feedback, which you keep."
      />

      {isLoading && (
        <div className="p-12 text-center text-text-muted flex items-center justify-center gap-2">
          <Loader2 className="w-5 h-5 animate-spin text-primary" /> Loading your evaluation reports...
        </div>
      )}

      {isError && (
        <div className="p-6 border border-danger/20 bg-danger/5 rounded-card text-center text-xs text-danger">
          {error?.message || "Failed to load candidate feedback."}
        </div>
      )}

      {reports && reports.length === 0 && (
        <div className="p-12 text-center border border-dashed border-border rounded-card bg-surface/30 space-y-2">
          <Award className="w-8 h-8 text-text-muted mx-auto opacity-50 mb-2" />
          <h4 className="text-base font-semibold text-text">No Released Feedback Reports Yet</h4>
          <p className="text-xs text-text-muted max-w-md mx-auto">
            When recruiters finish evaluating your application, your explainable feedback report and verified credential will appear here.
          </p>
        </div>
      )}

      <div className="space-y-8">
        {reports?.map((report) => {
          return (
            <div
              key={report.id}
              className="bg-bg border border-border rounded-card shadow-sm overflow-hidden divide-y divide-border"
            >
              {/* Header */}
              <div className="p-6 bg-surface flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <span className="text-xs font-semibold uppercase tracking-wider text-text-muted block mb-1">
                    Role Evaluation Report
                  </span>
                  <h2 className="text-xl font-bold text-text">{report.role_title || "Software Engineer"}</h2>
                  <span className="text-xs text-text-muted mt-1 block">
                    Released on {report.released_at ? new Date(report.released_at).toLocaleDateString() : "Recently"}
                  </span>
                </div>

                <div className="flex items-center gap-3">
                  <div className="text-right">
                    <span className="text-xs text-text-muted block">Demonstrated Fit Score</span>
                    <ScoreBadge score={report.score_snapshot} size="lg" showLabel />
                  </div>
                </div>
              </div>

              {/* Fit Summary */}
              <div className="p-6 space-y-2">
                <h3 className="text-xs font-semibold text-text uppercase tracking-wider">Evaluation Summary</h3>
                <p className="text-sm text-text leading-relaxed font-sans">{report.fit_summary}</p>
              </div>

              {/* Evidenced Strengths */}
              <div className="p-6 space-y-3">
                <h3 className="text-xs font-semibold text-success uppercase tracking-wider flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4" />
                  Demonstrated Strengths
                </h3>
                <div className="grid grid-cols-1 gap-2">
                  {report.strengths?.map((item, idx) => (
                    <div key={idx} className="p-3 rounded-control bg-success/10 border border-success/20 text-xs text-text">
                      {item.point}
                    </div>
                  ))}
                </div>
              </div>

              {/* Missing Requirements / Gaps */}
              <div className="p-6 space-y-3">
                <h3 className="text-xs font-semibold text-warning uppercase tracking-wider flex items-center gap-1.5">
                  <HelpCircle className="w-4 h-4" />
                  Missing Requirements for this Specific Role
                </h3>
                <div className="grid grid-cols-1 gap-2">
                  {report.gaps?.map((item, idx) => (
                    <div key={idx} className="p-3 rounded-control bg-warning/10 border border-warning/20 text-xs text-text space-y-1">
                      <p className="font-semibold text-text">{item.point}</p>
                      {item.why_it_mattered && (
                        <p className="text-text-muted text-[11px]">Why it mattered: {item.why_it_mattered}</p>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* Actionable Improvement Advice */}
              <div className="p-6 space-y-3 bg-primary-weak/30">
                <h3 className="text-xs font-semibold text-primary uppercase tracking-wider flex items-center gap-1.5">
                  <Award className="w-4 h-4" />
                  Actionable Steps to Move Into Range
                </h3>
                <ul className="list-disc list-inside text-xs text-text space-y-1.5 pl-1">
                  {report.improve_advice?.map((adv, idx) => (
                    <li key={idx} className="leading-relaxed">
                      {adv}
                    </li>
                  ))}
                </ul>
              </div>

              {/* Credential & Dispute Footer */}
              <div className="p-6 bg-surface flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 text-xs text-text-muted">
                <div className="space-y-1">
                  <div className="flex items-center gap-1.5 text-text font-semibold">
                    <ShieldCheck className="w-4 h-4 text-success" />
                    Cryptographic Credential Anchored
                  </div>
                  {report.credential_hash && (
                    <div className="font-mono text-[11px] text-text-muted truncate max-w-sm">
                      Hash: {report.credential_hash}
                    </div>
                  )}
                  <p className="text-[11px] text-text-muted italic">
                    Note: This evaluation reflects demonstrated evidence for one specific role and is not an assessment of your personal worth.
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  {report.credential_hash && (
                    <a
                      href={`/verify/${report.credential_hash}`}
                      target="_blank"
                      rel="noreferrer"
                      className="px-3 py-1.5 bg-bg border border-border text-text rounded-control hover:bg-border flex items-center gap-1 font-semibold transition-colors"
                    >
                      <ExternalLink className="w-3.5 h-3.5" /> Verify Credential
                    </a>
                  )}
                  <a
                    href="mailto:support@talentloop.dev?subject=Dispute Evaluation"
                    className="px-3 py-1.5 bg-bg border border-border text-text-muted hover:text-text rounded-control flex items-center gap-1 transition-colors"
                  >
                    <Mail className="w-3.5 h-3.5" /> Dispute / Update
                  </a>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default CandidatePortal;
