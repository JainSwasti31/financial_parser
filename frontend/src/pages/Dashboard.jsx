import React, { useEffect, useState } from 'react';
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import RecentActivity from '../components/RecentActivity';
import { getDashboard } from '../services/api';

const ChartCard = ({ title, children }) => <div className="bg-slate-800/40 border border-slate-700/50 rounded-2xl p-5"><h2 className="font-semibold mb-5">{title}</h2><div className="h-64">{children}</div></div>;
const tooltipStyle = { background: '#0f172a', border: '1px solid #334155', borderRadius: 8 };

const Dashboard = () => {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  useEffect(() => {
    getDashboard().then(response => setData(response.data)).catch(e => setError(e.response?.data?.error?.message || 'Failed to load dashboard.'));
  }, []);
  if (error) return <div className="text-red-400 py-16 text-center">{error}</div>;
  if (!data) return <div className="text-slate-400 py-16 text-center">Loading dashboard…</div>;
  const cards = [
    ['Total Uploaded', data.total_uploaded_documents],
    ['Successfully Parsed', data.successfully_parsed],
    ['Failed Parsing', data.failed_parsing],
    ['Success Rate', `${data.processing_success_rate}%`],
    ['Average Processing', `${data.average_processing_time}s`],
  ];
  return (
    <div className="space-y-6">
      <div><h1 className="text-3xl font-bold">Dashboard</h1><p className="text-slate-400 mt-1">Live document processing overview</p></div>
      <div className="grid sm:grid-cols-2 lg:grid-cols-5 gap-4">{cards.map(([label, value]) => <div key={label} className="bg-slate-800/40 border border-slate-700/50 rounded-2xl p-5"><p className="text-xs uppercase text-slate-500">{label}</p><p className="text-3xl font-bold mt-2">{value}</p></div>)}</div>
      <div className="grid lg:grid-cols-2 gap-6">
        <ChartCard title="Documents by Type"><ResponsiveContainer width="100%" height="100%"><BarChart data={data.documents_by_type}><CartesianGrid stroke="#334155" strokeDasharray="3 3"/><XAxis dataKey="type" stroke="#94a3b8" tick={{fontSize: 11}}/><YAxis allowDecimals={false} stroke="#94a3b8"/><Tooltip contentStyle={tooltipStyle}/><Bar dataKey="count" fill="#818cf8" radius={[5,5,0,0]}/></BarChart></ResponsiveContainer></ChartCard>
        <ChartCard title="Daily Uploads"><ResponsiveContainer width="100%" height="100%"><LineChart data={data.daily_uploads}><CartesianGrid stroke="#334155" strokeDasharray="3 3"/><XAxis dataKey="date" stroke="#94a3b8" tick={{fontSize: 10}}/><YAxis allowDecimals={false} stroke="#94a3b8"/><Tooltip contentStyle={tooltipStyle}/><Line type="monotone" dataKey="count" stroke="#a78bfa" strokeWidth={3}/></LineChart></ResponsiveContainer></ChartCard>
        <ChartCard title="Monthly Uploads"><ResponsiveContainer width="100%" height="100%"><BarChart data={data.monthly_uploads}><CartesianGrid stroke="#334155" strokeDasharray="3 3"/><XAxis dataKey="month" stroke="#94a3b8"/><YAxis allowDecimals={false} stroke="#94a3b8"/><Tooltip contentStyle={tooltipStyle}/><Bar dataKey="count" fill="#34d399" radius={[5,5,0,0]}/></BarChart></ResponsiveContainer></ChartCard>
        <RecentActivity items={data.recent_activity}/>
      </div>
    </div>
  );
};

export default Dashboard;
