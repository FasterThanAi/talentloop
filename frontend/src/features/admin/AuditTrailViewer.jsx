import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ShieldCheck, Database, Filter, Loader2 } from "lucide-react";
import api from "../../lib/api";
import PageHeader from "../../components/ui/PageHeader";
import DataTable from "../../components/ui/DataTable";
import BiasReportView from "./BiasReportView";

export const AuditTrailViewer = () => {
  const [activeTab, setActiveTab] = useState("audit"); // "audit" | "bias"
  const [entityFilter, setEntityFilter] = useState("");

  const { data: auditEvents, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["audit", entityFilter],
    queryFn: () => api.get(`/audit${entityFilter ? `?entity=${entityFilter}` : ""}`),
  });

  const columns = [
    {
      header: "Timestamp",
      accessor: "created_at",
      render: (row) => (
        <span className="text-xs font-mono text-text-muted">
          {new Date(row.created_at).toLocaleString()}
        </span>
      ),
    },
    {
      header: "Action",
      accessor: "action",
      render: (row) => (
        <span className="font-semibold text-xs px-2 py-0.5 rounded-control bg-primary-weak text-primary uppercase tracking-wider">
          {row.action.replace(/_/g, " ")}
        </span>
      ),
    },
    {
      header: "Entity",
      accessor: "entity",
      render: (row) => (
        <div>
          <span className="text-xs font-medium text-text capitalize">{row.entity}</span>
          <span className="text-[10px] text-text-muted block font-mono">{row.entity_id?.slice(0, 10)}...</span>
        </div>
      ),
    },
    {
      header: "Actor ID",
      accessor: "actor_id",
      render: (row) => <span className="text-xs font-mono text-text-muted">{row.actor_id}</span>,
    },
    {
      header: "Payload Diff",
      accessor: "payload",
      render: (row) => (
        <pre className="text-[11px] font-mono text-text bg-surface p-1.5 rounded max-w-xs truncate">
          {JSON.stringify(row.payload)}
        </pre>
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        title="Safety, Fairness & Audit Controls"
        subtitle="Append-only immutable audit trail and programmatic matched-pair bias evaluation suite."
      />

      {/* Tabs */}
      <div className="flex border-b border-border mb-6">
        <button
          onClick={() => setActiveTab("audit")}
          className={`px-4 py-2 text-sm font-semibold border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === "audit"
              ? "border-primary text-primary"
              : "border-transparent text-text-muted hover:text-text"
          }`}
        >
          <Database className="w-4 h-4" /> Immutable Audit Log
        </button>
        <button
          onClick={() => setActiveTab("bias")}
          className={`px-4 py-2 text-sm font-semibold border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === "bias"
              ? "border-primary text-primary"
              : "border-transparent text-text-muted hover:text-text"
          }`}
        >
          <ShieldCheck className="w-4 h-4" /> Matched-Pair Bias Probes (12 Pairs)
        </button>
      </div>

      {activeTab === "audit" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-text-muted uppercase tracking-wider">
              Audit Events (Append-Only)
            </span>
            <div className="flex items-center gap-2">
              <Filter className="w-3.5 h-3.5 text-text-muted" />
              <select
                value={entityFilter}
                onChange={(e) => setEntityFilter(e.target.value)}
                className="px-2.5 py-1 text-xs border border-border rounded-control bg-bg text-text focus:outline-none"
              >
                <option value="">All Entities</option>
                <option value="requisition">Requisition</option>
                <option value="candidate">Candidate</option>
                <option value="pipeline_entry">Pipeline Entry</option>
                <option value="outreach_message">Outreach Message</option>
                <option value="feedback_report">Feedback Report</option>
              </select>
            </div>
          </div>

          <DataTable
            columns={columns}
            data={auditEvents || []}
            isLoading={isLoading}
            isError={isError}
            error={error}
            onRetry={refetch}
            emptyTitle="No audit events recorded"
            emptyDescription="All actions (parse, score, draft, approve, send, release) are automatically audited here."
          />
        </div>
      )}

      {activeTab === "bias" && <BiasReportView />}
    </div>
  );
};

export default AuditTrailViewer;
