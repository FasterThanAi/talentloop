import React from "react";
import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ShieldCheck, AlertCircle, CheckCircle2, ArrowLeft, Loader2 } from "lucide-react";
import api from "../../lib/api";

export const CredentialVerification = () => {
  const { hash } = useParams();

  const { data: result, isLoading, isError, error } = useQuery({
    queryKey: ["credential_verify", hash],
    queryFn: () => api.get(`/credentials/${hash}/verify`),
    enabled: Boolean(hash),
  });

  return (
    <div className="min-h-screen bg-surface flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-lg">
        <div className="text-center mb-6">
          <div className="inline-flex p-3 bg-primary text-white rounded-control shadow-sm mb-3">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-text">TalentLoop Credential Verification</h1>
          <p className="mt-1 text-sm text-text-muted">Public, unauthenticated cryptographic verification check.</p>
        </div>

        <div className="bg-bg p-8 shadow-card border border-border rounded-card space-y-6">
          {isLoading && (
            <div className="p-8 text-center text-text-muted flex items-center justify-center gap-2">
              <Loader2 className="w-5 h-5 animate-spin text-primary" /> Verifying cryptographic hash...
            </div>
          )}

          {isError && (
            <div className="p-4 bg-danger/10 text-danger text-xs rounded-control flex items-center gap-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>Failed to verify credential: {error?.message}</span>
            </div>
          )}

          {result && (
            <div className="space-y-4">
              <div
                className={`p-4 rounded-control border flex items-center gap-3 ${
                  result.verified
                    ? "bg-success/10 border-success/30 text-success"
                    : "bg-warning/10 border-warning/30 text-warning"
                }`}
              >
                {result.verified ? <CheckCircle2 className="w-6 h-6 flex-shrink-0" /> : <AlertCircle className="w-6 h-6 flex-shrink-0" />}
                <div>
                  <h3 className="text-base font-bold">
                    {result.verified ? "Cryptographic Credential Verified" : "Unverified or Revoked Credential"}
                  </h3>
                  <p className="text-xs text-text-muted">
                    {result.verified
                      ? "The evaluation payload matches the deterministic hash issued by the hiring organization."
                      : "This hash does not match an active released evaluation."}
                  </p>
                </div>
              </div>

              <div className="space-y-2 text-xs border-t border-border pt-4 text-text">
                <div>
                  <span className="text-text-muted block font-mono">Payload SHA-256 Hash:</span>
                  <span className="font-mono text-text break-all bg-surface p-1.5 rounded block">{result.payload_hash}</span>
                </div>
                {result.tx_hash && (
                  <div>
                    <span className="text-text-muted block font-mono">Blockchain Transaction:</span>
                    <span className="font-mono text-text break-all bg-surface p-1.5 rounded block">{result.tx_hash}</span>
                  </div>
                )}
                <div className="flex justify-between py-1">
                  <span className="text-text-muted">Network:</span>
                  <span className="font-semibold">{result.network}</span>
                </div>
                {result.issued_at && (
                  <div className="flex justify-between py-1">
                    <span className="text-text-muted">Issued At:</span>
                    <span>{new Date(result.issued_at).toLocaleString()}</span>
                  </div>
                )}
              </div>
            </div>
          )}

          <div className="pt-4 border-t border-border flex justify-center">
            <Link
              to="/login"
              className="text-xs font-semibold text-primary hover:underline flex items-center gap-1"
            >
              <ArrowLeft className="w-3.5 h-3.5" /> Back to TalentLoop Home
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CredentialVerification;
