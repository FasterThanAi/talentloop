import React, { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Sparkles, Users, FileText, Upload, Play, Loader2, CheckCircle2 } from "lucide-react";
import api from "../../lib/api";
import PageHeader from "../../components/ui/PageHeader";
import ParsedProfileEditor from "./ParsedProfileEditor";
import SourcingModal from "../candidates/SourcingModal";
import JobProgress from "../../components/ui/JobProgress";

export const RequisitionDetail = () => {
  const { id } = useParams();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState("parsed"); // "parsed" | "raw"
  const [isSourcingOpen, setIsSourcingOpen] = useState(false);
  const [currentJobId, setCurrentJobId] = useState(null);

  const { data: req, isLoading, refetch } = useQuery({
    queryKey: ["requisition", id],
    queryFn: () => api.get(`/requisitions/${id}`),
  });

  const parseMutation = useMutation({
    mutationFn: () => api.post(`/requisitions/${id}/parse`),
    onSuccess: (res) => {
      queryClient.invalidateQueries(["requisition", id]);
      refetch();
    },
  });

  const scoreMutation = useMutation({
    mutationFn: () => api.post(`/requisitions/${id}/score`),
    onSuccess: (res) => {
      if (res.job_id) {
        setCurrentJobId(res.job_id);
      }
    },
  });

  const updateProfileMutation = useMutation({
    mutationFn: (updatedProfile) =>
      api.put(`/requisitions/${id}`, {
        parsed_profile: updatedProfile,
        title: updatedProfile.role_title,
        seniority: updatedProfile.seniority,
        location: updatedProfile.location_constraint,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries(["requisition", id]);
      alert("Ideal profile updated successfully!");
    },
  });

  if (isLoading) {
    return (
      <div className="p-12 text-center text-text-muted flex items-center justify-center gap-2">
        <Loader2 className="w-5 h-5 animate-spin text-primary" /> Loading requisition details...
      </div>
    );
  }

  if (!req) return <div className="p-8 text-center text-text">Requisition not found.</div>;

  return (
    <div>
      <PageHeader
        title={req.title}
        subtitle={`Requisition #${req.id.slice(0, 8)} • ${req.location || "Remote"} • ${req.candidate_count || 0} candidates in pipeline`}
      >
        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsSourcingOpen(true)}
            className="px-3.5 py-1.5 text-xs font-semibold text-text bg-bg border border-border rounded-control hover:bg-surface flex items-center gap-1.5 transition-colors"
          >
            <Upload className="w-3.5 h-3.5 text-primary" /> Source Candidates
          </button>

          <button
            onClick={() => scoreMutation.mutate()}
            disabled={scoreMutation.isPending || !req.parsed_profile}
            title={
              req.parsed_profile
                ? "Score every candidate in this pipeline against the ideal profile"
                : "Parse the job description first — scoring needs an ideal profile to compare against"
            }
            className="px-3.5 py-1.5 text-xs font-semibold text-white bg-primary hover:bg-primary/90 rounded-control flex items-center gap-1.5 shadow-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {scoreMutation.isPending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
            Score All Candidates
          </button>

          <Link
            to={`/pipeline?requisition_id=${req.id}`}
            className="px-3.5 py-1.5 text-xs font-semibold text-text bg-surface border border-border rounded-control hover:bg-border transition-colors flex items-center gap-1.5"
          >
            <Users className="w-3.5 h-3.5 text-text-muted" /> View Pipeline
          </Link>
        </div>
      </PageHeader>

      {/* Failures here used to be swallowed: the mutation rejected, nothing rendered, and
          the pipeline just stayed "(Unscored)" with no clue why. */}
      {scoreMutation.isError && (
        <div className="mb-4 p-3 rounded-card border border-danger/30 bg-danger/5 text-xs text-danger">
          <span className="font-semibold">Scoring could not start: </span>
          {scoreMutation.error?.message || "Unknown error."}
        </div>
      )}
      {parseMutation.isError && (
        <div className="mb-4 p-3 rounded-card border border-danger/30 bg-danger/5 text-xs text-danger">
          <span className="font-semibold">Parse failed: </span>
          {parseMutation.error?.message || "Unknown error."}
        </div>
      )}

      {/* Background Job Progress Bar */}
      {currentJobId && (
        <JobProgress
          jobId={currentJobId}
          label="Running Explainable Scoring Evaluation on Candidates"
          onCompleted={() => {
            queryClient.invalidateQueries(["requisition", id]);
            queryClient.invalidateQueries(["pipeline"]);
          }}
        />
      )}

      {/* Tabs */}
      <div className="flex border-b border-border mb-6">
        <button
          onClick={() => setActiveTab("parsed")}
          className={`px-4 py-2 text-sm font-semibold border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === "parsed"
              ? "border-primary text-primary"
              : "border-transparent text-text-muted hover:text-text"
          }`}
        >
          <Sparkles className="w-4 h-4" /> Parsed Ideal Profile
        </button>
        <button
          onClick={() => setActiveTab("raw")}
          className={`px-4 py-2 text-sm font-semibold border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === "raw"
              ? "border-primary text-primary"
              : "border-transparent text-text-muted hover:text-text"
          }`}
        >
          <FileText className="w-4 h-4" /> Raw Job Description
        </button>
      </div>

      {activeTab === "parsed" && (
        <div>
          {req.parsed_profile ? (
            <ParsedProfileEditor
              profile={req.parsed_profile}
              onSave={(updated) => updateProfileMutation.mutate(updated)}
              isSaving={updateProfileMutation.isPending}
            />
          ) : (
            <div className="p-12 text-center border border-dashed border-border rounded-card bg-surface/30 space-y-3">
              <Sparkles className="w-8 h-8 text-primary mx-auto opacity-70" />
              <h4 className="text-base font-semibold text-text">Job Description Not Yet Parsed</h4>
              <p className="text-xs text-text-muted max-w-sm mx-auto">
                Run Gemini extraction to structure requirements, must-haves, domain context, and implicit signals.
              </p>
              <button
                onClick={() => parseMutation.mutate()}
                disabled={parseMutation.isPending}
                className="px-4 py-2 text-xs font-semibold text-white bg-primary hover:bg-primary/90 rounded-control inline-flex items-center gap-1.5 transition-colors disabled:opacity-50"
              >
                {parseMutation.isPending && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                Parse Job Description
              </button>
            </div>
          )}
        </div>
      )}

      {activeTab === "raw" && (
        <div className="p-6 rounded-card border border-border bg-bg shadow-sm space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-sm font-semibold text-text">Raw Text Input</h3>
            <button
              onClick={() => parseMutation.mutate()}
              disabled={parseMutation.isPending}
              className="px-3 py-1.5 text-xs font-semibold text-primary bg-primary-weak border border-primary/30 rounded-control hover:bg-primary-weak/80 transition-colors flex items-center gap-1"
            >
              <Sparkles className="w-3.5 h-3.5" /> Re-parse with AI
            </button>
          </div>
          <pre className="p-4 bg-surface rounded-control text-xs text-text whitespace-pre-wrap font-mono leading-relaxed border border-border">
            {req.jd_raw}
          </pre>
        </div>
      )}

      {/* Sourcing Modal */}
      <SourcingModal
        isOpen={isSourcingOpen}
        onClose={() => setIsSourcingOpen(false)}
        requisitionId={req.id}
        onJobStarted={(jobId) => setCurrentJobId(jobId)}
      />
    </div>
  );
};

export default RequisitionDetail;
