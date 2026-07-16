import React, { useContext } from 'react';
import { AuthContext } from '../context/AuthContext';
import { useNavigate, Link, Outlet } from 'react-router-dom';

const Layout = () => {
  const { user, logout } = useContext(AuthContext);
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-slate-900 text-white">
      {/* Header */}
      <header className="bg-slate-800/50 backdrop-blur-md border-b border-slate-700/50 p-4 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <Link to="/dashboard" className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 to-violet-400">
            Financial Parser
          </Link>
          <div className="flex items-center space-x-6">
            <Link to="/documents" className="text-sm font-medium text-slate-300 hover:text-white transition-colors">
              Documents
            </Link>
            <Link to="/reports" className="text-sm font-medium text-slate-300 hover:text-white transition-colors">
              Reports
            </Link>
            <Link to="/logs" className="text-sm font-medium text-slate-300 hover:text-white transition-colors">
              Audit Logs
            </Link>
            <Link to="/upload" className="text-sm font-medium text-slate-300 hover:text-white transition-colors">
              Upload
            </Link>
            <div className="flex items-center space-x-2 border-l border-slate-700 pl-6">
              <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-indigo-500 to-violet-500 flex items-center justify-center font-bold text-sm shadow-lg">
                {user?.name?.charAt(0)?.toUpperCase()}
              </div>
              <span className="text-sm text-slate-300 font-medium">
                {user?.name}
              </span>
              <span className="text-xs px-2 py-1 bg-indigo-500/20 text-indigo-300 rounded-full border border-indigo-500/30">
                {user?.role}
              </span>
            </div>
            <button
              onClick={handleLogout}
              className="text-sm text-slate-400 hover:text-white transition-colors ml-4"
            >
              Sign out
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto p-6 mt-8">
        <Outlet />
      </main>
    </div>
  );
};

export default Layout;
