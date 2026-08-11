import React, { useState } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Send, FileText, Sparkles, ExternalLink, ShieldAlert, Play, Loader2 } from "lucide-react";
import api from "../../lib/api";
import PageHeader from "../../components/ui/PageHeader";
import DataTable from "../../components/ui/DataTable";
import ScoreBadge from "../../components/ui/ScoreBadge";
import StatusPill from "../../components/ui/StatusPill";
import EvidenceDrawer from "../../components/ui/EvidenceDrawer";

export const PipelineView = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const requisitionId = searchParams.get("requisition_id") || "";
  const queryClient = useQueryClient();

  const [selectedEntryForExplain, setSelectedEntryForExplain] = useState(null);
  const [explainData, setExplainData] = useState(null);
  const [isExplainLoading, setIsExplainLoading] = useState(false);

  // Fetch requisitions for dropdown
  const { data: requisitions } = useQuery({
    queryKey: ["requisitions"],
    queryFn: () => api.get("/requisitions"),
  });

  // Fetch pipeline entries
  const { data: entries, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["pipeline", requisitionId],
    queryFn: () => api.get(`/pipeline${requisitionId ? `?requisition_id=${requisitionId}` : ""}`),
  });

  const draftMutation = useMutation({
    mutationFn: (pipelineId) => api.post(`/pipeline/${pipelineId}/draft`),
    onSuccess: () => {
      queryClient.invalidateQueries(["pipeline"]);
      alert("Personalized outreach message drafted in Outreach Gate!");
    },
  });

  const handleOpenExplain = async (entry) => {
    setSelectedEntryForExplain(entry);
    setIsExplainLoading(true);
    try {
      const data = await api.get(`/pipeline/${entry.id}/explain`);
      setExplainData(data);
    } catch (err) {
      alert("Failed to load score explanation.");
    } finally {
      setIsExplainLoading(false);
    }
  };

  const columns = [
    {
      header: "Candidate",
      accessor: "candidate",
      render: (row) => (
        <div>
          <span className="font-semibold text-text block">{row.candidate?.full_name || "Candidate"}</span>
          <span className="text-xs text-text-muted">{row.candidate?.email}</span>
          {row.candidate?.do_not_contact && (
            <span className="inline-flex items-center gap-1 text-[10px] text-danger font-semibold bg-danger/10 px-1.5 py-0.5 rounded mt-0.5">
              <ShieldAlert className="w-3 h-3" /> Do Not Contact
            </span>
          )}
        </div>
      ),
    },
    {
      header: "Fit Score (0-100)",
      accessor: "fit_score",
      render: (row) => (
        <div className="flex items-center gap-2">
          <ScoreBadge score={row.fit_score} onClick={() => handleOpenExplain(row)} />
        </div>
      ),
    },
    {
      header: "Pipeline Stage",
      accessor: "stage",
      render: (row) => <StatusPill status={row.stage} />,
    },
    {
      header: "Evidence Verified",
      accessor: "candidate.research",
      render: (row) => {
        const skillsCount = row.candidate?.research?.skills?.length || 0;
        const urlsCount = row.candidate?.research?.evidence_urls?.length || 0;
        return (
          <span className="text-xs text-text-muted">
            {skillsCount} claims • {urlsCount} URLs
          </span>
        );
      },
    },
    {
      header: "Actions",
      accessor: "id",
      render: (row) => (
        <div className="flex items-center gap-2">
          <button
            onClick={() => handleOpenExplain(row)}
            className="px-2.5 py-1 text-xs font-medium text-text bg-surface border border-border rounded-control hover:bg-border/40 transition-colors"
          >
            Explain
          </button>
          <button
            onClick={() => draftMutation.mutate(row.id)}
            disabled={draftMutation.isPending || row.candidate?.do_not_contact}
            className="px-2.5 py-1 text-xs font-semibold text-primary bg-primary-weak border border-primary/30 rounded-control hover:bg-primary-weak/80 transition-colors flex items-center gap-1 disabled:opacity-40"
          >
            <Send className="w-3 h-3" /> Draft
          </button>
        </div>
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        title="Candidate Pipeline & Rankings"
        subtitle="Transparent evaluation rankings with verifiable citations and one-click evidence audit."
      >
        <div className="flex items-center gap-2">
          <select
            value={requisitionId}
            onChange={(e) => setSearchParams(e.target.value ? { requisition_id: e.target.value } : {})}
            className="px-3 py-1.5 text-xs font-medium border border-border rounded-control bg-bg text-text focus:ring-2 focus:ring-primary focus:outline-none"
          >
            <option value="">All Requisitions</option>
            {requisitions?.map((r) => (
              <option key={r.id} value={r.id}>
                {r.title}
              </option>
            ))}
          </select>
        </div>
      </PageHeader>

      <DataTable
        columns={columns}
        data={entries || []}
        isLoading={isLoading}
        isError={isError}
        error={error}
        onRetry={refetch}
        emptyTitle="No candidates in pipeline"
        emptyDescription="Source candidates from CSV, URLs, or the RizeOS pool to evaluate them."
      />

      {/* Evidence Drawer for explainability */}
      <EvidenceDrawer
        isOpen={Boolean(explainData)}
        onClose={() => setExplainData(null)}
        explainData={explainData}
      />
    </div>
  );
};

export default PipelineView;
