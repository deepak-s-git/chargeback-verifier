import { useState, useEffect } from "react";
import { Shield, FileText, Clock, CheckCircle, Activity, Package, List } from 'lucide-react';
import type { DisputeCase } from './lib/types';
import CaseList from './components/CaseList';
import CaseDashboard from './components/CaseDashboard';
import EvidenceExplorer from './components/EvidenceExplorer';
import Timeline from './components/Timeline';
import RequirementMatrix from './components/RequirementMatrix';
import ScoreBreakdown from './components/ScoreBreakdown';
import PackageViewer from './components/PackageViewer';
import AuditTrail from './components/AuditTrail';
import NewCaseModal from './components/NewCaseModal';
import { listCases, createCase, loadDemo } from './lib/api';

function App() {
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [isNewCaseModalOpen, setIsNewCaseModalOpen] = useState(false);
  const [cases, setCases] = useState<DisputeCase[]>([]);

  const fetchCases = async () => {
    try {
      const data = await listCases();
      setCases(data);
      if (data.length > 0 && !selectedCaseId) {
        setSelectedCaseId(data[0].id);
      }
    } catch (err) {
      console.error('Failed to fetch cases:', err);
    }
  };

  useEffect(() => {
    fetchCases();
  }, []);

  const handleCreateCase = async (data: any) => {
    try {
      const newCase = await createCase({ merchant_id: 'merchant_123', transaction_id: data.payment_id, amount: data.amount, currency: data.currency, card_network: data.card_network, reason_code: data.reason_code, metadata: { dispute_id: data.dispute_id, respond_by: data.respond_by } } as any);
      await fetchCases();
      setSelectedCaseId(newCase.id);
      setIsNewCaseModalOpen(false);
    } catch (err) {
      console.error('Failed to create case:', err);
    }
  };

  const handleLoadDemo = async () => {
    try {
      await loadDemo();
      await fetchCases();
    } catch (err) {
      console.error('Failed to load demo cases:', err);
    }
  };

  const selectedCase = cases.find(c => c.id === selectedCaseId) || null;

  const tabs = [
    { id: 'overview', label: 'Overview', icon: Activity },
    { id: 'evidence', label: 'Evidence', icon: FileText },
    { id: 'timeline', label: 'Timeline', icon: Clock },
    { id: 'requirements', label: 'Requirements', icon: CheckCircle },
    { id: 'score', label: 'Score', icon: Shield },
    { id: 'package', label: 'Package', icon: Package },
    { id: 'audit', label: 'Audit', icon: List },
  ];

  return (
    <div className="flex h-screen bg-slate-900 text-slate-100 overflow-hidden font-sans">
      {/* Sidebar */}
      <div className="w-80 flex-shrink-0 border-r border-slate-700 bg-slate-800 flex flex-col">
        <div className="p-4 border-b border-slate-700 flex items-center space-x-2">
          <Shield className="w-6 h-6 text-blue-500" />
          <h1 className="text-xl font-bold tracking-tight">DisputeShield</h1>
        </div>
        <div className="p-4 border-b border-slate-700">
          <button 
            onClick={() => setIsNewCaseModalOpen(true)}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-md transition-colors"
          >
            New Case
          </button>
        </div>
        <div className="flex-1 overflow-hidden flex flex-col p-2">
          <CaseList 
            cases={cases} 
            selectedId={selectedCaseId} 
            onSelect={setSelectedCaseId} 
            onLoadDemo={handleLoadDemo} 
          />
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0 bg-slate-900">
        {selectedCase ? (
          <>
            {/* Header */}
            <div className="p-6 border-b border-slate-700 bg-slate-800/50">
              <div className="flex justify-between items-start">
                <div>
                  <div className="flex items-center space-x-3 mb-2">
                    <h2 className="text-2xl font-bold">{selectedCase.dispute_id || selectedCase.id.substring(0, 13)}</h2>
                    <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-500/20 text-blue-400 border border-blue-500/20">
                      {selectedCase.card_network}
                    </span>
                    <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium border uppercase
                      ${selectedCase.status === 'WON' ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/20' :
                        selectedCase.status === 'LOST' ? 'bg-red-500/20 text-red-400 border-red-500/20' :
                        selectedCase.status === 'PACKAGE_READY' ? 'bg-green-500/20 text-green-400 border-green-500/20' :
                        selectedCase.status === 'READY' ? 'bg-blue-500/20 text-blue-400 border-blue-500/20' :
                        'bg-slate-500/20 text-slate-400 border-slate-500/20'}`}>
                      {selectedCase.status.replace('_', ' ')}
                    </span>
                  </div>
                  <div className="text-slate-400 flex items-center space-x-4 text-sm">
                    <span>Payment: {selectedCase.payment_id || 'N/A'}</span>
                    <span>Amount: {selectedCase.currency} {selectedCase.amount.toLocaleString()}</span>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-sm text-slate-400 mb-1">Deadline</div>
                  <div className="font-mono text-amber-400 font-medium bg-amber-400/10 px-3 py-1 rounded border border-amber-400/20">
                    {selectedCase.respond_by ? new Date(selectedCase.respond_by).toLocaleDateString() : 'N/A'}
                  </div>
                </div>
              </div>
            </div>

            {/* Tabs */}
            <div className="border-b border-slate-700 bg-slate-800/30 px-6">
              <div className="flex space-x-6 overflow-x-auto">
                {tabs.map((tab) => {
                  const Icon = tab.icon;
                  return (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id)}
                      className={`flex items-center space-x-2 py-4 border-b-2 font-medium text-sm transition-colors whitespace-nowrap ${
                        activeTab === tab.id
                          ? 'border-blue-500 text-blue-400'
                          : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-500'
                      }`}
                    >
                      <Icon className="w-4 h-4" />
                      <span>{tab.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Tab Content */}
            <div className="flex-1 overflow-y-auto p-6 relative">
              {activeTab === 'overview' && <CaseDashboard caseId={selectedCase.id} />}
              {activeTab === 'evidence' && <EvidenceExplorer caseId={selectedCase.id} />}
              {activeTab === 'timeline' && <Timeline caseId={selectedCase.id} />}
              {activeTab === 'requirements' && <RequirementMatrix caseId={selectedCase.id} />}
              {activeTab === 'score' && <ScoreBreakdown caseId={selectedCase.id} />}
              {activeTab === 'package' && <PackageViewer caseId={selectedCase.id} />}
              {activeTab === 'audit' && <AuditTrail caseId={selectedCase.id} />}
            </div>
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-slate-500">
            <Shield className="w-16 h-16 mb-4 opacity-20" />
            <p className="text-lg">Select a case from the sidebar to view details</p>
          </div>
        )}
      </div>

      <NewCaseModal 
        isOpen={isNewCaseModalOpen} 
        onClose={() => setIsNewCaseModalOpen(false)} 
        onCreate={handleCreateCase}
      />
    </div>
  );
}

export default App;
