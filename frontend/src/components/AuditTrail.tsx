import React, { useEffect, useState } from 'react';
import { getAuditTrail } from '../lib/api';
import type { AuditLogEntry } from '../lib/types';
import { Filter, Clock, ChevronDown, ChevronUp, Cpu } from 'lucide-react';

interface Props {
  caseId: string;
}

const AuditTrail: React.FC<Props> = ({ caseId }) => {
  const [entries, setEntries] = useState<AuditLogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterStage, setFilterStage] = useState<string>('ALL');
  const [expandedId, setExpandedId] = useState<string | null>(null);

  useEffect(() => {
    getAuditTrail(caseId)
      .then(setEntries)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [caseId]);

  if (loading) {
    return <div className="animate-pulse bg-slate-800 h-64 rounded-lg"></div>;
  }

  const stages = ['ALL', ...Array.from(new Set(entries.map(e => e.pipeline_stage).filter(Boolean)))];

  const filtered = filterStage === 'ALL' 
    ? entries 
    : entries.filter(e => e.pipeline_stage === filterStage);

  // Sort descending by timestamp
  const sorted = [...filtered].sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());

  const getStageColor = (stage: string) => {
    const stageStr = (stage || '').toUpperCase();
    if (stageStr.includes('INGEST')) return 'bg-blue-500/20 text-blue-400 border-blue-500/20';
    if (stageStr.includes('EXTRACT')) return 'bg-purple-500/20 text-purple-400 border-purple-500/20';
    if (stageStr.includes('VERIF')) return 'bg-green-500/20 text-green-400 border-green-500/20';
    if (stageStr.includes('SCOR')) return 'bg-amber-500/20 text-amber-400 border-amber-500/20';
    if (stageStr.includes('PACKAG')) return 'bg-cyan-500/20 text-cyan-400 border-cyan-500/20';
    return 'bg-slate-500/20 text-slate-400 border-slate-500/20';
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center mb-6 bg-slate-800 p-4 rounded-lg border border-slate-700">
        <h2 className="font-semibold flex items-center">
          <Cpu className="w-5 h-5 mr-2 text-slate-400" />
          AI Decision Audit Log
        </h2>
        <div className="flex items-center space-x-2">
          <Filter className="w-4 h-4 text-slate-400" />
          <select 
            className="bg-slate-900 border border-slate-700 rounded-md text-sm p-1.5 focus:outline-none focus:border-blue-500 text-slate-200"
            value={filterStage}
            onChange={e => setFilterStage(e.target.value)}
          >
            {stages.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
      </div>

      <div className="space-y-3">
        {sorted.map((entry) => (
          <div key={entry.id} className="bg-slate-800 border border-slate-700 rounded-lg overflow-hidden transition-all">
            <div 
              className="p-4 cursor-pointer hover:bg-slate-700/50 flex items-center justify-between"
              onClick={() => setExpandedId(expandedId === entry.id ? null : entry.id)}
            >
              <div className="flex items-center space-x-4">
                <div className="flex flex-col text-slate-400 text-xs w-24">
                  <span className="flex items-center"><Clock className="w-3 h-3 mr-1" /> {new Date(entry.timestamp).toLocaleTimeString()}</span>
                  <span className="text-slate-500 mt-0.5">{new Date(entry.timestamp).toLocaleDateString()}</span>
                </div>
                
                <span className={`px-2 py-0.5 rounded text-xs font-medium border w-24 text-center ${getStageColor(entry.pipeline_stage)}`}>
                  {entry.pipeline_stage || entry.action}
                </span>
                
                <div className="font-medium text-slate-200">{entry.action || entry.details}</div>
              </div>
              
              <div className="flex items-center space-x-6 text-sm">
                {entry.confidence !== undefined && (
                  <div className="flex flex-col items-end">
                    <span className="text-xs text-slate-500">Confidence</span>
                    <span className={entry.confidence > 0.8 ? 'text-green-400' : 'text-amber-400'}>
                      {(entry.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                )}
                
                {entry.latency_ms !== undefined && (
                  <div className="flex flex-col items-end w-16">
                    <span className="text-xs text-slate-500">Latency</span>
                    <span className="text-slate-300 font-mono text-xs">{entry.latency_ms}ms</span>
                  </div>
                )}
                
                <button className="text-slate-400 hover:text-white">
                  {expandedId === entry.id ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                </button>
              </div>
            </div>
            
            {expandedId === entry.id && (
              <div className="bg-slate-900/50 p-4 border-t border-slate-700 text-sm">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <span className="block text-xs text-slate-500 mb-1">Details</span>
                    <p className="text-slate-300 whitespace-pre-wrap">{entry.details || entry.decision}</p>
                  </div>
                  <div>
                    <span className="block text-xs text-slate-500 mb-1">Model / System</span>
                    <p className="text-slate-300 font-mono text-xs bg-slate-950 p-2 rounded border border-slate-800">
                      {entry.model_used || 'system'}
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        ))}
        {sorted.length === 0 && (
          <div className="text-center p-8 text-slate-500">
            No audit logs found for this case.
          </div>
        )}
      </div>
    </div>
  );
};

export default AuditTrail;
