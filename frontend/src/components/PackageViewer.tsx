import React, { useEffect, useState } from 'react';
import { getPackage } from '../lib/api';

import { CheckCircle, AlertTriangle, FileText, Download } from 'lucide-react';

interface Props {
  caseId: string;
}

const PackageViewer: React.FC<Props> = ({ caseId }) => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getPackage(caseId)
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [caseId]);

  if (loading) {
    return <div className="animate-pulse bg-slate-800 h-64 rounded-lg"></div>;
  }

  if (!data) {
    return (
      <div className="bg-slate-800 rounded-lg p-6 border border-slate-700 text-center text-slate-400">
        <FileText className="w-12 h-12 mx-auto mb-4 opacity-50" />
        <p>No package generated yet for this case.</p>
      </div>
    );
  }

  // Fallbacks if shape is slightly different
  const { case_id, claims = [], score = null, timeline = [] } = data;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-xl font-bold text-slate-100">Evidence Package</h2>
        <button className="flex items-center space-x-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md transition-colors text-sm font-medium">
          <Download className="w-4 h-4" />
          <span>Export JSON</span>
        </button>
      </div>

      <div className="bg-slate-50 text-slate-900 rounded-lg shadow-lg overflow-hidden border border-slate-200">
        {/* Section 1: Exec Summary */}
        <div className="p-8 border-b border-slate-200">
          <div className="flex justify-between items-start mb-6">
            <div>
              <h1 className="text-3xl font-bold text-slate-900 mb-2">Dispute Defense Package</h1>
              <div className="text-slate-500 font-medium">Case: {case_id}</div>
            </div>
            {score && (
              <div className="text-right">
                <div className="text-sm font-bold uppercase tracking-wider text-slate-500 mb-1">Recommendation</div>
                <div className={`px-4 py-1 rounded-full font-bold text-sm border inline-block
                  ${score.recommendation === 'CONTEST' ? 'bg-green-100 text-green-800 border-green-200' : 
                  'bg-amber-100 text-amber-800 border-amber-200'}`}>
                  {score.recommendation}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Section 2: Identity Verification */}
        <div className="p-8 border-b border-slate-200">
          <h2 className="text-xl font-bold mb-4 flex items-center">
            <CheckCircle className="w-5 h-5 mr-2 text-green-600" />
            Verified Claims
          </h2>
          <div className="space-y-4">
            {claims.map((claim: any, idx: number) => (
              <div key={idx} className={`p-4 rounded-md border ${claim.status === 'BLOCKED' ? 'bg-red-50 border-red-200' : 'bg-white border-slate-200'}`}>
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <p className={`font-medium ${claim.status === 'BLOCKED' ? 'text-red-900' : 'text-slate-800'}`}>
                      {claim.description}
                    </p>
                    {claim.block_reason && (
                      <p className="text-sm text-red-600 mt-1 flex items-center">
                        <AlertTriangle className="w-4 h-4 mr-1" />
                        {claim.block_reason}
                      </p>
                    )}
                  </div>
                  <div className="ml-4 flex flex-wrap justify-end gap-1 w-48">
                    {claim.supporting_evidence_ids?.map((eid: string) => (
                      <span key={eid} className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800 border border-blue-200">
                        [{eid}]
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            ))}
            {claims.length === 0 && (
              <p className="text-slate-500 italic">No claims generated.</p>
            )}
          </div>
        </div>

        {/* Section 3: Timeline */}
        <div className="p-8 border-b border-slate-200">
          <h2 className="text-xl font-bold mb-4">Event Timeline</h2>
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm text-left">
              <thead className="bg-slate-100 text-slate-600 font-semibold border-b border-slate-200">
                <tr>
                  <th className="px-4 py-3">Time</th>
                  <th className="px-4 py-3">Event</th>
                  <th className="px-4 py-3">Evidence</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {timeline.map((ev: any, idx: number) => (
                  <tr key={idx} className="bg-white">
                    <td className="px-4 py-3 font-mono text-xs whitespace-nowrap text-slate-500">
                      {new Date(ev.timestamp).toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-slate-800">{ev.description}</td>
                    <td className="px-4 py-3">
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800 border border-blue-200">
                        [{ev.evidence_id}]
                      </span>
                    </td>
                  </tr>
                ))}
                {timeline.length === 0 && (
                  <tr>
                    <td colSpan={3} className="px-4 py-4 text-center text-slate-500 italic">No timeline events found.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Footer */}
        <div className="bg-slate-800 text-slate-400 p-6 text-xs text-center border-t-4 border-slate-900">
          <p>Razorpay Dispute API Mapping Ready</p>
        </div>
      </div>
    </div>
  );
};

export default PackageViewer;
