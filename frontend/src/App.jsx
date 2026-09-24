import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Navbar } from './components/navbar/Navbar';
import { OpportunitiesFeed } from './routes/learner/OpportunitiesFeed';
import { SubmitOpportunity } from './routes/learner/SubmitOpportunity';
import { SavedOpportunities } from './routes/learner/SavedOpportunities';
import { Login } from './routes/public/Login';
import { Register } from './routes/public/Register';
import { ModerationQueue } from './routes/admin/ModerationQueue';
import { Loader2 } from 'lucide-react';

const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();
  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <Loader2 size={36} className="animate-spin" color="var(--accent-primary)" />
      </div>
    );
  }
  return isAuthenticated ? children : <Navigate to="/login" replace />;
};

const ModeratorRoute = ({ children }) => {
  const { isAuthenticated, isModerator, loading } = useAuth();
  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <Loader2 size={36} className="animate-spin" color="var(--accent-primary)" />
      </div>
    );
  }
  return isAuthenticated && isModerator ? children : <Navigate to="/opportunities" replace />;
};

export function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
          <Navbar />
          <main style={{ flex: 1 }}>
            <Routes>
              <Route path="/" element={<Navigate to="/opportunities" replace />} />
              <Route path="/opportunities" element={<OpportunitiesFeed />} />
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />
              
              <Route
                path="/submit"
                element={
                  <ProtectedRoute>
                    <SubmitOpportunity />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/saved"
                element={
                  <ProtectedRoute>
                    <SavedOpportunities />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/admin/moderation"
                element={
                  <ModeratorRoute>
                    <ModerationQueue />
                  </ModeratorRoute>
                }
              />

              <Route path="*" element={<Navigate to="/opportunities" replace />} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
