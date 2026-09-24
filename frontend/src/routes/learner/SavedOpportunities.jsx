import React, { useState, useEffect } from 'react';
import { apiClient } from '../../lib/apiClient';
import { OpportunityCard } from '../../components/opportunity/OpportunityCard';
import { Bookmark, Loader2 } from 'lucide-react';

export const SavedOpportunities = () => {
  const [savedItems, setSavedItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchSaved = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.get('/opportunities/saved/');
      setSavedItems(res.data.results || res.data);
    } catch (err) {
      console.error('Failed to load saved items:', err);
      setError('Could not fetch bookmarked opportunities.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSaved();
  }, []);

  const handleUnsave = (opportunityId) => {
    setSavedItems((prev) => prev.filter((item) => item.opportunity.id !== opportunityId));
  };

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '32px 24px' }}>
      <header style={{ marginBottom: '32px' }}>
        <h1 style={{ fontSize: '2.2rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Bookmark className="gradient-text" size={32} /> Saved Opportunities
        </h1>
        <p style={{ color: 'var(--text-muted)', fontSize: '1rem' }}>
          Your bookmarked opportunities, synced across devices.
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
      ) : savedItems.length === 0 ? (
        <div className="glass-panel" style={{ padding: '48px', textAlign: 'center' }}>
          <Bookmark size={48} color="var(--text-muted)" style={{ marginBottom: '16px', opacity: 0.5 }} />
          <h3 style={{ fontSize: '1.2rem', marginBottom: '8px' }}>No saved opportunities yet</h3>
          <p style={{ color: 'var(--text-muted)' }}>Browse the feed and click the bookmark icon to save opportunities for later.</p>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))', gap: '24px' }}>
          {savedItems.map((item) => (
            <OpportunityCard
              key={item.id}
              opportunity={{ ...item.opportunity, is_saved: true }}
              onToggleSave={handleUnsave}
            />
          ))}
        </div>
      )}
    </div>
  );
};
