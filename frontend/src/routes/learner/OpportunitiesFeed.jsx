import React, { useState, useEffect, useCallback } from 'react';
import { apiClient } from '../../lib/apiClient';
import { OpportunityCard } from '../../components/opportunity/OpportunityCard';
import { Search, Loader2, Sparkles } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

export const OpportunitiesFeed = () => {
  const { isPremium } = useAuth();
  const [opportunities, setOpportunities] = useState([]);
  const [categories, setCategories] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchCategories = async () => {
    try {
      const res = await apiClient.get('/opportunities/categories/');
      setCategories(res.data.results || res.data);
    } catch (err) {
      console.error('Failed to fetch categories:', err);
    }
  };

  const fetchOpportunities = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = {};
      if (selectedCategory) params.category = selectedCategory;
      const res = await apiClient.get('/opportunities/', { params });
      setOpportunities(res.data.results || res.data);
    } catch (err) {
      console.error('Failed to fetch opportunities:', err);
      setError('Could not load opportunities. Please verify server connection.');
    } finally {
      setLoading(false);
    }
  }, [selectedCategory]);

  useEffect(() => {
    fetchCategories();
  }, []);

  useEffect(() => {
    fetchOpportunities();
  }, [fetchOpportunities]);

  const filteredOpportunities = opportunities.filter((opp) =>
    opp.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    opp.organization?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    opp.description.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '28px 24px 48px' }}>
      {/* Header */}
      <header style={{ marginBottom: '28px' }}>
        <h1 style={{ fontSize: '2.2rem', fontWeight: 700, letterSpacing: '-0.02em', marginBottom: '8px' }}>
          Explore <span className="gradient-text">Opportunities</span>
        </h1>
        <p style={{ color: 'var(--text-muted)', fontSize: '1rem', maxWidth: '640px' }}>
          Curated scholarships, internships, grants, and career listings verified for students and researchers.
        </p>

        {!isPremium && (
          <div className="glass-card" style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', marginTop: '14px', padding: '6px 14px', border: '1px solid rgba(168, 85, 247, 0.25)', background: 'rgba(168, 85, 247, 0.08)' }}>
            <Sparkles size={15} color="#c084fc" />
            <span style={{ fontSize: '0.825rem', color: '#e9d5ff' }}>
              <strong>48-Hour Early Access</strong> unlocked for Premium Members. Bypasses waiting windows.
            </span>
          </div>
        )}
      </header>

      {/* Search & Filter Bar */}
      <div style={{ display: 'flex', gap: '14px', marginBottom: '24px', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between' }}>
        {/* Search */}
        <div style={{ position: 'relative', flex: 1, minWidth: '260px' }}>
          <Search size={16} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
          <input
            type="text"
            className="input-field"
            placeholder="Search titles, organizations, or keywords..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{ paddingLeft: '38px', fontSize: '0.875rem' }}
          />
        </div>

        {/* Category Pills */}
        <div style={{ display: 'flex', gap: '6px', overflowX: 'auto', paddingBottom: '2px' }}>
          <button
            onClick={() => setSelectedCategory('')}
            className={selectedCategory === '' ? 'btn-primary' : 'btn-secondary'}
            style={{ padding: '6px 14px', fontSize: '0.825rem' }}
          >
            All
          </button>
          {categories.map((cat) => (
            <button
              key={cat.id}
              onClick={() => setSelectedCategory(cat.slug)}
              className={selectedCategory === cat.slug ? 'btn-primary' : 'btn-secondary'}
              style={{ padding: '6px 14px', fontSize: '0.825rem', whitespace: 'nowrap' }}
            >
              {cat.name}
            </button>
          ))}
        </div>
      </div>

      {/* Grid Content */}
      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', padding: '60px' }}>
          <Loader2 size={32} className="animate-spin" color="var(--accent-primary)" />
        </div>
      ) : error ? (
        <div className="glass-card" style={{ padding: '24px', textAlign: 'center', color: '#f87171' }}>
          {error}
        </div>
      ) : filteredOpportunities.length === 0 ? (
        <div className="glass-card" style={{ padding: '40px', textAlign: 'center' }}>
          <h3 style={{ fontSize: '1.1rem', marginBottom: '6px' }}>No opportunities found</h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>Try clearing your search term or choosing another category.</p>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: '20px' }}>
          {filteredOpportunities.map((opp) => (
            <OpportunityCard key={opp.id} opportunity={opp} />
          ))}
        </div>
      )}
    </div>
  );
};
