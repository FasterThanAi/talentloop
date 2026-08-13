import React from "react";
import { AlertTriangle } from "lucide-react";

/**
 * Operational honesty banner.
 *
 * The backend can serve canned AI responses when no GEMINI_API_KEY is set, and can run on
 * SQLite instead of Postgres/pgvector. Both are legitimate for local development and both
 * would be misleading during a demo, so neither is allowed to be invisible.
 *
 * Renders nothing when the environment is fully live.
 */
export const EnvironmentBanner = ({ health }) => {
  if (!health) return null;

  const problems = [];

  if (health.ai_mode === "MOCK") {
    problems.push({
      key: "ai",
      severity: "danger",
      text: "AI MOCK MODE — every model result on screen is canned, not generated. Set GEMINI_API_KEY in backend/.env.",
    });
  }
  if (health.db_dialect && health.db_dialect !== "postgresql") {
    problems.push({
      key: "db",
      severity: "warning",
      text: "Running on SQLite. Switch DATABASE_URL to the Supabase Postgres URI for pgvector search and append-only audit enforcement.",
    });
  } else if (health.vector_backend && health.vector_backend !== "pgvector") {
    problems.push({
      key: "vec",
      severity: "warning",
      text: "pgvector is not active — semantic retrieval is falling back to keyword matching.",
    });
  }
  if (health.db === false) {
    problems.push({
      key: "conn",
      severity: "danger",
      text: "Database unreachable. Nothing will persist.",
    });
  }

  if (problems.length === 0) return null;

  return (
    <div className="flex flex-col">
      {problems.map((p) => (
        <div
          key={p.key}
          className={[
            "flex items-start gap-2 px-6 py-2 text-[12px] leading-snug border-b",
            p.severity === "danger"
              ? "bg-danger/10 border-danger/30 text-danger"
              : "bg-warning/10 border-warning/30 text-warning",
          ].join(" ")}
          role="status"
        >
          <AlertTriangle size={14} className="mt-[1px] shrink-0" />
          <span className="font-medium">{p.text}</span>
        </div>
      ))}
    </div>
  );
};

export default EnvironmentBanner;
