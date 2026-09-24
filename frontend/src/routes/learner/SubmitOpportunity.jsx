import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../../lib/apiClient';
import { Send, CheckCircle2, AlertCircle } from 'lucide-react';

export const SubmitOpportunity = () => {
  const navigate = useNavigate();
  const [categories, setCategories] = useState([]);
  const [formData, setFormData] = useState({
    title: '',
    organization: '',
    description: '',
    location: '',
    opportunity_url: '',
    application_deadline: '',
    category: '',
  });
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchCats = async () => {
      try {
        const res = await apiClient.get('/opportunities/categories/');
        const list = res.data.results || res.data;
        setCategories(list);
        if (list.length > 0) {
          setFormData((prev) => ({ ...prev, category: list[0].id }));
        }
      } catch (err) {
        console.error('Failed to load categories:', err);
      }
    };
    fetchCats();
  }, []);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    setSuccess(false);

    try {
      const payload = {
        ...formData,
        application_deadline: formData.application_deadline ? new Date(formData.application_deadline).toISOString() : null,
      };

      await apiClient.post('/opportunities/', payload);
      setSuccess(true);
      setTimeout(() => {
        navigate('/opportunities');
      }, 2000);
    } catch (err) {
      console.error('Submission failed:', err);
      setError(err.response?.data?.detail || 'Failed to submit opportunity. Please check required fields.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{ maxWidth: '700px', margin: '36px auto', padding: '0 24px' }}>
      <div className="glass-panel" style={{ padding: '36px' }}>
        <h2 style={{ fontSize: '1.8rem', fontWeight: 700, marginBottom: '8px' }}>
          Submit an <span className="gradient-text">Opportunity</span>
        </h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.95rem', marginBottom: '28px' }}>
          Submissions are reviewed by moderators before publication to maintain data quality.
        </p>

        {success && (
          <div style={{ background: 'rgba(16, 185, 129, 0.15)', border: '1px solid rgba(16, 185, 129, 0.3)', color: '#6ee7b7', padding: '16px', borderRadius: '10px', display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '24px' }}>
            <CheckCircle2 size={20} />
            <span>Opportunity submitted successfully! Redirecting to feed...</span>
          </div>
        )}

        {error && (
          <div style={{ background: 'rgba(239, 68, 68, 0.15)', border: '1px solid rgba(239, 68, 68, 0.3)', color: '#fca5a5', padding: '16px', borderRadius: '10px', display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '24px' }}>
            <AlertCircle size={20} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div>
            <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, marginBottom: '6px' }}>
              Title *
            </label>
            <input
              type="text"
              required
              name="title"
              className="input-field"
              placeholder="e.g. Software Engineering Internship 2026"
              value={formData.title}
              onChange={handleChange}
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, marginBottom: '6px' }}>
                Organization / Company *
              </label>
              <input
                type="text"
                required
                name="organization"
                className="input-field"
                placeholder="e.g. TechCorp"
                value={formData.organization}
                onChange={handleChange}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, marginBottom: '6px' }}>
                Category *
              </label>
              <select
                name="category"
                className="input-field"
                value={formData.category}
                onChange={handleChange}
                style={{ cursor: 'pointer' }}
              >
                {categories.map((cat) => (
                  <option key={cat.id} value={cat.id} style={{ background: '#1e293b' }}>
                    {cat.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, marginBottom: '6px' }}>
                Location
              </label>
              <input
                type="text"
                name="location"
                className="input-field"
                placeholder="e.g. Remote / Accra, Ghana"
                value={formData.location}
                onChange={handleChange}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, marginBottom: '6px' }}>
                Application Deadline
              </label>
              <input
                type="date"
                name="application_deadline"
                className="input-field"
                value={formData.application_deadline}
                onChange={handleChange}
              />
            </div>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, marginBottom: '6px' }}>
              Official Application URL
            </label>
            <input
              type="url"
              name="opportunity_url"
              className="input-field"
              placeholder="https://example.com/apply"
              value={formData.opportunity_url}
              onChange={handleChange}
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, marginBottom: '6px' }}>
              Description & Requirements *
            </label>
            <textarea
              required
              rows={5}
              name="description"
              className="input-field"
              placeholder="Provide key details, prerequisites, and instructions..."
              value={formData.description}
              onChange={handleChange}
              style={{ resize: 'vertical' }}
            />
          </div>

          <button type="submit" disabled={submitting} className="btn-primary" style={{ width: '100%', marginTop: '10px' }}>
            {submitting ? 'Submitting...' : 'Submit Opportunity'} <Send size={18} />
          </button>
        </form>
      </div>
    </div>
  );
};
