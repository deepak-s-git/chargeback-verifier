import React, { useEffect, useState } from 'react';

import ContradictionAlert from './ContradictionAlert';

import type { CaseAnalysisResult } from '../lib/types';

interface Props {
  caseId: string;
}

const CaseDashboard: React.FC<Props> = ({ caseId }) => {
  const [data, setData] = useState<CaseAnalysisResult | null>(null);

  // Mock data for immediate render
  const mockData: CaseAnalysisResult = {
    case_id: caseId,
    score: {
      score: 82,
      factors: [],
      win_probability: 0.85,
      recommendation: 'CONTEST'
    },
    claims: [],
    requirements: [],
    contradictions: [],
    timeline: [],
    summary: [
      "Customer claims unauthorized transaction, but 3D Secure was fully authenticated.",
      "IP address matches customer's typical billing region.",
      "Digital goods were delivered and accessed 5 minutes after purchase."
    ]
  };

  useEffect(() => {
    // In real implementation:
    // getAnalysis(caseId).then(setData);
    setData(mockData);
  }, [caseId]);

  if (!data) return <div className="animate-pulse bg-slate-800 h-64 rounded-lg"></div>;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Score Card */}
        <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
          <h3 className="text-slate-400 text-sm font-medium mb-4">Evidence Score</h3>
          <div className="flex items-end space-x-4 mb-4">
            <span className={`text-5xl font-bold ${data.score.score >= 75 ? 'text-emerald-500' : data.score.score >= 50 ? 'text-amber-500' : 'text-red-500'}`}>
              {data.score.score}
            </span>
            <span className="text-slate-400 text-lg mb-1">/ 100</span>
          </div>
          <div className="mt-4">
            <span className="text-xs text-slate-400 uppercase tracking-wider">Recommendation</span>
            <div className={`mt-1 inline-flex items-center px-3 py-1 rounded-full text-sm font-medium border
              ${data.score.recommendation === 'CONTEST' ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/20' : 
                data.score.recommendation === 'REVIEW' ? 'bg-amber-500/20 text-amber-400 border-amber-500/20' :
                'bg-red-500/20 text-red-400 border-red-500/20'}`}>
              {data.score.recommendation}
            </div>
          </div>
        </div>

        {/* Evidence Breakdown */}
        <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
          <h3 className="text-slate-400 text-sm font-medium mb-4">Evidence Processed</h3>
          <div className="text-4xl font-bold text-slate-100 mb-4">8</div>
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-slate-400">API Logs</span>
              <span className="text-slate-200 font-medium">3</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-slate-400">Emails</span>
              <span className="text-slate-200 font-medium">4</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-slate-400">PDF Receipts</span>
              <span className="text-slate-200 font-medium">1</span>
            </div>
          </div>
        </div>
      </div>

      {data.contradictions.length > 0 && (
        <ContradictionAlert contradictions={data.contradictions} />
      )}

      {/* Key Findings */}
      <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
        <h3 className="text-slate-100 font-medium mb-4">Key Findings</h3>
        <ul className="space-y-3">
          {data.summary.map((point, i) => (
            <li key={i} className="flex items-start">
              <div className="flex-shrink-0 w-1.5 h-1.5 rounded-full bg-blue-500 mt-2 mr-3"></div>
              <span className="text-slate-300">{point}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
};

export default CaseDashboard;
