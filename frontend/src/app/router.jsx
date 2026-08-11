import React from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import AppShell from "../components/ui/AppShell";
import Login from "../features/auth/Login";
import Register from "../features/auth/Register";
import GmailConnect from "../features/auth/GmailConnect";
import RequisitionList from "../features/requisitions/RequisitionList";
import RequisitionDetail from "../features/requisitions/RequisitionDetail";
import PipelineView from "../features/pipeline/PipelineView";
import OutreachReviewQueue from "../features/outreach/OutreachReviewQueue";
import TriageInbox from "../features/replies/TriageInbox";
import RecruiterReleaseQueue from "../features/feedback/RecruiterReleaseQueue";
import CandidatePortal from "../features/portal/CandidatePortal";
import CredentialVerification from "../features/portal/CredentialVerification";
import AuditTrailViewer from "../features/admin/AuditTrailViewer";

const ProtectedRoute = ({ children, requiredRole }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return <div className="p-8 text-center text-text-muted">Loading authentication state...</div>;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (requiredRole && requiredRole === "recruiter" && user.role !== "recruiter" && user.role !== "admin") {
    return <Navigate to="/portal" replace />;
  }

  return <AppShell>{children}</AppShell>;
};

export const AppRoutes = () => {
  return (
    <Routes>
      {/* Public routes */}
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/verify/:hash" element={<CredentialVerification />} />
      <Route path="/credentials/:hash/verify" element={<CredentialVerification />} />

      {/* Recruiter protected routes */}
      <Route
        path="/requisitions"
        element={
          <ProtectedRoute requiredRole="recruiter">
            <RequisitionList />
          </ProtectedRoute>
        }
      />
      <Route
        path="/requisitions/:id"
        element={
          <ProtectedRoute requiredRole="recruiter">
            <RequisitionDetail />
          </ProtectedRoute>
        }
      />
      <Route
        path="/pipeline"
        element={
          <ProtectedRoute requiredRole="recruiter">
            <PipelineView />
          </ProtectedRoute>
        }
      />
      <Route
        path="/outreach"
        element={
          <ProtectedRoute requiredRole="recruiter">
            <OutreachReviewQueue />
          </ProtectedRoute>
        }
      />
      <Route
        path="/replies"
        element={
          <ProtectedRoute requiredRole="recruiter">
            <TriageInbox />
          </ProtectedRoute>
        }
      />
      <Route
        path="/feedback"
        element={
          <ProtectedRoute requiredRole="recruiter">
            <RecruiterReleaseQueue />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin"
        element={
          <ProtectedRoute requiredRole="recruiter">
            <AuditTrailViewer />
          </ProtectedRoute>
        }
      />
      <Route
        path="/gmail-connect"
        element={
          <ProtectedRoute requiredRole="recruiter">
            <GmailConnect />
          </ProtectedRoute>
        }
      />

      {/* Candidate Portal route */}
      <Route
        path="/portal"
        element={
          <ProtectedRoute>
            <CandidatePortal />
          </ProtectedRoute>
        }
      />

      {/* Default fallback */}
      <Route path="/" element={<Navigate to="/requisitions" replace />} />
      <Route path="*" element={<Navigate to="/requisitions" replace />} />
    </Routes>
  );
};

export default AppRoutes;
