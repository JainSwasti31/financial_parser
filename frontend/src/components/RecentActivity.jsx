import React from 'react';
import { Link } from 'react-router-dom';

const RecentActivity = ({ items = [] }) => (
  <div className="bg-slate-800/40 border border-slate-700/50 rounded-2xl p-6">
    <div className="flex justify-between items-center mb-4"><h2 className="text-lg font-semibold">Recent Activity</h2><Link to="/logs" className="text-sm text-indigo-400">View all</Link></div>
    <div className="space-y-3">
      {items.length === 0 ? <p className="text-slate-500 text-sm">No activity yet.</p> : items.map(item => (
        <div key={item.id} className="border-l-2 border-indigo-500 pl-4 py-1">
          <div className="flex justify-between gap-4"><p className="text-sm text-slate-200">{item.action}</p><span className="text-xs text-slate-500">{item.created_at ? new Date(item.created_at).toLocaleString() : ''}</span></div>
          <p className="text-xs text-slate-400 mt-1">{item.document_name || `Document #${item.document_id}`} · {item.status}</p>
          {item.remarks && <p className="text-xs text-slate-500 mt-1 truncate">{item.remarks}</p>}
        </div>
      ))}
    </div>
  </div>
);

export default RecentActivity;
