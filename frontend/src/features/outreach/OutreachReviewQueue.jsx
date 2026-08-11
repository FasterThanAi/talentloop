import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Send, Check, Edit3, ShieldAlert, Sparkles, Loader2, CheckCircle2 } from "lucide-react";
import api from "../../lib/api";
import PageHeader from "../../components/ui/PageHeader";
import StatusPill from "../../components/ui/StatusPill";
import ApprovalBar from "../../components/ui/ApprovalBar";

export const OutreachReviewQueue = () => {
  const queryClient = useQueryClient();
  const [selectedIds, setSelectedIds] = useState([]);
  const [editingId, setEditingId] = useState(null);
  const [editSubject, setEditSubject] = useState("");
  const [editBody, setEditBody] = useState("");

  const { data: messages, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["outreach_messages"],
    queryFn: () => api.get("/outreach"),
  });

  const approveMutation = useMutation({
    mutationFn: (msgId) => api.post(`/outreach/${msgId}/approve`),
    onSuccess: () => {
      queryClient.invalidateQueries(["outreach_messages"]);
    },
  });

  const sendMutation = useMutation({
    mutationFn: (msgId) => api.post(`/outreach/${msgId}/send`),
    onSuccess: () => {
      queryClient.invalidateQueries(["outreach_messages"]);
      alert("Email dispatched successfully via Gmail!");
    },
    onError: (err) => {
      alert(`Send blocked: ${err.message}`);
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ msgId, subject, body }) => api.put(`/outreach/${msgId}`, { subject, body }),
    onSuccess: () => {
      queryClient.invalidateQueries(["outreach_messages"]);
      setEditingId(null);
    },
  });

  const startEdit = (msg) => {
    setEditingId(msg.id);
    setEditSubject(msg.subject);
    setEditBody(msg.body);
  };

  const handleSelectRow = (id) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const handleBulkApprove = async () => {
    for (const id of selectedIds) {
      await approveMutation.mutateAsync(id);
    }
    setSelectedIds([]);
    alert(`Approved ${selectedIds.length} messages!`);
  };

  return (
    <div>
      <PageHeader
        title="Outreach Approval Gate"
        subtitle="Invariant #2: Nothing reaches a candidate without human review and explicit approval."
      />

      {isLoading && (
        <div className="p-12 text-center text-text-muted flex items-center justify-center gap-2">
          <Loader2 className="w-5 h-5 animate-spin text-primary" /> Loading outreach queue...
        </div>
      )}

      {isError && (
        <div className="p-6 border border-danger/20 bg-danger/5 rounded-card text-center text-xs text-danger">
          {error?.message || "Failed to load outreach messages."}
        </div>
      )}

      {messages && messages.length === 0 && (
        <div className="p-12 text-center border border-dashed border-border rounded-card bg-surface/30">
          <Send className="w-8 h-8 text-text-muted mx-auto opacity-50 mb-2" />
          <h4 className="text-base font-semibold text-text">No outreach drafts pending</h4>
          <p className="text-xs text-text-muted mt-1">
            Navigate to the Candidate Pipeline and click "Draft" on any scored candidate.
          </p>
        </div>
      )}

      <div className="space-y-4">
        {messages?.map((msg) => {
          const isDraft = msg.status === "draft";
          const isApproved = msg.status === "approved";
          const isSent = msg.status === "sent";

          return (
            <div
              key={msg.id}
              className={`p-5 rounded-card border transition-all ${
                isSent
                  ? "bg-surface/40 border-border opacity-80"
                  : isApproved
                  ? "bg-primary-weak/20 border-primary/30 shadow-sm"
                  : "bg-bg border-border shadow-sm"
              }`}
            >
              <div className="flex items-start justify-between gap-4 pb-3 border-b border-border">
                <div className="flex items-center gap-3">
                  {isDraft && (
                    <input
                      type="checkbox"
                      checked={selectedIds.includes(msg.id)}
                      onChange={() => handleSelectRow(msg.id)}
                      className="rounded border-border text-primary focus:ring-primary h-4 w-4"
                    />
                  )}
                  <div>
                    <span className="text-xs font-semibold text-text-muted uppercase tracking-wider block">
                      Subject: {msg.subject}
                    </span>
                    <span className="text-xs text-text-muted">
                      Created: {new Date(msg.created_at).toLocaleString()}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <StatusPill status={msg.status} />
                  {isDraft && (
                    <button
                      onClick={() => startEdit(msg)}
                      className="p-1.5 text-text-muted hover:text-text rounded-control hover:bg-surface"
                      title="Edit draft body"
                    >
                      <Edit3 className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>

              {/* Message Body */}
              <div className="py-3">
                {editingId === msg.id ? (
                  <div className="space-y-3">
                    <input
                      type="text"
                      value={editSubject}
                      onChange={(e) => setEditSubject(e.target.value)}
                      className="w-full p-2 text-sm border border-border rounded font-semibold text-text bg-bg"
                    />
                    <textarea
                      rows={4}
                      value={editBody}
                      onChange={(e) => setEditBody(e.target.value)}
                      className="w-full p-2 text-sm border border-border rounded font-sans text-text bg-bg"
                    />
                    <div className="flex justify-end gap-2">
                      <button
                        onClick={() => setEditingId(null)}
                        className="px-3 py-1 text-xs text-text-muted"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={() =>
                          updateMutation.mutate({
                            msgId: msg.id,
                            subject: editSubject,
                            body: editBody,
                          })
                        }
                        className="px-3 py-1 text-xs font-semibold bg-primary text-white rounded"
                      >
                        Save Edits
                      </button>
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-text font-sans leading-relaxed whitespace-pre-wrap ai-evidence-border pl-3">
                    {msg.body}
                  </p>
                )}
              </div>

              {/* Action Buttons */}
              <div className="pt-3 border-t border-border flex items-center justify-between text-xs">
                <div className="text-text-muted">
                  {msg.approved_at && (
                    <span>Approved by {msg.approved_by || "Recruiter"} on {new Date(msg.approved_at).toLocaleTimeString()}</span>
                  )}
                  {msg.sent_at && (
                    <span className="text-success font-semibold flex items-center gap-1">
                      <CheckCircle2 className="w-3.5 h-3.5" /> Dispatched via Gmail ({new Date(msg.sent_at).toLocaleTimeString()})
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  {isDraft && (
                    <button
                      onClick={() => approveMutation.mutate(msg.id)}
                      disabled={approveMutation.isPending}
                      className="px-3.5 py-1.5 font-semibold text-xs text-white bg-success hover:bg-success/90 rounded-control flex items-center gap-1 transition-colors"
                    >
                      <Check className="w-3.5 h-3.5" /> Approve Draft
                    </button>
                  )}
                  {isApproved && (
                    <button
                      onClick={() => sendMutation.mutate(msg.id)}
                      disabled={sendMutation.isPending}
                      className="px-3.5 py-1.5 font-semibold text-xs text-white bg-primary hover:bg-primary/90 rounded-control flex items-center gap-1 transition-colors shadow-sm"
                    >
                      <Send className="w-3.5 h-3.5" /> Send via Gmail
                    </button>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Bulk Approval Bar */}
      <ApprovalBar
        selectedCount={selectedIds.length}
        onApprove={handleBulkApprove}
        onReject={() => setSelectedIds([])}
      />
    </div>
  );
};

export default OutreachReviewQueue;
