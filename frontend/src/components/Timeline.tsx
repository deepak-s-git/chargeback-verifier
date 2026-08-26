import React from 'react';
import { User, Monitor, Store, AlertTriangle } from 'lucide-react';

interface Props {
  caseId: string;
}

const Timeline: React.FC<Props> = ({}) => {
  const events = [
    { id: '1', time: '2026-08-20T14:22:10Z', type: 'PAYMENT_AUTH', desc: 'Payment authorized successfully with 3D Secure', actor: 'CUSTOMER', actor_type: 'CUSTOMER', ip: '192.168.1.45', anomalies: [] },
    { id: '2', time: '2026-08-20T14:22:15Z', type: 'ORDER_CREATED', desc: 'Order #ORD-552 created in system', actor: 'SYSTEM', actor_type: 'SYSTEM', anomalies: [] },
    { id: '3', time: '2026-08-20T14:27:00Z', type: 'DIGITAL_DELIVERY', desc: 'Digital goods access link sent via email', actor: 'SYSTEM', actor_type: 'SYSTEM', anomalies: [] },
    { id: '4', time: '2026-08-20T14:28:30Z', type: 'CONTENT_ACCESSED', desc: 'Digital content downloaded', actor: 'CUSTOMER', actor_type: 'CUSTOMER', ip: '192.168.1.45', anomalies: [] },
    { id: '5', time: '2026-08-25T09:10:00Z', type: 'DISPUTE_CREATED', desc: 'Dispute raised for reason: Fraudulent', actor: 'BANK', actor_type: 'MERCHANT', anomalies: ['SUSPICIOUS_TIMING'] },
  ];

  const getActorIcon = (type: string) => {
    switch (type) {
      case 'CUSTOMER': return <User className="w-4 h-4 text-blue-400" />;
      case 'SYSTEM': return <Monitor className="w-4 h-4 text-emerald-400" />;
      case 'MERCHANT': return <Store className="w-4 h-4 text-purple-400" />;
      default: return <User className="w-4 h-4 text-slate-400" />;
    }
  };

  const getActorColor = (type: string) => {
    switch (type) {
      case 'CUSTOMER': return 'bg-blue-500/20 border-blue-500/30';
      case 'SYSTEM': return 'bg-emerald-500/20 border-emerald-500/30';
      case 'MERCHANT': return 'bg-purple-500/20 border-purple-500/30';
      default: return 'bg-slate-500/20 border-slate-500/30';
    }
  };

  return (
    <div className="max-w-3xl mx-auto py-8">
      <div className="relative border-l-2 border-slate-700 ml-6 space-y-8">
        {events.map((event, _idx) => (
          <div key={event.id} className="relative pl-8">
            {/* Node */}
            <div className={`absolute -left-[17px] top-1 w-8 h-8 rounded-full border-2 flex items-center justify-center bg-slate-900 ${getActorColor(event.actor_type)}`}>
              {getActorIcon(event.actor_type)}
            </div>
            
            {/* Content */}
            <div className="bg-slate-800 rounded-lg p-5 border border-slate-700 shadow-sm hover:border-slate-600 transition-colors">
              <div className="flex justify-between items-start mb-2">
                <div className="flex items-center space-x-3">
                  <span className="font-mono text-sm text-blue-400">{event.type}</span>
                  <span className="text-xs text-slate-400">{new Date(event.time).toLocaleString()}</span>
                </div>
                {event.anomalies.length > 0 && (
                  <div className="flex items-center text-xs font-medium text-red-400 bg-red-500/10 px-2 py-1 rounded border border-red-500/20">
                    <AlertTriangle className="w-3 h-3 mr-1" />
                    {event.anomalies[0]}
                  </div>
                )}
              </div>
              <p className="text-slate-200 mb-3">{event.desc}</p>
              
              <div className="flex items-center space-x-4 text-xs text-slate-400">
                <span className="flex items-center">
                  <span className="font-medium mr-1 text-slate-500">Actor:</span> {event.actor}
                </span>
                {event.ip && (
                  <span className="flex items-center">
                    <span className="font-medium mr-1 text-slate-500">IP:</span> {event.ip}
                  </span>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Timeline;
