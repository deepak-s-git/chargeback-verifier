import React from 'react';
import { CheckCircle, AlertTriangle, XCircle, Ban } from 'lucide-react';
import type { Requirement } from '../lib/types';

interface Props {
  caseId: string;
}

const RequirementMatrix: React.FC<Props> = ({}) => {
  const requirements: Requirement[] = [
    { id: 'req_1', network: 'Visa', requirement_id: 'CE_3.0_SEC_3.2', description: 'Proof of customer identity matching payment details', status: 'SATISFIED', confidence: 0.95, evidence_ids: ['e1', 'e2'] },
    { id: 'req_2', network: 'Visa', requirement_id: 'CE_3.0_SEC_3.3', description: 'Proof of delivery or access to digital goods', status: 'SATISFIED', confidence: 0.88, evidence_ids: ['e4'] },
    { id: 'req_3', network: 'Visa', requirement_id: 'CE_3.0_SEC_3.4', description: 'Device fingerprint match to previous undisputed transaction', status: 'PARTIAL', confidence: 0.65, evidence_ids: ['e1'] },
    { id: 'req_4', network: 'Visa', requirement_id: 'CE_3.0_SEC_3.5', description: 'Terms of service acceptance', status: 'MISSING', confidence: 0, evidence_ids: [] },
  ];

  const getStatusDisplay = (status: string) => {
    switch (status) {
      case 'SATISFIED': return <div className="flex items-center text-emerald-400"><CheckCircle className="w-4 h-4 mr-2"/> Satisfied</div>;
      case 'PARTIAL': return <div className="flex items-center text-amber-400"><AlertTriangle className="w-4 h-4 mr-2"/> Partial</div>;
      case 'MISSING': return <div className="flex items-center text-red-400"><XCircle className="w-4 h-4 mr-2"/> Missing</div>;
      case 'CONTRADICTED': return <div className="flex items-center text-red-500 line-through"><Ban className="w-4 h-4 mr-2"/> Contradicted</div>;
      default: return null;
    }
  };

  return (
    <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
      <div className="p-4 border-b border-slate-700 flex justify-between items-center bg-slate-800/80">
        <h3 className="font-medium text-slate-200">Network Requirements Evaluation</h3>
        <span className="px-3 py-1 bg-blue-500/20 text-blue-400 border border-blue-500/20 rounded-full text-xs font-bold uppercase tracking-wider">
          Visa CE 3.0
        </span>
      </div>
      
      <div className="overflow-x-auto">
        <table className="w-full text-sm text-left">
          <thead className="bg-slate-900/50 text-slate-400 uppercase text-xs tracking-wider border-b border-slate-700">
            <tr>
              <th className="px-6 py-4 font-medium">Requirement ID</th>
              <th className="px-6 py-4 font-medium">Description</th>
              <th className="px-6 py-4 font-medium">Status</th>
              <th className="px-6 py-4 font-medium">Confidence</th>
              <th className="px-6 py-4 font-medium">Evidence Source</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-700/50">
            {requirements.map((req) => (
              <tr key={req.id} className="hover:bg-slate-700/20 transition-colors">
                <td className="px-6 py-4 font-mono text-blue-400 whitespace-nowrap">{req.requirement_id}</td>
                <td className="px-6 py-4 text-slate-200">{req.description}</td>
                <td className="px-6 py-4 whitespace-nowrap">
                  {getStatusDisplay(req.status)}
                </td>
                <td className="px-6 py-4">
                  {req.status !== 'MISSING' ? (
                    <div className="flex items-center">
                      <div className="w-16 h-2 bg-slate-700 rounded-full mr-2 overflow-hidden">
                        <div 
                          className={`h-full rounded-full ${req.confidence > 0.8 ? 'bg-emerald-500' : 'bg-amber-500'}`}
                          style={{ width: `${req.confidence * 100}%` }}
                        ></div>
                      </div>
                      <span className="text-xs text-slate-400">{Math.round(req.confidence * 100)}%</span>
                    </div>
                  ) : (
                    <span className="text-slate-500">-</span>
                  )}
                </td>
                <td className="px-6 py-4">
                  {req.evidence_ids.length > 0 ? (
                    <div className="flex flex-wrap gap-1">
                      {req.evidence_ids.map(eid => (
                        <span key={eid} className="px-2 py-0.5 bg-slate-700 text-slate-300 rounded text-xs font-mono">
                          {eid}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <span className="text-slate-500 italic text-xs">None found</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default RequirementMatrix;
