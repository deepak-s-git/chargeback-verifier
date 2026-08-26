import React from 'react';
import type { DisputeCase } from '../lib/types';
import { Loader2 } from 'lucide-react';

interface Props {
  cases: DisputeCase[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onLoadDemo: () => void;
}

const CaseList: React.FC<Props> = ({ cases, selectedId, onSelect, onLoadDemo }) => {
  const [loading, setLoading] = React.useState(false);

  const handleLoadDemo = async () => {
    setLoading(true);
    await onLoadDemo();
    setLoading(false);
  };

  const getStatusColor = (status: string) => {
    const s = (status || '').toUpperCase();
    if (s === 'OPEN') return 'bg-slate-500/20 text-slate-400 border-slate-500/20';
    if (s === 'ANALYZING') return 'bg-blue-500/20 text-blue-400 border-blue-500/20';
    if (s === 'REVIEW_REQUIRED') return 'bg-amber-500/20 text-amber-400 border-amber-500/20';
    if (s === 'PACKAGE_READY' || s === 'READY') return 'bg-green-500/20 text-green-400 border-green-500/20';
    if (s === 'WON') return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/20';
    if (s === 'LOST') return 'bg-red-500/20 text-red-400 border-red-500/20';
    return 'bg-slate-500/20 text-slate-400 border-slate-500/20';
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto space-y-2 pb-4">
        {cases.map((c) => (
          <div
            key={c.id}
            onClick={() => onSelect(c.id)}
            className={`p-3 rounded-lg cursor-pointer transition-all border ${
              selectedId === c.id
                ? 'bg-blue-900/30 border-blue-500'
                : 'bg-slate-800 border-transparent hover:border-slate-600'
            }`}
          >
            <div className="flex justify-between items-start mb-2">
              <span className="font-medium text-slate-200">
                {c.id.substring(0, 13)}
              </span>
              <span className={`px-2 py-0.5 rounded text-[10px] font-bold border uppercase ${getStatusColor(c.status)}`}>
                {c.status.replace('_', ' ')}
              </span>
            </div>
            
            <div className="flex items-center justify-between text-sm">
              <span className="text-slate-400 font-medium">
                {c.currency} {c.amount.toLocaleString()}
              </span>
              <div className="flex items-center justify-center w-5 h-5 rounded-full bg-slate-700 text-[10px] font-bold text-white">
                {c.card_network?.charAt(0).toUpperCase() || 'V'}
              </div>
            </div>
            
            {c.dispute_id && (
              <div className="mt-2 text-xs text-slate-500">
                Ref: {c.dispute_id}
              </div>
            )}
          </div>
        ))}
        {cases.length === 0 && (
          <div className="text-center p-4 text-slate-500 text-sm">
            No cases found
          </div>
        )}
      </div>
      
      <div className="pt-4 border-t border-slate-700 mt-auto">
        <button
          onClick={handleLoadDemo}
          disabled={loading}
          className="w-full flex items-center justify-center space-x-2 bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium py-2 px-4 rounded-md transition-colors border border-slate-600"
        >
          {loading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Loading...</span>
            </>
          ) : (
            <span>Load Demo Cases</span>
          )}
        </button>
      </div>
    </div>
  );
};

export default CaseList;
