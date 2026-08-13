import React from "react";
import { useQuery } from "@tanstack/react-query";
import api from "../../lib/api";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api/v1";

const GoogleGlyph = () => (
  <svg width="16" height="16" viewBox="0 0 48 48" aria-hidden="true">
    <path fill="#4285F4" d="M45.1 24.5c0-1.6-.1-3.1-.4-4.5H24v8.5h11.8c-.5 2.7-2 5-4.4 6.6v5.5h7.1c4.1-3.8 6.6-9.4 6.6-16.1z" />
    <path fill="#34A853" d="M24 46c5.9 0 10.9-2 14.5-5.4l-7.1-5.5c-2 1.3-4.5 2.1-7.4 2.1-5.7 0-10.5-3.8-12.2-9H4.5v5.7C8.1 41.1 15.4 46 24 46z" />
    <path fill="#FBBC05" d="M11.8 28.2c-.4-1.3-.7-2.7-.7-4.2s.2-2.9.7-4.2v-5.7H4.5C3 17.1 2.1 20.4 2.1 24s.9 6.9 2.4 9.9l7.3-5.7z" />
    <path fill="#EA4335" d="M24 10.8c3.2 0 6.1 1.1 8.4 3.3l6.3-6.3C34.9 4.2 29.9 2 24 2 15.4 2 8.1 6.9 4.5 14.1l7.3 5.7c1.7-5.2 6.5-9 12.2-9z" />
  </svg>
);

/**
 * Starts the Google identity flow. This asks only for openid/email/profile —
 * mailbox access is a separate, recruiter-only consent requested later from
 * the Gmail Integration screen.
 *
 * Renders nothing when the backend has no Google client configured, so the UI
 * never offers a button that cannot work.
 */
export const GoogleSignInButton = ({ role = "candidate", label = "Continue with Google" }) => {
  const { data } = useQuery({
    queryKey: ["google-status"],
    queryFn: () => api.get("/auth/google/status"),
    staleTime: 5 * 60 * 1000,
    retry: false,
  });

  if (!data?.enabled) return null;

  return (
    <>
      <div className="relative my-5">
        <div className="absolute inset-0 flex items-center">
          <div className="w-full border-t border-border" />
        </div>
        <div className="relative flex justify-center">
          <span className="bg-bg px-2 text-[11px] uppercase tracking-wider text-text-muted">or</span>
        </div>
      </div>

      <a
        href={`${API_BASE_URL}/auth/google/login?role=${role}`}
        className="w-full py-2 px-4 border border-border rounded-control text-sm font-semibold text-text bg-bg hover:bg-surface transition-colors flex items-center justify-center gap-2.5"
      >
        <GoogleGlyph />
        {label}
      </a>

      <p className="mt-2 text-center text-[11px] text-text-muted">
        Signs you in only. We never read your mailbox.
      </p>
    </>
  );
};

export default GoogleSignInButton;
