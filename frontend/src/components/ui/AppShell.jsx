import React from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Briefcase,
  Users,
  Send,
  MessageSquare,
  Award,
  ShieldCheck,
  UserCheck,
  Mail,
  LogOut,
  Sparkles,
  Activity,
} from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import api from "../../lib/api";

export const AppShell = ({ children }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const { data: health } = useQuery({
    queryKey: ["health"],
    queryFn: () => api.get("/health"),
    refetchInterval: 30000,
  });

  const isRecruiter = user?.role === "recruiter" || user?.role === "admin";

  const navItems = [
    { label: "Requisitions", path: "/requisitions", icon: Briefcase, recruiterOnly: true },
    { label: "Pipeline & Scores", path: "/pipeline", icon: Users, recruiterOnly: true },
    { label: "Outreach Gate", path: "/outreach", icon: Send, recruiterOnly: true },
    { label: "Reply Inbox", path: "/replies", icon: MessageSquare, recruiterOnly: true },
    { label: "Feedback Release", path: "/feedback", icon: Award, recruiterOnly: true },
    { label: "Safety & Audit", path: "/admin", icon: ShieldCheck, recruiterOnly: true },
    { label: "Gmail Integration", path: "/gmail-connect", icon: Mail, recruiterOnly: true },
    { label: "Candidate Portal", path: "/portal", icon: UserCheck, recruiterOnly: false },
  ];

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className="min-h-screen bg-bg flex flex-col md:flex-row">
      {/* Sidebar */}
      <aside className="w-full md:w-64 bg-surface border-r border-border flex flex-col justify-between p-4 flex-shrink-0">
        <div>
          {/* Logo & Brand */}
          <div className="flex items-center gap-2.5 px-3 py-4 mb-4 border-b border-border">
            <div className="p-2 bg-primary text-white rounded-control shadow-sm">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <span className="font-bold text-base tracking-tight text-text">TalentLoop</span>
              <span className="text-xs text-text-muted block font-medium">Hiring Assistant</span>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="space-y-1">
            {navItems
              .filter((item) => !item.recruiterOnly || isRecruiter)
              .map((item) => {
                const Icon = item.icon;
                const active = location.pathname === item.path || location.pathname.startsWith(`${item.path}/`);

                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={`flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-control transition-colors ${
                      active
                        ? "bg-primary-weak text-primary font-semibold"
                        : "text-text-muted hover:text-text hover:bg-border/40"
                    }`}
                  >
                    <Icon className="w-4 h-4" />
                    <span>{item.label}</span>
                  </Link>
                );
              })}
          </nav>
        </div>

        {/* User & Health Footer */}
        <div className="pt-4 border-t border-border space-y-3">
          {/* Health Indicator */}
          <div className="flex items-center justify-between text-xs text-text-muted px-2">
            <span className="flex items-center gap-1.5">
              <span
                className={`w-2 h-2 rounded-full ${
                  health?.status === "ok" ? "bg-success" : "bg-warning"
                }`}
              />
              System Health
            </span>
            <span className="font-mono text-[10px] uppercase">{health?.status || "Checking..."}</span>
          </div>

          {/* User profile */}
          {user && (
            <div className="p-2.5 rounded-control bg-bg border border-border flex items-center justify-between">
              <div className="truncate">
                <span className="text-xs font-semibold text-text block truncate">{user.email}</span>
                <span className="text-[10px] text-text-muted capitalize font-medium">{user.role} Account</span>
              </div>
              <button
                onClick={handleLogout}
                title="Sign out"
                className="p-1 text-text-muted hover:text-danger rounded-control hover:bg-surface transition-colors"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        <div className="max-w-7xl w-full mx-auto p-6 md:p-8 flex-1">
          {children}
        </div>
      </main>
    </div>
  );
};

export default AppShell;
