import React, { useState } from 'react';
import { X, UploadCloud } from 'lucide-react';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onCreate: (data: any) => void;
}

const NewCaseModal: React.FC<Props> = ({ isOpen, onClose, onCreate }) => {
  const [formData, setFormData] = useState({
    dispute_id: '',
    payment_id: '',
    amount: '',
    currency: 'INR',
    reason_code: '10.4',
    card_network: 'VISA',
    respond_by: ''
  });

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onCreate({
      ...formData,
      amount: parseFloat(formData.amount)
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/80 backdrop-blur-sm p-4">
      <div className="bg-slate-800 rounded-xl shadow-2xl w-full max-w-lg border border-slate-700 overflow-hidden flex flex-col max-h-[90vh]">
        <div className="px-6 py-4 border-b border-slate-700 flex justify-between items-center bg-slate-800/50">
          <h2 className="text-xl font-bold text-slate-100">Create New Case</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-white transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>
        
        <div className="p-6 overflow-y-auto">
          <form id="new-case-form" onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1">
                <label className="text-sm font-medium text-slate-300">Dispute ID</label>
                <input 
                  required
                  type="text" 
                  value={formData.dispute_id}
                  onChange={e => setFormData({...formData, dispute_id: e.target.value})}
                  className="w-full bg-slate-900 border border-slate-700 rounded-md px-3 py-2 text-slate-200 focus:outline-none focus:border-blue-500" 
                  placeholder="e.g. DSP-1234"
                />
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium text-slate-300">Payment ID</label>
                <input 
                  required
                  type="text" 
                  value={formData.payment_id}
                  onChange={e => setFormData({...formData, payment_id: e.target.value})}
                  className="w-full bg-slate-900 border border-slate-700 rounded-md px-3 py-2 text-slate-200 focus:outline-none focus:border-blue-500" 
                  placeholder="e.g. pay_XYZ"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1">
                <label className="text-sm font-medium text-slate-300">Amount</label>
                <input 
                  required
                  type="number" 
                  step="0.01"
                  value={formData.amount}
                  onChange={e => setFormData({...formData, amount: e.target.value})}
                  className="w-full bg-slate-900 border border-slate-700 rounded-md px-3 py-2 text-slate-200 focus:outline-none focus:border-blue-500" 
                  placeholder="0.00"
                />
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium text-slate-300">Currency</label>
                <select 
                  value={formData.currency}
                  onChange={e => setFormData({...formData, currency: e.target.value})}
                  className="w-full bg-slate-900 border border-slate-700 rounded-md px-3 py-2 text-slate-200 focus:outline-none focus:border-blue-500"
                >
                  <option value="INR">INR</option>
                  <option value="USD">USD</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1">
                <label className="text-sm font-medium text-slate-300">Card Network</label>
                <div className="flex space-x-4 pt-1">
                  <label className="flex items-center space-x-2 cursor-pointer text-slate-300">
                    <input 
                      type="radio" 
                      name="network" 
                      value="VISA" 
                      checked={formData.card_network === 'VISA'}
                      onChange={e => setFormData({...formData, card_network: e.target.value})}
                      className="text-blue-500 bg-slate-900 border-slate-700 focus:ring-blue-500 focus:ring-offset-slate-800"
                    />
                    <span>Visa</span>
                  </label>
                  <label className="flex items-center space-x-2 cursor-pointer text-slate-300">
                    <input 
                      type="radio" 
                      name="network" 
                      value="MASTERCARD" 
                      checked={formData.card_network === 'MASTERCARD'}
                      onChange={e => setFormData({...formData, card_network: e.target.value})}
                      className="text-blue-500 bg-slate-900 border-slate-700 focus:ring-blue-500 focus:ring-offset-slate-800"
                    />
                    <span>Mastercard</span>
                  </label>
                </div>
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium text-slate-300">Reason Code</label>
                <select 
                  value={formData.reason_code}
                  onChange={e => setFormData({...formData, reason_code: e.target.value})}
                  className="w-full bg-slate-900 border border-slate-700 rounded-md px-3 py-2 text-slate-200 focus:outline-none focus:border-blue-500"
                >
                  <option value="10.4">10.4 (Fraud)</option>
                  <option value="4837">4837 (Fraud)</option>
                  <option value="13.1">13.1 (Merchandise Not Received)</option>
                </select>
              </div>
            </div>

            <div className="space-y-1">
              <label className="text-sm font-medium text-slate-300">Respond By</label>
              <input 
                required
                type="date" 
                value={formData.respond_by}
                onChange={e => setFormData({...formData, respond_by: e.target.value})}
                className="w-full bg-slate-900 border border-slate-700 rounded-md px-3 py-2 text-slate-200 focus:outline-none focus:border-blue-500 [color-scheme:dark]" 
              />
            </div>
            
            <div className="space-y-1 pt-2">
              <label className="text-sm font-medium text-slate-300 mb-1 block">Initial Evidence</label>
              <div className="border-2 border-dashed border-slate-600 rounded-lg p-6 flex flex-col items-center justify-center bg-slate-800/50 hover:bg-slate-700/50 transition-colors cursor-pointer">
                <UploadCloud className="w-8 h-8 text-slate-400 mb-2" />
                <p className="text-sm text-slate-300 font-medium">Click to upload or drag and drop</p>
                <p className="text-xs text-slate-500 mt-1">PDF, CSV, JSON up to 10MB</p>
              </div>
            </div>
          </form>
        </div>
        
        <div className="px-6 py-4 border-t border-slate-700 flex justify-end space-x-3 bg-slate-800/50">
          <button 
            type="button" 
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-slate-300 hover:text-white transition-colors"
          >
            Cancel
          </button>
          <button 
            type="submit" 
            form="new-case-form"
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md text-sm font-medium transition-colors"
          >
            Create Case
          </button>
        </div>
      </div>
    </div>
  );
};

export default NewCaseModal;
