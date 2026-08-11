import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Briefcase, Sparkles, Users, ArrowRight, Loader2 } from "lucide-react";
import api from "../../lib/api";
import PageHeader from "../../components/ui/PageHeader";
import DataTable from "../../components/ui/DataTable";
import StatusPill from "../../components/ui/StatusPill";

export const RequisitionList = () => {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [isCreating, setIsCreating] = useState(false);
  const [title, setTitle] = useState("");
  const [jdRaw, setJdRaw] = useState("");

  const { data: requisitions, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["requisitions"],
    queryFn: () => api.get("/requisitions"),
  });

  const createMutation = useMutation({
    mutationFn: (newReq) => api.post("/requisitions", newReq),
    onSuccess: (created) => {
      queryClient.invalidateQueries(["requisitions"]);
      setIsCreating(false);
      setTitle("");
      setJdRaw("");
      navigate(`/requisitions/${created.id}`);
    },
  });

  const handleCreate = (e) => {
    e.preventDefault();
    if (!title || !jdRaw) return;
    createMutation.mutate({ title, jd_raw: jdRaw });
  };

  const columns = [
    {
      header: "Role Title",
      accessor: "title",
      render: (row) => (
        <div>
          <Link to={`/requisitions/${row.id}`} className="font-semibold text-text hover:text-primary transition-colors">
            {row.title}
          </Link>
          <span className="text-xs text-text-muted block mt-0.5">
            {row.location || "Remote"} • Created {new Date(row.created_at).toLocaleDateString()}
          </span>
        </div>
      ),
    },
    {
      header: "Status",
      accessor: "status",
      render: (row) => <StatusPill status={row.status} />,
    },
    {
      header: "Candidates in Pipeline",
      accessor: "candidate_count",
      render: (row) => (
        <span className="inline-flex items-center gap-1.5 font-medium text-text">
          <Users className="w-3.5 h-3.5 text-text-muted" />
          {row.candidate_count || 0}
        </span>
      ),
    },
    {
      header: "Actions",
      accessor: "id",
      render: (row) => (
        <div className="flex items-center gap-2">
          <Link
            to={`/requisitions/${row.id}`}
            className="px-3 py-1.5 text-xs font-semibold text-text bg-surface border border-border rounded-control hover:bg-border/30 transition-colors inline-flex items-center gap-1"
          >
            Manage <ArrowRight className="w-3 h-3" />
          </Link>
          <Link
            to={`/pipeline?requisition_id=${row.id}`}
            className="px-3 py-1.5 text-xs font-semibold text-primary bg-primary-weak border border-primary/20 rounded-control hover:bg-primary-weak/80 transition-colors"
          >
            Pipeline
          </Link>
        </div>
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        title="Requisitions & Roles"
        subtitle="Manage job descriptions, parse ideal candidate profiles with AI, and source talent pools."
      >
        <button
          onClick={() => setIsCreating(!isCreating)}
          className="px-4 py-2 text-xs font-semibold text-white bg-primary hover:bg-primary/90 rounded-control flex items-center gap-1.5 shadow-sm transition-all active:scale-95"
        >
          <Plus className="w-4 h-4" />
          New Requisition
        </button>
      </PageHeader>

      {/* Inline Create Form */}
      {isCreating && (
        <div className="p-6 mb-6 rounded-card border border-primary/30 bg-surface shadow-sm space-y-4">
          <h3 className="text-base font-semibold text-text flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-primary" />
            Create New Requisition
          </h3>
          <form onSubmit={handleCreate} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-text uppercase tracking-wider mb-1">
                Job Title
              </label>
              <input
                type="text"
                required
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Senior Backend Engineer (Python / FastAPI)"
                className="w-full px-3 py-2 border border-border rounded-control text-sm bg-bg text-text focus:ring-2 focus:ring-primary focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-text uppercase tracking-wider mb-1">
                Raw Job Description Text
              </label>
              <textarea
                required
                rows={6}
                value={jdRaw}
                onChange={(e) => setJdRaw(e.target.value)}
                placeholder="Paste the full job description text here..."
                className="w-full px-3 py-2 border border-border rounded-control text-sm bg-bg text-text focus:ring-2 focus:ring-primary focus:outline-none"
              />
            </div>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setIsCreating(false)}
                className="px-4 py-2 text-xs font-medium text-text-muted hover:text-text"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={createMutation.isPending}
                className="px-4 py-2 text-xs font-semibold text-white bg-primary hover:bg-primary/90 rounded-control flex items-center gap-1.5 transition-colors disabled:opacity-50"
              >
                {createMutation.isPending && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                Create & Open
              </button>
            </div>
          </form>
        </div>
      )}

      <DataTable
        columns={columns}
        data={requisitions || []}
        isLoading={isLoading}
        isError={isError}
        error={error}
        onRetry={refetch}
        emptyTitle="No requisitions yet"
        emptyDescription="Create your first job requisition to start AI-powered ideal profile parsing."
      />
    </div>
  );
};

export default RequisitionList;
