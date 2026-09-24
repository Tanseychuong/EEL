import React, { useState, useEffect } from 'react';
import { apiClient } from '../../lib/apiClient';
import { Shield, Check, X, Building2, Calendar, MapPin, Loader2, AlertCircle } from 'lucide-react';

export const ModerationQueue = () => {
  const [pendingItems, setPendingItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [rejectingId, setRejectingId] = useState(null);
  const [rejectionReason, setRejectionReason] = useState('');
  const [actioning, setActioning] = useState(false);

  const fetchPending = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.get('/opportunities/pending/');
      setPendingItems(res.data.results || res.data);
    } catch (err) {
      console.error('Failed to load pending queue:', err);
      setError('Failed to fetch pending moderation queue.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPending();
  }, []);

  const handleApprove = async (id) => {
    setActioning(true);
    try {
      await apiClient.post(`/opportunities/${id}/approve/`);
      setPendingItems((prev) => prev.filter((item) => item.id !== id));
    } catch (err) {
      console.error('Approval failed:', err);
      alert('Failed to approve opportunity.');
    } finally {
      setActioning(false);
    }
  };

  const handleRejectSubmit = async (e) => {
    e.preventDefault();
    if (!rejectionReason.trim()) return;
    setActioning(true);
    try {
      await apiClient.post(`/opportunities/${rejectingId}/reject/`, {
        reason: rejectionReason,
      });
      setPendingItems((prev) => prev.filter((item) => item.id !== rejectingId));
      setRejectingId(null);
      setRejectionReason('');
    } catch (err) {
      console.error('Rejection failed:', err);
      alert('Failed to reject opportunity.');
    } finally {
      setActioning(false);
    }
  };

  return (
    <div style={{ maxWidth: '1100px', margin: '0 auto', padding: '32px 24px' }}>
      <header style={{ marginBottom: '32px' }}>
        <h1 style={{ fontSize: '2.2rem', fontWeight: 700, color: '#fcd34d', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Shield size={32} /> Moderation Queue
        </h1>
        <p style={{ color: 'var(--text-muted)', fontSize: '1rem' }}>
          Review and approve pending user submissions. Approved items trigger early-access windows.
        </p>
      </header>

      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: '60px' }}>
          <Loader2 size={36} className="animate-spin" color="var(--accent-primary)" />
        </div>
      ) : error ? (
        <div className="glass-panel" style={{ padding: '32px', color: '#f87171', textAlign: 'center' }}>
          {error}
        </div>
      ) : pendingItems.length === 0 ? (
        <div className="glass-panel" style={{ padding: '48px', textAlign: 'center' }}>
          <Check size={48} color="#6ee7b7" style={{ marginBottom: '16px', opacity: 0.8 }} />
          <h3 style={{ fontSize: '1.2rem', marginBottom: '8px' }}>Queue is Clear!</h3>
          <p style={{ color: 'var(--text-muted)' }}>There are no pending submissions awaiting moderation.</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {pendingItems.map((opp) => (
            <div key={opp.id} className="glass-panel" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                    <span className="badge badge-pending">PENDING REVIEW</span>
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                      Submitted by: {opp.posted_by?.name || opp.posted_by?.email || 'Anonymous'}
                    </span>
                  </div>
                  <h3 style={{ fontSize: '1.3rem', fontWeight: 600, color: '#fff' }}>{opp.title}</h3>
                </div>

                <div style={{ display: 'flex', gap: '10px' }}>
                  <button
                    onClick={() => handleApprove(opp.id)}
                    disabled={actioning}
                    className="btn-primary"
                    style={{ background: 'linear-gradient(135deg, #10b981, #059669)', padding: '8px 16px', fontSize: '0.875rem' }}
                  >
                    <Check size={16} /> Approve
                  </button>
                  <button
                    onClick={() => setRejectingId(opp.id)}
                    disabled={actioning}
                    className="btn-secondary"
                    style={{ borderColor: 'rgba(239, 68, 68, 0.4)', color: '#fca5a5', padding: '8px 16px', fontSize: '0.875rem' }}
                  >
                    <X size={16} /> Reject
                  </button>
                </div>
              </div>

              <div style={{ display: 'flex', gap: '16px', fontSize: '0.875rem', color: 'var(--text-muted)', flexWrap: 'wrap' }}>
                {opp.organization && <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}><Building2 size={16} /> {opp.organization}</span>}
                {opp.location && <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}><MapPin size={16} /> {opp.location}</span>}
                {opp.application_deadline && <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}><Calendar size={16} /> Deadline: {new Date(opp.application_deadline).toLocaleDateString()}</span>}
              </div>

              <p style={{ fontSize: '0.95rem', color: 'var(--text-main)', background: 'rgba(0, 0, 0, 0.2)', padding: '12px', borderRadius: '8px' }}>
                {opp.description}
              </p>

              {rejectingId === opp.id && (
                <form onSubmit={handleRejectSubmit} style={{ marginTop: '12px', background: 'rgba(239, 68, 68, 0.1)', padding: '16px', borderRadius: '10px', border: '1px solid rgba(239, 68, 68, 0.3)' }}>
                  <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, color: '#fca5a5', marginBottom: '6px' }}>
                    Reason for Rejection *
                  </label>
                  <textarea
                    required
                    rows={2}
                    className="input-field"
                    placeholder="Provide clear reason to submitter..."
                    value={rejectionReason}
                    onChange={(e) => setRejectionReason(e.target.value)}
                    style={{ marginBottom: '12px' }}
                  />
                  <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
                    <button type="button" onClick={() => setRejectingId(null)} className="btn-secondary" style={{ padding: '6px 12px', fontSize: '0.85rem' }}>
                      Cancel
                    </button>
                    <button type="submit" disabled={actioning} className="btn-primary" style={{ background: '#dc2626', padding: '6px 12px', fontSize: '0.85rem' }}>
                      Confirm Rejection
                    </button>
                  </div>
                </form>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
