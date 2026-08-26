import React from 'react';
import { Shield, TrendingUp } from 'lucide-react';
import type { ScoringFactor } from '../lib/types';

interface Props {
  caseId: string;
}

const ScoreBreakdown: React.FC<Props> = ({}) => {
  const score = 82;
  const factors: ScoringFactor[] = [
    { name: '3D Secure Authentication', points: 30, type: 'POSITIVE', evidence_ids: ['e1'] },
    { name: 'IP matches Billing Zip', points: 15, type: 'POSITIVE', evidence_ids: ['e1'] },
    { name: 'Digital Delivery Confirmed', points: 20, type: 'POSITIVE', evidence_ids: ['e3'] },
    { name: 'Prior Undisputed Transaction', points: 25, type: 'POSITIVE', evidence_ids: ['e4'] },
    { name: 'Terms of Service Missing', points: -5, type: 'MISSING', evidence_ids: [] },
    { name: 'Timing Anomaly (Immediate Use)', points: -3, type: 'NEGATIVE', evidence_ids: ['e1'] },
  ];

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Top Section */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-slate-800 p-8 rounded-lg border border-slate-700 flex flex-col items-center justify-center text-center">
          <div className="relative w-48 h-48 flex items-center justify-center mb-4">
            <svg className="w-full h-full transform -rotate-90 absolute top-0 left-0">
              <circle cx="96" cy="96" r="88" stroke="currentColor" strokeWidth="12" fill="transparent" className="text-slate-700" />
              <circle cx="96" cy="96" r="88" stroke="currentColor" strokeWidth="12" fill="transparent" className="text-emerald-500" strokeDasharray="552.9" strokeDashoffset={552.9 - (552.9 * score) / 100} strokeLinecap="round" />
            </svg>
            <div className="flex flex-col items-center">
              <span className="text-6xl font-bold text-emerald-500">{score}</span>
              <span className="text-slate-400 text-sm mt-1">out of 100</span>
            </div>
          </div>
          <h2 className="text-xl font-bold text-slate-100 mb-2">Recommendation: CONTEST</h2>
          <p className="text-sm text-slate-400">High likelihood of winning based on compelling evidence matrix.</p>
        </div>

        <div className="space-y-6">
          <div className="bg-slate-800 p-6 rounded-lg border border-slate-700">
            <h3 className="flex items-center text-slate-200 font-medium mb-4"><TrendingUp className="w-5 h-5 mr-2 text-blue-500"/> Win Probability Calibration</h3>
            <div className="text-4xl font-bold text-slate-100 mb-2">85%</div>
            <p className="text-sm text-slate-400">Historical win rate for cases with similar evidence profiles and reason codes.</p>
          </div>

          <div className="bg-slate-800 p-6 rounded-lg border border-slate-700">
            <h3 className="flex items-center text-slate-200 font-medium mb-4"><Shield className="w-5 h-5 mr-2 text-purple-500"/> Cost/Benefit Analysis</h3>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-slate-400">Dispute Amount:</span>
                <span className="text-slate-200 font-medium">₹5,000</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Arbitration Fees (if lost):</span>
                <span className="text-slate-200 font-medium">₹15,000</span>
              </div>
              <div className="flex justify-between pt-2 border-t border-slate-700">
                <span className="text-slate-300 font-medium">Expected Value of Contesting:</span>
                <span className="text-emerald-400 font-bold">+ ₹3,500</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Factor Breakdown */}
      <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
        <div className="p-4 border-b border-slate-700 bg-slate-800/80">
          <h3 className="font-medium text-slate-200">Scoring Factor Breakdown</h3>
        </div>
        <div className="p-6 space-y-4">
          {factors.map((factor, idx) => (
            <div key={idx} className="flex items-center justify-between">
              <div className="flex-1 mr-6">
                <div className="flex justify-between mb-1">
                  <span className="text-sm font-medium text-slate-200">{factor.name}</span>
                  <span className={`text-sm font-bold ${factor.points > 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                    {factor.points > 0 ? '+' : ''}{factor.points}
                  </span>
                </div>
                <div className="w-full h-2 bg-slate-700 rounded-full overflow-hidden">
                  <div 
                    className={`h-full rounded-full ${factor.type === 'POSITIVE' ? 'bg-emerald-500' : factor.type === 'NEGATIVE' ? 'bg-red-500' : 'bg-slate-500'}`}
                    style={{ width: `${Math.min(Math.abs(factor.points) * 2, 100)}%` }}
                  ></div>
                </div>
              </div>
              <div className="w-24 text-right">
                {factor.evidence_ids.length > 0 ? (
                  <div className="flex justify-end gap-1 flex-wrap">
                    {factor.evidence_ids.map(eid => (
                      <span key={eid} className="px-1.5 py-0.5 bg-slate-700 text-slate-300 rounded text-[10px] font-mono">
                        {eid}
                      </span>
                    ))}
                  </div>
                ) : (
                  <span className="text-[10px] text-slate-500 uppercase">No Evidence</span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default ScoreBreakdown;
