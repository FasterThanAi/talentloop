import React, { useState } from "react";
import { Sparkles, Save, Plus, Trash2, HelpCircle, Check } from "lucide-react";

export const ParsedProfileEditor = ({ profile, onSave, isSaving = false }) => {
  const [formData, setFormData] = useState(profile || {
    role_title: "",
    seniority: "senior",
    must_have_skills: [],
    nice_to_have_skills: [],
    domain_context: "",
    location_constraint: "",
    implicit_signals: [],
    ambiguities: [],
  });

  const handleMustHaveChange = (index, field, value) => {
    const updated = [...formData.must_have_skills];
    updated[index] = { ...updated[index], [field]: value };
    setFormData({ ...formData, must_have_skills: updated });
  };

  const addMustHave = () => {
    setFormData({
      ...formData,
      must_have_skills: [
        ...formData.must_have_skills,
        { skill: "", why_required: "", evidence_of: "" },
      ],
    });
  };

  const removeMustHave = (index) => {
    setFormData({
      ...formData,
      must_have_skills: formData.must_have_skills.filter((_, i) => i !== index),
    });
  };

  const handleSave = (e) => {
    e.preventDefault();
    onSave(formData);
  };

  return (
    <form onSubmit={handleSave} className="space-y-6">
      {/* Header Banner */}
      <div className="p-4 rounded-card bg-surface border border-border flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="p-1.5 rounded-control ai-evidence-chip">
            <Sparkles className="w-4 h-4" />
          </span>
          <div>
            <h4 className="text-sm font-semibold text-text">AI-Parsed Ideal Profile</h4>
            <p className="text-xs text-text-muted">
              Human-in-the-loop: Edit any field below to update authoritative scoring constraints.
            </p>
          </div>
        </div>
        <button
          type="submit"
          disabled={isSaving}
          className="px-4 py-1.5 text-xs font-semibold text-white bg-primary hover:bg-primary/90 rounded-control flex items-center gap-1.5 transition-colors disabled:opacity-50"
        >
          <Save className="w-3.5 h-3.5" />
          {isSaving ? "Saving..." : "Save Profile Edits"}
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-xs font-semibold text-text uppercase tracking-wider mb-1">
            Role Title
          </label>
          <input
            type="text"
            value={formData.role_title}
            onChange={(e) => setFormData({ ...formData, role_title: e.target.value })}
            className="w-full px-3 py-2 border border-border rounded-control text-sm bg-bg text-text focus:ring-2 focus:ring-primary focus:outline-none"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-text uppercase tracking-wider mb-1">
            Seniority Band
          </label>
          <select
            value={formData.seniority}
            onChange={(e) => setFormData({ ...formData, seniority: e.target.value })}
            className="w-full px-3 py-2 border border-border rounded-control text-sm bg-bg text-text focus:ring-2 focus:ring-primary focus:outline-none capitalize"
          >
            {["intern", "junior", "mid", "senior", "lead", "principal"].map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Must-Have Requirements */}
      <div className="p-4 rounded-card border border-border bg-surface/50 space-y-3 ai-evidence-border">
        <div className="flex items-center justify-between">
          <h4 className="text-xs font-semibold text-text uppercase tracking-wider">
            Must-Have Skills & Evidence Criteria (40% Rubric Weight)
          </h4>
          <button
            type="button"
            onClick={addMustHave}
            className="text-xs font-semibold text-primary hover:underline flex items-center gap-1"
          >
            <Plus className="w-3 h-3" /> Add Requirement
          </button>
        </div>

        <div className="space-y-3">
          {formData.must_have_skills.map((item, idx) => (
            <div key={idx} className="p-3 bg-bg border border-border rounded-control space-y-2">
              <div className="flex items-center justify-between gap-2">
                <input
                  type="text"
                  value={item.skill}
                  onChange={(e) => handleMustHaveChange(idx, "skill", e.target.value)}
                  placeholder="Required Skill (e.g. Python / FastAPI)"
                  className="font-medium text-sm text-text w-full bg-transparent border-b border-border pb-1 focus:outline-none focus:border-primary"
                />
                <button
                  type="button"
                  onClick={() => removeMustHave(idx)}
                  className="text-text-muted hover:text-danger p-1"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
                <div>
                  <span className="text-text-muted block mb-0.5">Why Required:</span>
                  <input
                    type="text"
                    value={item.why_required}
                    onChange={(e) => handleMustHaveChange(idx, "why_required", e.target.value)}
                    placeholder="e.g. Core microservices engine"
                    className="w-full p-1.5 border border-border rounded text-text bg-surface/40 focus:outline-none"
                  />
                </div>
                <div>
                  <span className="text-text-muted block mb-0.5">Demonstrable Evidence Of:</span>
                  <input
                    type="text"
                    value={item.evidence_of}
                    onChange={(e) => handleMustHaveChange(idx, "evidence_of", e.target.value)}
                    placeholder="e.g. Deployed API handling real traffic"
                    className="w-full p-1.5 border border-border rounded text-text bg-surface/40 focus:outline-none"
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Domain Context & Location */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-xs font-semibold text-text uppercase tracking-wider mb-1">
            Domain & Industry Context
          </label>
          <input
            type="text"
            value={formData.domain_context}
            onChange={(e) => setFormData({ ...formData, domain_context: e.target.value })}
            className="w-full px-3 py-2 border border-border rounded-control text-sm bg-bg text-text focus:ring-2 focus:ring-primary focus:outline-none"
          />
        </div>
        <div>
          <label className="block text-xs font-semibold text-text uppercase tracking-wider mb-1">
            Location Constraint
          </label>
          <input
            type="text"
            value={formData.location_constraint || ""}
            onChange={(e) => setFormData({ ...formData, location_constraint: e.target.value })}
            className="w-full px-3 py-2 border border-border rounded-control text-sm bg-bg text-text focus:ring-2 focus:ring-primary focus:outline-none"
          />
        </div>
      </div>

      {/* Implicit Signals & Ambiguities */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="p-4 rounded-card border border-border bg-surface/40 space-y-2">
          <span className="text-xs font-semibold text-text uppercase tracking-wider block">
            Implicit Signals Detected
          </span>
          <ul className="list-disc list-inside text-xs text-text-muted space-y-1">
            {formData.implicit_signals && formData.implicit_signals.length > 0 ? (
              formData.implicit_signals.map((sig, i) => <li key={i}>{sig}</li>)
            ) : (
              <li>None detected.</li>
            )}
          </ul>
        </div>

        <div className="p-4 rounded-card border border-warning/30 bg-warning/5 space-y-2">
          <span className="text-xs font-semibold text-warning uppercase tracking-wider flex items-center gap-1">
            <HelpCircle className="w-3.5 h-3.5" /> Ambiguities to Clarify
          </span>
          <ul className="list-disc list-inside text-xs text-text space-y-1">
            {formData.ambiguities && formData.ambiguities.length > 0 ? (
              formData.ambiguities.map((amb, i) => <li key={i}>{amb}</li>)
            ) : (
              <li>No ambiguities detected in job description.</li>
            )}
          </ul>
        </div>
      </div>
    </form>
  );
};

export default ParsedProfileEditor;
