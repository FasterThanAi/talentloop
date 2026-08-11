import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { MessageSquare, RotateCcw, Send, Database, AlertCircle, CheckCircle2, Loader2 } from "lucide-react";
import api from "../../lib/api";
import PageHeader from "../../components/ui/PageHeader";
import StatusPill from "../../components/ui/StatusPill";

export const TriageInbox = () => {
  const queryClient = useQueryClient();
  const [selectedIntent, setSelectedIntent] = useState("");

  const { data: replies, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["replies", selectedIntent],
    queryFn: () => api.get(`/replies${selectedIntent ? `?intent=${selectedIntent}` : ""}`),
  });

  const syncMutation = useMutation({
    mutationFn: () => api.post("/replies/sync"),
    onSuccess: (res) => {
      queryClient.invalidateQueries(["replies"]);
      alert(`Synced and classified ${res.synced_count} candidate replies!`);
    },
  });

  const intents = [
    { label: "All Intents", value: "" },
    { label: "Interested", value: "interested" },
    { label: "Salary Question", value: "salary_question" },
    { label: "Needs Info", value: "needs_info" },
    { label: "Schedule Request", value: "schedule_request" },
    { label: "Not Interested", value: "not_interested" },
    { label: "Auto Reply", value: "auto_reply" },
  ];

  return (
    <div>
      <PageHeader
        title="Reply Triage & Grounded Responses"
        subtitle="Automatic reply intent classification with knowledge-retrieval gated response drafting."
      >
        <button
          onClick={() => syncMutation.mutate()}
          disabled={syncMutation.isPending}
          className="px-3.5 py-1.5 text-xs font-semibold text-text bg-bg border border-border rounded-control hover:bg-surface flex items-center gap-1.5 transition-colors shadow-sm disabled:opacity-50"
        >
          {syncMutation.isPending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RotateCcw className="w-3.5 h-3.5 text-primary" />}
          Sync & Classify Inbound Replies
        </button>
      </PageHeader>

      {/* Filter Tabs */}
      <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
        {intents.map((tab) => (
          <button
            key={tab.value}
            onClick={() => setSelectedIntent(tab.value)}
            className={`px-3 py-1 text-xs font-medium rounded-pill whitespace-nowrap transition-colors ${
              selectedIntent === tab.value
                ? "bg-primary text-white font-semibold"
                : "bg-surface border border-border text-text-muted hover:text-text"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {isLoading && (
        <div className="p-12 text-center text-text-muted flex items-center justify-center gap-2">
          <Loader2 className="w-5 h-5 animate-spin text-primary" /> Loading inbound replies...
        </div>
      )}

      {replies && replies.length === 0 && (
        <div className="p-12 text-center border border-dashed border-border rounded-card bg-surface/30">
          <MessageSquare className="w-8 h-8 text-text-muted mx-auto opacity-50 mb-2" />
          <h4 className="text-base font-semibold text-text">No candidate replies recorded</h4>
          <p className="text-xs text-text-muted mt-1">
            Click "Sync & Classify" to fetch candidate replies from your connected Gmail.
          </p>
        </div>
      )}

      <div className="space-y-4">
        {replies?.map((rep) => {
          const draft = rep.response_draft;

          return (
            <div key={rep.id} className="p-5 rounded-card bg-bg border border-border shadow-sm space-y-4">
              {/* Header */}
              <div className="flex items-center justify-between border-b border-border pb-3">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-sm text-text capitalize">
                    {rep.intent.replace(/_/g, " ")}
                  </span>
                  <span
                    className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded-pill ${
                      rep.priority === "high"
                        ? "bg-danger/10 text-danger border border-danger/30"
                        : "bg-surface text-text-muted border border-border"
                    }`}
                  >
                    {rep.priority} Priority
                  </span>
                  <span className="text-xs text-text-muted capitalize">({rep.sentiment} sentiment)</span>
                </div>
                <span className="text-xs text-text-muted">
                  {new Date(rep.received_at).toLocaleString()}
                </span>
              </div>

              {/* Inbound Message */}
              <div className="p-3 rounded-control bg-surface border border-border">
                <span className="text-xs font-semibold text-text-muted uppercase tracking-wider block mb-1">
                  Candidate Inbound Message:
                </span>
                <p className="text-sm text-text whitespace-pre-wrap">{rep.raw_body}</p>
              </div>

              {/* AI Classification Summary & Suggested Action */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                <div className="p-2.5 rounded bg-primary-weak/40 border border-primary/20">
                  <span className="font-semibold text-primary block mb-0.5">Summary</span>
                  <p className="text-text">{rep.summary}</p>
                </div>
                <div className="p-2.5 rounded bg-success/10 border border-success/20">
                  <span className="font-semibold text-success block mb-0.5">Suggested Action</span>
                  <p className="text-text">{rep.suggested_action}</p>
                </div>
              </div>

              {/* Grounded Response Draft */}
              {draft && (
                <div className="p-4 rounded-control border border-border bg-surface/60 space-y-2 ai-evidence-border">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-text uppercase tracking-wider">
                      RAG-Grounded Draft Response (Approve to Send)
                    </span>
                    {draft.knowledge_used && draft.knowledge_used.length > 0 && (
                      <span className="text-[11px] text-primary flex items-center gap-1">
                        <Database className="w-3 h-3" /> Grounded in {draft.knowledge_used.length} verified company facts
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-text font-sans whitespace-pre-wrap">{draft.body}</p>

                  <div className="pt-2 flex justify-end gap-2">
                    <button
                      onClick={() => alert("Response approved for dispatch!")}
                      className="px-3.5 py-1.5 text-xs font-semibold text-white bg-primary hover:bg-primary/90 rounded-control flex items-center gap-1 shadow-sm"
                    >
                      <Send className="w-3 h-3" /> Approve & Send Response
                    </button>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default TriageInbox;
