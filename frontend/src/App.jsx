import React, { lazy, Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import Login from './pages/Login';
import Register from './pages/Register';
import Upload from './pages/Upload';
import DocumentList from './pages/DocumentList';
import DocumentDetail from './pages/DocumentDetail';
import ReviewPage from './pages/ReviewPage';
import Reports from './pages/Reports';
import ReportDetail from './pages/ReportDetail';
import AuditLogs from './pages/AuditLogs';
import Layout from './components/Layout';
import ManageUsers from './pages/ManageUsers';
import ProfilePage from './pages/ProfilePage';
import './index.css';

const Dashboard = lazy(() => import('./pages/Dashboard'));

function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          <Route path="/" element={<Navigate to="/login" replace />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          
          {/* Protected Routes */}
          <Route element={<ProtectedRoute />}>
            <Route element={<Layout />}>
              <Route path="/dashboard" element={<Suspense fallback={<div className="text-slate-400 py-16 text-center">Loading dashboard…</div>}><Dashboard /></Suspense>} />
              <Route path="/upload" element={<Upload />} />
              <Route path="/documents" element={<DocumentList />} />
              <Route path="/documents/:id" element={<DocumentDetail />} />
              <Route path="/reports" element={<Reports />} />
              <Route path="/reports/:id" element={<ReportDetail />} />
              <Route path="/logs" element={<AuditLogs />} />
              <Route path="/profile" element={<ProfilePage />} />
              <Route element={<ProtectedRoute allowedRoles={['Admin']} />}>
                <Route path="/users" element={<ManageUsers />} />
              </Route>
              <Route element={<ProtectedRoute allowedRoles={['Admin', 'Analyst']} />}>
                <Route path="/review/:id" element={<ReviewPage />} />
              </Route>
            </Route>
          </Route>
          
          {/* Catch-all */}
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;
