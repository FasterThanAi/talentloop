import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Sparkles, AlertCircle, Loader2 } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import GoogleSignInButton from "../../components/ui/GoogleSignInButton";

export const Login = () => {
  const [email, setEmail] = useState("demo@talentloop.dev");
  const [password, setPassword] = useState("password123");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);
    try {
      const user = await login(email, password);
      if (user.role === "candidate") {
        navigate("/portal");
      } else {
        navigate("/requisitions");
      }
    } catch (err) {
      setError(err.message || "Failed to sign in. Please verify credentials.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-surface flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <div className="inline-flex p-3 bg-primary text-white rounded-control shadow-sm mb-3">
          <Sparkles className="w-6 h-6" />
        </div>
        <h2 className="text-2xl font-bold tracking-tight text-text">Sign in to TalentLoop</h2>
        <p className="mt-1 text-sm text-text-muted">Agentic Hiring Assistant & Candidate Feedback Portal</p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-bg py-8 px-4 shadow-card border border-border sm:rounded-card sm:px-10">
          <form className="space-y-4" onSubmit={handleSubmit}>
            {error && (
              <div className="p-3 bg-danger/10 border border-danger/20 rounded-control flex items-center gap-2 text-xs text-danger">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <div>
              <label className="block text-xs font-semibold text-text uppercase tracking-wider mb-1">
                Email Address
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3 py-2 border border-border rounded-control text-sm bg-bg text-text focus:outline-none focus:ring-2 focus:ring-primary"
                placeholder="recruiter@example.com"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-text uppercase tracking-wider mb-1">
                Password
              </label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3 py-2 border border-border rounded-control text-sm bg-bg text-text focus:outline-none focus:ring-2 focus:ring-primary"
                placeholder="••••••••"
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full mt-2 py-2 px-4 border border-transparent rounded-control shadow-sm text-sm font-semibold text-white bg-primary hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-primary transition-all flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {isLoading && <Loader2 className="w-4 h-4 animate-spin" />}
              {isLoading ? "Signing in..." : "Sign In"}
            </button>
          </form>

          <GoogleSignInButton role="candidate" label="Sign in with Google" />

          {/* Quick Demo Credentials */}
          <div className="mt-6 pt-4 border-t border-border space-y-2">
            <span className="text-xs font-semibold text-text-muted block">Quick Demo Logins:</span>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <button
                type="button"
                onClick={() => {
                  setEmail("demo@talentloop.dev");
                  setPassword("password123");
                }}
                className="p-2 border border-border rounded-control bg-surface hover:bg-border/30 text-left"
              >
                <span className="font-semibold block text-text">Recruiter Demo</span>
                <span className="text-text-muted text-[10px]">demo@talentloop.dev</span>
              </button>
              <button
                type="button"
                onClick={() => {
                  setEmail("alex.rivera@synth.dev");
                  setPassword("password123");
                }}
                className="p-2 border border-border rounded-control bg-surface hover:bg-border/30 text-left"
              >
                <span className="font-semibold block text-text">Candidate Demo</span>
                <span className="text-text-muted text-[10px]">alex.rivera@synth.dev</span>
              </button>
            </div>
          </div>

          <div className="mt-6 text-center text-xs text-text-muted">
            Don't have an organization?{" "}
            <Link to="/register" className="font-semibold text-primary hover:underline">
              Create an account
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
