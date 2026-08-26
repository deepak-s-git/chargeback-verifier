import React, { useState } from 'react';
import { AlertTriangle, ChevronDown, ChevronRight } from 'lucide-react';
import type { Contradiction } from '../lib/types';

interface Props {
  contradictions: Contradiction[];
}

const ContradictionAlert: React.FC<Props> = ({ contradictions }) => {
  const [expanded, setExpanded] = useState(false);

  if (!contradictions || contradictions.length === 0) return null;

  const highSeverity = contradictions.some(c => c.severity === 'HIGH');
  const colorClass = highSeverity ? 'border-red-500 bg-red-500/10' : 'border-amber-500 bg-amber-500/10';
  const textColorClass = highSeverity ? 'text-red-400' : 'text-amber-400';
  const iconColorClass = highSeverity ? 'text-red-500' : 'text-amber-500';

  return (
    <div className={`border rounded-lg overflow-hidden ${colorClass}`}>
      <button 
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-4 focus:outline-none"
      >
        <div className="flex items-center space-x-3">
          <AlertTriangle className={`w-6 h-6 ${iconColorClass}`} />
          <div className="text-left">
            <h4 className={`font-semibold ${textColorClass}`}>
              {contradictions.length} Contradiction{contradictions.length > 1 ? 's' : ''} Detected
            </h4>
            {!expanded && (
              <p className="text-sm text-slate-300 mt-1">{contradictions[0].description}</p>
            )}
          </div>
        </div>
        {expanded ? <ChevronDown className={textColorClass} /> : <ChevronRight className={textColorClass} />}
      </button>

      {expanded && (
        <div className="p-4 border-t border-red-500/20 bg-red-900/10 space-y-4">
          {contradictions.map((c, idx) => (
            <div key={c.id || idx} className="bg-slate-900/50 rounded p-4 border border-slate-700/50">
              <div className="flex justify-between mb-2">
                <span className={`text-xs font-bold uppercase px-2 py-0.5 rounded ${c.severity === 'HIGH' ? 'bg-red-500/20 text-red-400' : 'bg-amber-500/20 text-amber-400'}`}>
                  {c.severity} SEVERITY
                </span>
                <span className="text-xs text-slate-400 font-mono">ID: {c.id}</span>
              </div>
              <p className="text-slate-200 mb-3">{c.description}</p>
              <div className="flex space-x-4 text-sm">
                <div className="flex-1 bg-slate-800/80 p-3 rounded border border-slate-700">
                  <span className="text-xs text-slate-400 block mb-1">Claim A (ID: {c.claim_a_id})</span>
                  <div className="text-slate-300">Customer claims card was lost on 2026-08-19</div>
                </div>
                <div className="flex-1 bg-slate-800/80 p-3 rounded border border-slate-700">
                  <span className="text-xs text-slate-400 block mb-1">Claim B (ID: {c.claim_b_id})</span>
                  <div className="text-slate-300">Authentication succeeded with 3D Secure on 2026-08-20 using device fingerprint seen before</div>
                </div>
              </div>
              <div className="mt-3 text-sm">
                <span className="text-slate-400">Sources: </span>
                {c.evidence_ids.map(eid => (
                  <a key={eid} href="#" className="text-blue-400 hover:underline mr-2">{eid}</a>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ContradictionAlert;
