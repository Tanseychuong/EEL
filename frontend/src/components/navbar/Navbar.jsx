import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { Compass, Bookmark, PlusCircle, Shield, LogOut, User, Sparkles } from 'lucide-react';

export const Navbar = () => {
  const { user, isAuthenticated, isPremium, isModerator, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  return (
    <nav className="glass-panel" style={{ borderRadius: 0, borderTop: 0, borderLeft: 0, borderRight: 0, position: 'sticky', top: 0, zIndex: 100 }}>
      <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '14px 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Link to="/" style={{ textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{ background: 'linear-gradient(135deg, #6366f1, #a855f7)', width: '36px', height: '36px', borderRadius: '10px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontWeight: 'bold' }}>
            E
          </div>
          <span className="gradient-text" style={{ fontSize: '1.4rem', fontWeight: 700 }}>EEL Portal</span>
        </Link>

        <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
          <Link to="/opportunities" style={{ color: 'var(--text-main)', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.95rem' }}>
            <Compass size={18} /> Browse
          </Link>

          {isAuthenticated && (
            <>
              <Link to="/saved" style={{ color: 'var(--text-main)', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.95rem' }}>
                <Bookmark size={18} /> Bookmarks
              </Link>
              <Link to="/submit" style={{ color: 'var(--text-main)', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.95rem' }}>
                <PlusCircle size={18} /> Post Opportunity
              </Link>
            </>
          )}

          {isModerator && (
            <Link to="/admin/moderation" style={{ color: '#fcd34d', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.95rem', background: 'rgba(245, 158, 11, 0.15)', padding: '6px 12px', borderRadius: '8px', border: '1px solid rgba(245, 158, 11, 0.3)' }}>
              <Shield size={18} /> Moderation Queue
            </Link>
          )}

          {isAuthenticated ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', paddingLeft: '12px', borderLeft: '1px solid var(--border-subtle)' }}>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span style={{ fontWeight: 600, fontSize: '0.9rem' }}>{user.name}</span>
                  {isPremium && (
                    <span className="badge badge-premium" style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.65rem' }}>
                      <Sparkles size={10} /> PRO
                    </span>
                  )}
                </div>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{user.email}</span>
              </div>
              <button onClick={handleLogout} className="btn-secondary" style={{ padding: '8px 12px', fontSize: '0.85rem' }}>
                <LogOut size={16} /> Logout
              </button>
            </div>
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <Link to="/login" className="btn-secondary" style={{ textDecoration: 'none', fontSize: '0.9rem' }}>Log In</Link>
              <Link to="/register" className="btn-primary" style={{ textDecoration: 'none', fontSize: '0.9rem' }}>Sign Up</Link>
            </div>
          )}
        </div>
      </div>
    </nav>
  );
};
