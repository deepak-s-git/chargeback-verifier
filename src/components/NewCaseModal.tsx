/**
 * New-case dialog. Emits a {@link CaseCreateRequest} that matches the backend
 * exactly (network + reason_code, never the old `card_network`/metadata shape).
 *
 * Reason codes are constrained to the pairs the requirement engine actually
 * supports — Visa 10.4 and Mastercard 4837 — because any other combination
 * would produce a case with no requirements to evaluate. Evidence is attached
 * afterwards (Evidence tab) or via the demo loader, so there is no decorative
 * "upload" affordance here that doesn't do anything.
 */

import { useState, type FormEvent } from 'react';
import { Plus, X } from 'lucide-react';
import type { CardNetwork, CaseCreateRequest } from '../lib/types';

interface ReasonOption {
  code: string;
  label: string;
}

const REASON_CODES: Record<CardNetwork, ReasonOption[]> = {
  VISA: [{ code: '10.4', label: '10.4 — Fraud (Card-Absent Environment)' }],
  MASTERCARD: [{ code: '4837', label: '4837 — No Cardholder Authorization' }],
};

const CURRENCIES = ['INR', 'USD', 'EUR', 'GBP', 'SGD', 'AED'];

interface FormState {
  merchant_id: string;
  transaction_id: string;
  amount: string;
  currency: string;
  network: CardNetwork;
  reason_code: string;
  dispute_id: string;
  transaction_date: string;
  respond_by: string;
}

const INITIAL: FormState = {
  merchant_id: 'merchant_demo',
  transaction_id: '',
  amount: '',
  currency: 'INR',
  network: 'VISA',
  reason_code: '10.4',
  dispute_id: '',
  transaction_date: '',
  respond_by: '',
};

function toIsoOrNull(date: string): string | null {
  return date ? `${date}T00:00:00Z` : null;
}

export default function NewCaseModal({
  isOpen,
  onClose,
  onCreate,
}: {
  isOpen: boolean;
  onClose: () => void;
  onCreate: (req: CaseCreateRequest) => Promise<void>;
}) {
  const [form, setForm] = useState<FormState>(INITIAL);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const set = <K extends keyof FormState>(key: K, value: FormState[K]) =>
    setForm((f) => ({ ...f, [key]: value }));

  const setNetwork = (network: CardNetwork) =>
    setForm((f) => ({ ...f, network, reason_code: REASON_CODES[network][0].code }));

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const amount = Number(form.amount);
    if (!form.transaction_id.trim()) {
      setError('Transaction ID is required.');
      return;
    }
    if (!Number.isFinite(amount) || amount <= 0) {
      setError('Enter a valid amount greater than zero.');
      return;
    }
    const req: CaseCreateRequest = {
      merchant_id: form.merchant_id.trim() || 'merchant_demo',
      transaction_id: form.transaction_id.trim(),
      amount,
      currency: form.currency,
      network: form.network,
      reason_code: form.reason_code,
      dispute_id: form.dispute_id.trim() || null,
      transaction_date: toIsoOrNull(form.transaction_date),
      respond_by: toIsoOrNull(form.respond_by),
    };
    setSubmitting(true);
    setError(null);
    try {
      await onCreate(req);
      setForm(INITIAL); // parent closes the modal on success
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create the case.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="overlay" onMouseDown={onClose}>
      <div className="modal" onMouseDown={(e) => e.stopPropagation()}>
        <header className="card__header">
          <div>
            <div className="eyebrow">New dispute</div>
            <div className="section-title">Create a case</div>
          </div>
          <button className="btn btn--ghost btn--sm" onClick={onClose} aria-label="Close">
            <X size={16} />
          </button>
        </header>

        <form id="new-case-form" onSubmit={handleSubmit} className="card__body" style={{ display: 'grid', gap: 16 }}>
          <div>
            <span className="label">Card network</span>
            <div className="radio-row">
              {(['VISA', 'MASTERCARD'] as CardNetwork[]).map((n) => (
                <button
                  key={n}
                  type="button"
                  className={`radio-card${form.network === n ? ' radio-card--active' : ''}`}
                  onClick={() => setNetwork(n)}
                >
                  {n === 'MASTERCARD' ? 'Mastercard' : 'Visa'}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="label" htmlFor="nc-reason">Reason code</label>
            <select
              id="nc-reason"
              className="select"
              value={form.reason_code}
              onChange={(e) => set('reason_code', e.target.value)}
            >
              {REASON_CODES[form.network].map((r) => (
                <option key={r.code} value={r.code}>
                  {r.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="label" htmlFor="nc-txn">Transaction ID</label>
            <input
              id="nc-txn"
              className="input mono"
              placeholder="tx_..."
              value={form.transaction_id}
              onChange={(e) => set('transaction_id', e.target.value)}
              autoFocus
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 120px', gap: 12 }}>
            <div>
              <label className="label" htmlFor="nc-amount">Disputed amount</label>
              <input
                id="nc-amount"
                className="input mono"
                type="number"
                min="0"
                step="0.01"
                placeholder="0.00"
                value={form.amount}
                onChange={(e) => set('amount', e.target.value)}
              />
            </div>
            <div>
              <label className="label" htmlFor="nc-currency">Currency</label>
              <select
                id="nc-currency"
                className="select"
                value={form.currency}
                onChange={(e) => set('currency', e.target.value)}
              >
                {CURRENCIES.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div>
              <label className="label" htmlFor="nc-txndate">Transaction date</label>
              <input
                id="nc-txndate"
                className="input"
                type="date"
                value={form.transaction_date}
                onChange={(e) => set('transaction_date', e.target.value)}
              />
            </div>
            <div>
              <label className="label" htmlFor="nc-respond">Respond by</label>
              <input
                id="nc-respond"
                className="input"
                type="date"
                value={form.respond_by}
                onChange={(e) => set('respond_by', e.target.value)}
              />
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div>
              <label className="label" htmlFor="nc-dispute">Dispute ID <span className="text-faint">(optional)</span></label>
              <input
                id="nc-dispute"
                className="input mono"
                placeholder="dsp_..."
                value={form.dispute_id}
                onChange={(e) => set('dispute_id', e.target.value)}
              />
            </div>
            <div>
              <label className="label" htmlFor="nc-merchant">Merchant ID</label>
              <input
                id="nc-merchant"
                className="input mono"
                value={form.merchant_id}
                onChange={(e) => set('merchant_id', e.target.value)}
              />
            </div>
          </div>

          <p className="text-faint" style={{ fontSize: 12, margin: 0 }}>
            The transaction date anchors Visa CE 3.0 windows. Add evidence from the Evidence tab
            after the case is created.
          </p>

          {error && (
            <div className="banner banner--crit">
              <div className="banner__body" style={{ color: 'var(--crit)' }}>{error}</div>
            </div>
          )}
        </form>

        <footer className="card__header" style={{ borderTop: '1px solid var(--hair)', borderBottom: 'none', justifyContent: 'flex-end', gap: 10 }}>
          <button className="btn" onClick={onClose} disabled={submitting}>
            Cancel
          </button>
          <button className="btn btn--primary" type="submit" form="new-case-form" disabled={submitting}>
            {submitting ? <span className="spinner spinner--rail" /> : <Plus size={15} />}
            Create case
          </button>
        </footer>
      </div>
    </div>
  );
}
