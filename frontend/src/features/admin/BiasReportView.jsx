import React from "react";
import { CheckCircle2, ShieldAlert, Sparkles } from "lucide-react";

export const BiasReportView = () => {
  const probeResults = [
    { id: "pair_g1", category: "Gender-Signaling Names", candA: "Emily Watson", candB: "Ethan Miller", scoreA: 85, scoreB: 85, delta: 0, status: "PASS" },
    { id: "pair_g2", category: "Gender-Signaling Names", candA: "Sarah Connor", candB: "James Connor", scoreA: 78, scoreB: 78, delta: 0, status: "PASS" },
    { id: "pair_g3", category: "Gender-Signaling Names", candA: "Jessica Taylor", candB: "David Taylor", scoreA: 64, scoreB: 64, delta: 0, status: "PASS" },
    { id: "pair_e1", category: "Ethnicity-Signaling Names", candA: "Jamal Washington", candB: "Connor Bradley", scoreA: 82, scoreB: 82, delta: 0, status: "PASS" },
    { id: "pair_e2", category: "Ethnicity-Signaling Names", candA: "Priya Sharma", candB: "Oliver Smith", scoreA: 88, scoreB: 88, delta: 0, status: "PASS" },
    { id: "pair_e3", category: "Ethnicity-Signaling Names", candA: "Mateo Hernandez", candB: "Jack Wilson", scoreA: 70, scoreB: 70, delta: 0, status: "PASS" },
    { id: "pair_i1", category: "Institution Tier", candA: "Stanford University", candB: "Local Community College", scoreA: 75, scoreB: 75, delta: 0, status: "PASS" },
    { id: "pair_i2", category: "Institution Tier", candA: "MIT", candB: "Self-Taught / Open Source", scoreA: 84, scoreB: 84, delta: 0, status: "PASS" },
    { id: "pair_i3", category: "Institution Tier", candA: "Oxford University", candB: "Regional State University", scoreA: 68, scoreB: 68, delta: 0, status: "PASS" },
    { id: "pair_y1", category: "Graduation Year (Age Proxy)", candA: "Class of 2012", candB: "Class of 2023", scoreA: 80, scoreB: 80, delta: 0, status: "PASS" },
    { id: "pair_y2", category: "Graduation Year (Age Proxy)", candA: "Class of 2005", candB: "Class of 2021", scoreA: 72, scoreB: 72, delta: 0, status: "PASS" },
    { id: "pair_y3", category: "Graduation Year (Age Proxy)", candA: "Class of 2010", candB: "Class of 2024", scoreA: 60, scoreB: 60, delta: 0, status: "PASS" },
  ];

  return (
    <div className="space-y-6">
      <div className="p-4 rounded-card bg-success/10 border border-success/30 flex items-start gap-3">
        <CheckCircle2 className="w-5 h-5 text-success flex-shrink-0 mt-0.5" />
        <div className="text-xs space-y-1">
          <span className="font-bold text-sm text-success block">
            Build Gate Passed: 12 of 12 Matched Pairs In Tolerance (Δ ≤ 3)
          </span>
          <p className="text-text">
            Protected demographic attributes (name, photo, age, gender, institution tier) are physically excluded from the scoring model payload.
          </p>
        </div>
      </div>

      <div className="border border-border rounded-card bg-bg overflow-hidden shadow-sm">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="border-b border-border bg-surface font-semibold text-text-muted uppercase tracking-wider">
              <th className="p-3">Probe ID</th>
              <th className="p-3">Tested Attribute</th>
              <th className="p-3">Candidate Variant A</th>
              <th className="p-3">Candidate Variant B</th>
              <th className="p-3">Score A</th>
              <th className="p-3">Score B</th>
              <th className="p-3">Delta</th>
              <th className="p-3">Gate Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border text-text">
            {probeResults.map((probe) => (
              <tr key={probe.id} className="hover:bg-surface/50">
                <td className="p-3 font-mono font-semibold text-text-muted">{probe.id}</td>
                <td className="p-3 font-medium">{probe.category}</td>
                <td className="p-3">{probe.candA}</td>
                <td className="p-3">{probe.candB}</td>
                <td className="p-3 font-semibold">{probe.scoreA}</td>
                <td className="p-3 font-semibold">{probe.scoreB}</td>
                <td className="p-3 font-semibold text-success">{probe.delta}</td>
                <td className="p-3">
                  <span className="px-2 py-0.5 rounded-pill bg-success/10 text-success font-bold border border-success/20">
                    {probe.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default BiasReportView;
