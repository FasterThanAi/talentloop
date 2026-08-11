import React, { useState } from "react";
import { Mail, CheckCircle2, ShieldAlert, Loader2, ExternalLink } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import api from "../../lib/api";
import PageHeader from "../../components/ui/PageHeader";

export const GmailConnect = () => {
  const { user } = useAuth();
  const [connecting, setConnecting] = useState(false);

  const handleConnect = async () => {
    setConnecting(true);
    try {
      const res = await api.get("/auth/gmail/connect");
      if (res.auth_url) {
        window.location.href = res.auth_url;
      }
    } catch (err) {
      alert("Failed to initiate Gmail OAuth flow.");
      setConnecting(false);
    }
  };

  const isConnected = Boolean(user?.gmail_email);

  return (
    <div>
      <PageHeader
        title="Gmail OAuth Integration"
        subtitle="Connect a recruiter Gmail account for human-approved candidate outreach and reply triage."
      />

      <div className="max-w-2xl bg-bg border border-border rounded-card p-6 shadow-sm space-y-6">
        <div className="flex items-start gap-4">
          <div className="p-3 bg-primary-weak text-primary rounded-pill">
            <Mail className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-text">Gmail Account Status</h3>
            <p className="text-sm text-text-muted mt-0.5">
              TalentLoop uses strictly bounded permissions (<code>gmail.send</code> and <code>gmail.readonly</code>) to dispatch approved messages.
            </p>
          </div>
        </div>

        {isConnected ? (
          <div className="p-4 rounded-control bg-success/10 border border-success/30 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-success" />
              <div>
                <span className="text-sm font-semibold text-text block">Connected Account</span>
                <span className="text-xs text-text-muted">{user.gmail_email}</span>
              </div>
            </div>
            <button
              onClick={handleConnect}
              className="px-3 py-1.5 text-xs font-semibold text-primary bg-bg border border-border rounded-control hover:bg-surface transition-colors"
            >
              Reconnect
            </button>
          </div>
        ) : (
          <div className="p-4 rounded-control bg-warning/10 border border-warning/30 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ShieldAlert className="w-5 h-5 text-warning" />
              <span className="text-sm font-medium text-text">No Gmail Account Connected (Simulated Mode)</span>
            </div>
            <button
              onClick={handleConnect}
              disabled={connecting}
              className="px-4 py-2 text-xs font-semibold text-white bg-primary hover:bg-primary/90 rounded-control flex items-center gap-1.5 transition-colors disabled:opacity-50"
            >
              {connecting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              Connect Gmail
            </button>
          </div>
        )}

        <div className="border-t border-border pt-4 text-xs text-text-muted space-y-1">
          <p className="font-semibold text-text">Invariant #2 Enforcement:</p>
          <p>• The model drafts candidate outreach, but no email is EVER sent automatically.</p>
          <p>• Every email dispatch requires explicit human approval in the Outreach Gate view.</p>
          <p>• Tokens are encrypted at rest with AES/Fernet encryption.</p>
        </div>
      </div>
    </div>
  );
};

export default GmailConnect;
