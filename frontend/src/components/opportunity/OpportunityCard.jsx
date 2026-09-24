import React, { useState } from 'react';
import { Bookmark, MapPin, Building2, Calendar, ExternalLink, Sparkles } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { apiClient } from '../../lib/apiClient';

export const OpportunityCard = ({ opportunity, onToggleSave }) => {
  const { isAuthenticated, isPremium } = useAuth();
  const [saved, setSaved] = useState(opportunity.is_saved);
  const [saving, setSaving] = useState(false);

  const handleSaveToggle = async () => {
    if (!isAuthenticated) return;
    setSaving(true);
    try {
      if (saved) {
        await apiClient.delete(`/opportunities/${opportunity.id}/unsave/`);
        setSaved(false);
      } else {
        await apiClient.post(`/opportunities/${opportunity.id}/save/`);
        setSaved(true);
      }
      if (onToggleSave) onToggleSave(opportunity.id, !saved);
    } catch (err) {
      console.error('Failed to toggle save state:', err);
    } finally {
      setSaving(false);
    }
  };

  const formattedDeadline = opportunity.application_deadline
    ? new Date(opportunity.application_deadline).toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      })
    : null;

  return (
    <article className="glass-card" style={{ padding: '20px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', gap: '16px' }}>
      <div>
        {/* Header Badges & Actions */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="badge badge-category">
              {opportunity.category?.name || 'Opportunity'}
            </span>
            {opportunity.source_type === 'fetched' && (
              <span className="badge" style={{ background: 'rgba(255, 255, 255, 0.04)', color: 'var(--text-muted)', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
                Verified Fetch
              </span>
            )}
          </div>

          {isAuthenticated && (
            <button
              onClick={handleSaveToggle}
              disabled={saving}
              aria-label="Bookmark opportunity"
              style={{
                background: saved ? 'rgba(99, 102, 241, 0.15)' : 'transparent',
                border: 'none',
                color: saved ? '#a5b4fc' : 'var(--text-muted)',
                cursor: 'pointer',
                padding: '6px',
                borderRadius: '6px',
                transition: 'all 0.15s ease',
              }}
            >
              <Bookmark size={18} fill={saved ? '#a5b4fc' : 'none'} />
            </button>
          )}
        </div>

        {/* Title */}
        <h3 style={{ fontSize: '1.15rem', fontWeight: 600, color: 'var(--text-main)', marginBottom: '8px', lineHeight: 1.4 }}>
          {opportunity.title}
        </h3>

        {/* Meta Info */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px', color: 'var(--text-muted)', fontSize: '0.825rem', marginBottom: '14px', flexWrap: 'wrap' }}>
          {opportunity.organization && (
            <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <Building2 size={14} /> {opportunity.organization}
            </span>
          )}
          {opportunity.location && (
            <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <MapPin size={14} /> {opportunity.location}
            </span>
          )}
          {formattedDeadline && (
            <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#fde047' }}>
              <Calendar size={14} /> Deadline: {formattedDeadline}
            </span>
          )}
        </div>

        {/* Essential Description */}
        <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical', overflow: 'hidden', lineHeight: 1.5 }}>
          {opportunity.description}
        </p>
      </div>

      {/* Footer Action */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: '14px', borderTop: '1px solid var(--border-subtle)' }}>
        {opportunity.opportunity_url ? (
          <a
            href={opportunity.opportunity_url}
            target="_blank"
            rel="noopener noreferrer"
            className="btn-primary"
            style={{ textDecoration: 'none', fontSize: '0.825rem', padding: '7px 12px' }}
          >
            Apply Directly <ExternalLink size={14} />
          </a>
        ) : (
          <span style={{ fontSize: '0.8rem', color: 'var(--text-subtle)' }}>Direct submission</span>
        )}

        {isPremium && (
          <span style={{ fontSize: '0.725rem', color: '#d8b4fe', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <Sparkles size={12} /> Early Access
          </span>
        )}
      </div>
    </article>
  );
};
