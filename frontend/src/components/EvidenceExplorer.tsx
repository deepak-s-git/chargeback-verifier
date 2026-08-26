import React, { useState } from 'react';
import { FileCode, Mail, FileText, CheckCircle, AlertTriangle } from 'lucide-react';

interface Props {
  caseId: string;
}

const EvidenceExplorer: React.FC<Props> = ({}) => {
  const [selectedId, setSelectedId] = useState<string>('e1');

  const evidence = [
    { id: 'e1', type: 'API_LOG', name: 'webhook_payload_auth.json', confidence: 'HIGH', time: '2026-08-25T10:00:00Z', facts: 4 },
    { id: 'e2', type: 'EMAIL', name: 'customer_support_thread.eml', confidence: 'MEDIUM', time: '2026-08-25T11:20:00Z', facts: 2 },
    { id: 'e3', type: 'PDF', name: 'invoice_INV-992.pdf', confidence: 'HIGH', time: '2026-08-25T09:05:00Z', facts: 3 },
  ];

  const getIcon = (type: string) => {
    switch (type) {
      case 'API_LOG': return <FileCode className="w-5 h-5 text-blue-400" />;
      case 'EMAIL': return <Mail className="w-5 h-5 text-purple-400" />;
      case 'PDF': return <FileText className="w-5 h-5 text-red-400" />;
      default: return <FileText className="w-5 h-5 text-slate-400" />;
    }
  };

  return (
    <div className="flex h-full min-h-[600px] border border-slate-700 rounded-lg overflow-hidden bg-slate-800">
      {/* Left Panel - List */}
      <div className="w-1/3 border-r border-slate-700 overflow-y-auto">
        <div className="p-4 border-b border-slate-700 bg-slate-800/80 sticky top-0">
          <h3 className="font-medium text-slate-200">Evidence Sources</h3>
        </div>
        <div className="divide-y divide-slate-700/50">
          {evidence.map(item => (
            <div 
              key={item.id}
              onClick={() => setSelectedId(item.id)}
              className={`p-4 cursor-pointer transition-colors ${selectedId === item.id ? 'bg-blue-900/20 border-l-2 border-blue-500' : 'hover:bg-slate-700/30 border-l-2 border-transparent'}`}
            >
              <div className="flex items-start space-x-3">
                <div className="mt-1">{getIcon(item.type)}</div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-slate-200 truncate">{item.name}</div>
                  <div className="text-xs text-slate-400 mt-1">{new Date(item.time).toLocaleString()}</div>
                  <div className="flex items-center space-x-2 mt-2">
                    <span className="text-xs bg-slate-700 text-slate-300 px-2 py-0.5 rounded">{item.facts} facts</span>
                    {item.confidence === 'HIGH' ? (
                      <span className="text-xs bg-emerald-500/20 text-emerald-400 px-2 py-0.5 rounded flex items-center"><CheckCircle className="w-3 h-3 mr-1"/> High Confidence</span>
                    ) : (
                      <span className="text-xs bg-amber-500/20 text-amber-400 px-2 py-0.5 rounded flex items-center"><AlertTriangle className="w-3 h-3 mr-1"/> Med Confidence</span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Right Panel - Details */}
      <div className="flex-1 flex flex-col bg-slate-900 overflow-hidden">
        <div className="p-4 border-b border-slate-700 bg-slate-800 flex justify-between items-center">
          <h3 className="font-medium text-slate-200">Content & Facts</h3>
          <button className="text-sm bg-slate-700 hover:bg-slate-600 text-slate-200 px-3 py-1.5 rounded transition-colors">
            View Raw Source
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          <div>
            <h4 className="text-sm font-medium text-slate-400 mb-3 uppercase tracking-wider">Extracted Facts</h4>
            <div className="border border-slate-700 rounded-lg overflow-hidden">
              <table className="w-full text-sm text-left">
                <thead className="bg-slate-800 text-slate-300 border-b border-slate-700">
                  <tr>
                    <th className="px-4 py-3 font-medium">Fact Type</th>
                    <th className="px-4 py-3 font-medium">Value</th>
                    <th className="px-4 py-3 font-medium">Confidence</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-700/50 bg-slate-800/30">
                  <tr>
                    <td className="px-4 py-3 text-blue-400 font-mono text-xs">IP_ADDRESS</td>
                    <td className="px-4 py-3 text-slate-200">192.168.1.45</td>
                    <td className="px-4 py-3 text-emerald-400">99%</td>
                  </tr>
                  <tr>
                    <td className="px-4 py-3 text-blue-400 font-mono text-xs">DEVICE_FINGERPRINT</td>
                    <td className="px-4 py-3 text-slate-200">ios_safari_14_2</td>
                    <td className="px-4 py-3 text-emerald-400">95%</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <div>
            <h4 className="text-sm font-medium text-slate-400 mb-3 uppercase tracking-wider">Raw Content Snippet</h4>
            <pre className="bg-slate-950 p-4 rounded-lg overflow-x-auto text-xs text-slate-300 font-mono border border-slate-800">
{`{
  "event": "payment.authorized",
  "data": {
    "payment_id": "pay_ABC123",
    "method": "card",
    "ip": "192.168.1.45",
    "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_2 like Mac OS X)..."
  }
}`}
            </pre>
          </div>
        </div>
      </div>
    </div>
  );
};

export default EvidenceExplorer;
