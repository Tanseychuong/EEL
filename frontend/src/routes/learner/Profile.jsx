import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { apiClient } from '../../lib/apiClient';
import { User as UserIcon, Camera, Save, CheckCircle2, AlertCircle } from 'lucide-react';

export const Profile = () => {
  const { user, refreshUser } = useAuth();
  const [name, setName] = useState(user?.name || '');
  const [previewUrl, setPreviewUrl] = useState(user?.profile_picture || null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState(null);

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setSelectedFile(file);
    setPreviewUrl(URL.createObjectURL(file)); // local preview only, until saved
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSuccess(false);

    try {
      const formData = new FormData();
      formData.append('name', name);
      if (selectedFile) {
        formData.append('profile_picture', selectedFile);
      }

      // Overriding Content-Type to undefined lets the browser set the
      // correct multipart boundary itself — our apiClient's default header
      // is 'application/json', which would otherwise silently break the
      // file upload (DRF can't parse a multipart body sent as JSON).
      await apiClient.patch('/auth/me/', formData, {
        headers: { 'Content-Type': undefined },
      });

      await refreshUser(); // resync global user state with the saved values
      setSuccess(true);
      setSelectedFile(null);
    } catch (err) {
      console.error('Profile update failed:', err);
      const message =
        err.response?.data?.name?.[0] ||
        err.response?.data?.profile_picture?.[0] ||
        'Failed to update profile. Please try again.';
      setError(message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{ maxWidth: '560px', margin: '36px auto', padding: '0 24px' }}>
      <div className="glass-panel" style={{ padding: '36px' }}>
        <h2 style={{ fontSize: '1.8rem', fontWeight: 700, marginBottom: '8px' }}>
          Your <span className="gradient-text">Profile</span>
        </h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.95rem', marginBottom: '28px' }}>
          Update your display name and profile picture.
        </p>

        {success && (
          <div style={{ background: 'rgba(16, 185, 129, 0.15)', border: '1px solid rgba(16, 185, 129, 0.3)', color: '#6ee7b7', padding: '14px', borderRadius: '10px', display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '22px' }}>
            <CheckCircle2 size={18} /> Profile updated successfully.
          </div>
        )}
        {error && (
          <div style={{ background: 'rgba(239, 68, 68, 0.15)', border: '1px solid rgba(239, 68, 68, 0.3)', color: '#fca5a5', padding: '14px', borderRadius: '10px', display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '22px' }}>
            <AlertCircle size={18} /> {error}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {/* Profile picture */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
            <div style={{
              width: '84px', height: '84px', borderRadius: '50%', overflow: 'hidden',
              background: 'rgba(255,255,255,0.06)', display: 'flex', alignItems: 'center',
              justifyContent: 'center', border: '2px solid var(--border-subtle)', flexShrink: 0,
            }}>
              {previewUrl ? (
                <img src={previewUrl} alt="Profile" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
              ) : (
                <UserIcon size={36} color="var(--text-muted)" />
              )}
            </div>

            <label className="btn-secondary" style={{ cursor: 'pointer', fontSize: '0.875rem', padding: '8px 14px', display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
              <Camera size={16} /> Change photo
              <input type="file" accept="image/*" onChange={handleFileChange} style={{ display: 'none' }} />
            </label>
          </div>

          {/* Name */}
          <div>
            <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, marginBottom: '6px' }}>
              Display Name
            </label>
            <input
              type="text"
              required
              className="input-field"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>

          {/* Email — read-only, shown for context */}
          <div>
            <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, marginBottom: '6px' }}>
              Email
            </label>
            <input type="email" className="input-field" value={user?.email || ''} disabled style={{ opacity: 0.6, cursor: 'not-allowed' }} />
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '4px' }}>
              Email can't be changed here — it's your login identity.
            </p>
          </div>

          <button type="submit" disabled={saving} className="btn-primary" style={{ width: '100%', marginTop: '4px' }}>
            {saving ? 'Saving...' : 'Save Changes'} <Save size={18} />
          </button>
        </form>
      </div>
    </div>
  );
};
