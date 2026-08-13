import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Loader2, AlertCircle } from "lucide-react";
import { useAuth } from "../../context/AuthContext";

/**
 * Landing point after Google sign-in.
 *
 * The backend redirects here with the access token in the URL *fragment*, not the query
 * string — fragments are never sent to a server, so the token cannot leak into access logs
 * or a Referer header. We read it, hand it to AuthContext, then scrub it from the address
 * bar with a replaceState so it does not survive in browser history.
 */
export const AuthCallback = () => {
  const navigate = useNavigate();
  const { adoptToken } = useAuth();
  const [error, setError] = useState(null);

  useEffect(() => {
    const run = async () => {
      const params = new URLSearchParams(window.location.hash.replace(/^#/, ""));
      const token = params.get("access_token");
      const next = params.get("next") || "/requisitions";

      if (!token) {
        setError("No sign-in token was returned. Please try again.");
        return;
      }

      // Remove the token from the URL before anything else can read it.
      window.history.replaceState({}, document.title, "/auth/callback");

      try {
        await adoptToken(token);
        navigate(next, { replace: true });
      } catch (e) {
        setError(e?.message || "Could not complete sign-in.");
      }
    };
    run();
  }, [adoptToken, navigate]);

  return (
    <div className="min-h-screen bg-surface flex items-center justify-center px-4">
      <div className="bg-bg border border-border rounded-card shadow-card px-8 py-10 max-w-sm w-full text-center">
        {error ? (
          <>
            <div className="inline-flex p-2.5 bg-danger/10 text-danger rounded-control mb-3">
              <AlertCircle className="w-5 h-5" />
            </div>
            <p className="text-sm text-text font-medium">Sign-in failed</p>
            <p className="mt-1 text-xs text-text-muted">{error}</p>
            <button
              onClick={() => navigate("/login", { replace: true })}
              className="mt-5 w-full py-2 px-4 rounded-control text-sm font-semibold text-white bg-primary hover:bg-primary/90"
            >
              Back to sign in
            </button>
          </>
        ) : (
          <>
            <Loader2 className="w-6 h-6 animate-spin text-primary mx-auto" />
            <p className="mt-3 text-sm text-text-muted">Completing sign-in…</p>
          </>
        )}
      </div>
    </div>
  );
};

export default AuthCallback;
